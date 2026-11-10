"""Repository for POI collection.

CRITICAL INVARIANT:
- Uses COLLECTION_POI ("POI").
- Public queries MUST filter { "is_active": True, "deleted_at": None }.
- Uses 2dsphere index for find_nearby.
- Optimistic locking via 'version'.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import re
from app.repositories.base import BaseRepository, build_id_filter, serialize_mongo_doc
from app.db.collections import COLLECTION_POI, COLLECTION_POI_LOCALIZATIONS, COLLECTION_MENU_ITEM


VIETNAMESE_CHAR_MAP = {
    'a': '[aàáảãạăằắẳẵặâầấẩẫậ]',
    'e': '[eèéẻẽẹêềếểễệ]',
    'i': '[iìíỉĩị]',
    'o': '[oòóỏõọôồốổỗộơờớởỡợ]',
    'u': '[uùúủũụưừứửữự]',
    'y': '[yỳýỷỹỵ]',
    'd': '[dđ]',
}

def to_vietnamese_regex(text: str) -> str:
    result = []
    for ch in text:
        lower = ch.lower()
        if lower in VIETNAMESE_CHAR_MAP:
            result.append(VIETNAMESE_CHAR_MAP[lower])
        else:
            result.append(re.escape(ch))
    return ''.join(result)


class POIRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_POI)

    @property
    def localizations_collection(self):
        return self.db[COLLECTION_POI_LOCALIZATIONS]

    def content_query(self, poi_id, version):
        query = {**build_id_filter(poi_id), "deleted_at": None, "content_version": version}
        if version == 1:
            query.pop("content_version")
            query["$or"] = [{"content_version": 1}, {"content_version": {"$exists": False}}]
        return query

    async def fence_content(self, poi_id, version, session=None):
        result = await self.collection.update_one(
            self.content_query(poi_id, version),
            {"$inc": {"localization_revision": 1}},
            **({"session": session} if session else {}),
        )
        return bool(result.matched_count)

    async def get_public_by_id(self, poi_id: str) -> Optional[Dict[str, Any]]:
        """Fetch POI if active and not soft-deleted."""
        q = build_id_filter(poi_id)
        q["is_active"] = True
        q["deleted_at"] = None
        doc = await self.collection.find_one(q)
        return serialize_mongo_doc(doc)

    async def find_public(
        self,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "deleted_at": None,
        }
        if not include_inactive:
            query["is_active"] = True
        if category:
            query["category"] = category
        if search and search.strip():
            safe_search = re.escape(search.strip()[:100])
            query["$or"] = [
                {"name": {"$regex": safe_search, "$options": "i"}},
                {"description": {"$regex": safe_search, "$options": "i"}},
                {"address": {"$regex": safe_search, "$options": "i"}},
            ]
        cursor = self.collection.find(query).sort([("audio_priority", -1), ("_id", 1)]).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_nearby_geo_near(
        self,
        longitude: float,
        latitude: float,
        max_distance_meters: float = 2000.0,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Geospatial nearby query using MongoDB aggregation $geoNear.

        Directly computes and outputs `straight_line_distance_m` in SI meters.
        """
        from app.services.geo_service import haversine_distance_meters

        match_criteria: Dict[str, Any] = {
            "is_active": True,
            "deleted_at": None,
        }
        if category:
            match_criteria["category"] = category

        pipeline = [
            {
                "$geoNear": {
                    "near": {
                        "type": "Point",
                        "coordinates": [float(longitude), float(latitude)]
                    },
                    "distanceField": "straight_line_distance_m",
                    "maxDistance": float(max_distance_meters),
                    "query": match_criteria,
                    "spherical": True
                }
            },
            {"$limit": limit}
        ]

        try:
            results = await self.aggregate_to_list(self.collection, pipeline, length=limit)
            return results
        except Exception:
            # Fallback to query + python haversine if geoNear index not yet warm
            fallback_query = {
                "is_active": True,
                "deleted_at": None,
            }
            if category:
                fallback_query["category"] = category
            cursor = self.collection.find(fallback_query).limit(100)
            items = await cursor.to_list(length=100)
            with_dist = []
            for item in items:
                loc = item.get("location", {}).get("coordinates")
                if loc and len(loc) >= 2:
                    dist = haversine_distance_meters(latitude, longitude, loc[1], loc[0])
                    if dist <= max_distance_meters:
                        item["straight_line_distance_m"] = round(dist, 1)
                        with_dist.append(item)
            with_dist.sort(key=lambda x: x["straight_line_distance_m"])
            return with_dist[:limit]

    async def find_nearby(
        self,
        longitude: float,
        latitude: float,
        max_distance_meters: float = 1000.0,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Legacy-compatible wrapper calling find_nearby_geo_near."""
        return await self.find_nearby_geo_near(
            longitude=longitude,
            latitude=latitude,
            max_distance_meters=max_distance_meters,
            category=category,
            limit=limit
        )

    async def search_pois(
        self,
        query: str,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Searches POIs across name, description, address, menu dishes, and localized content without fake coords."""
        raw_query = query.strip()[:100]
        if not raw_query:
            return []
        viet_pattern = to_vietnamese_regex(raw_query)

        # 1. Match localized content (multilingual)
        loc_cursor = self.localizations_collection.find(
            {
                "$or": [
                    {"name": {"$regex": viet_pattern, "$options": "i"}},
                    {"description": {"$regex": viet_pattern, "$options": "i"}}
                ]
            },
            {"poi_id": 1}
        ).limit(50)
        matched_loc_ids = [doc["poi_id"] for doc in await loc_cursor.to_list(length=50) if "poi_id" in doc]

        # 2. Match dishes in menu_items collection
        menu_cursor = self.db[COLLECTION_MENU_ITEM].find(
            {
                "$or": [
                    {"name": {"$regex": viet_pattern, "$options": "i"}},
                    {"description": {"$regex": viet_pattern, "$options": "i"}}
                ],
                "is_available": True
            },
            {"poi_id": 1}
        ).limit(50)
        matched_menu_poi_ids = [doc["poi_id"] for doc in await menu_cursor.to_list(length=50) if "poi_id" in doc]

        all_matched_ids = list(set(matched_loc_ids + matched_menu_poi_ids))

        poi_query: Dict[str, Any] = {
            "is_active": True,
            "deleted_at": None,
            "location.coordinates": {"$exists": True, "$type": "array"},
            "$or": [
                {"name": {"$regex": viet_pattern, "$options": "i"}},
                {"description": {"$regex": viet_pattern, "$options": "i"}},
                {"address": {"$regex": viet_pattern, "$options": "i"}},
                {"code": {"$regex": re.escape(raw_query), "$options": "i"}},
            ]
        }
        if all_matched_ids:
            poi_query["$or"].append({"_id": {"$in": all_matched_ids}})

        if category and category != "all":
            poi_query["category"] = category

        cursor = self.collection.find(poi_query).skip(skip).limit(limit).sort("audio_priority", -1)
        results = await cursor.to_list(length=limit)

        # Filter out missing, null, or (0, 0) dummy/fake coordinates
        valid_results = []
        for doc in results:
            coords = doc.get("location", {}).get("coordinates")
            if coords and len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
                if abs(coords[0]) > 0.0001 and abs(coords[1]) > 0.0001:
                    valid_results.append(doc)
        return valid_results

    async def find_in_bounds(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Finds POIs within a bounding box [min_lon, min_lat, max_lon, max_lat]."""
        query: Dict[str, Any] = {
            "is_active": True,
            "deleted_at": None,
            "location": {
                "$geoWithin": {
                    "$box": [
                        [min_lon, min_lat],
                        [max_lon, max_lat]
                    ]
                }
            }
        }
        if category and category != "all":
            query["category"] = category

        try:
            cursor = self.collection.find(query).limit(limit).sort("audio_priority", -1)
            return await cursor.to_list(length=limit)
        except Exception:
            # Fallback for mongomock or test environments lacking $geoWithin
            fallback_query: Dict[str, Any] = {
                "is_active": True,
                "deleted_at": None,
            }
            if category and category != "all":
                fallback_query["category"] = category
            cursor = self.collection.find(fallback_query).limit(100)
            items = await cursor.to_list(length=100)
            matched = []
            for item in items:
                coords = item.get("location", {}).get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                        matched.append(item)
            matched.sort(key=lambda x: x.get("audio_priority", 0), reverse=True)
            return matched[:limit]

    async def find_by_owner(self, owner_id: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Owner-scoped query for their own POIs."""
        query = {
            "owner_id": owner_id,
            "deleted_at": None,
        }
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)

    async def count_public(self, category: Optional[str] = None, include_inactive: bool = False) -> int:
        query: Dict[str, Any] = {"deleted_at": None}
        if not include_inactive:
            query["is_active"] = True
        if category:
            query["category"] = category
        return await self.collection.count_documents(query)

    async def create_poi(self, doc: Dict[str, Any], session=None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc.setdefault("version", 1)
        doc.setdefault("content_version", 1)
        doc.setdefault("is_active", True)
        doc.setdefault("activation_requested", False)
        doc.setdefault("deleted_at", None)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        await self.collection.insert_one(doc, **({"session": session} if session else {}))
        return doc

    async def update_poi_with_version(
        self,
        poi_id: str,
        update_fields: Dict[str, Any],
        expected_version: int,
        content_changed: bool = False,
        session=None
    ) -> Optional[Dict[str, Any]]:
        """Optimistic concurrency update."""
        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now

        inc_fields = {"version": 1}
        if content_changed:
            inc_fields["content_version"] = 1

        query = build_id_filter(poi_id)
        query["version"] = expected_version
        query["deleted_at"] = None

        result = await self.collection.find_one_and_update(
            query,
            {
                "$set": update_fields,
                "$inc": inc_fields
            },
            return_document=True,
            **({"session": session} if session else {})
        )
        return serialize_mongo_doc(result)

    async def soft_delete(self, poi_id: str) -> bool:
        now = datetime.now(timezone.utc)
        query = build_id_filter(poi_id)
        query["deleted_at"] = None
        result = await self.collection.update_one(
            query,
            {"$set": {
                "deleted_at": now,
                "is_active": False,
                "updated_at": now,
            }}
        )
        return result.modified_count > 0

    async def get_localizations(self, poi_id: str) -> List[Dict[str, Any]]:
        cursor = self.localizations_collection.find({"poi_id": poi_id})
        return await cursor.to_list(length=50)

    async def get_localization_by_lang(self, poi_id: str, lang: str) -> Optional[Dict[str, Any]]:
        return await self.localizations_collection.find_one({"poi_id": poi_id, "lang": lang})

    async def upsert_localization(self, loc_doc: Dict[str, Any], session=None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        loc_doc["updated_at"] = now
        await self.localizations_collection.update_one(
            {"poi_id": loc_doc["poi_id"], "lang": loc_doc["lang"]},
            {"$set": loc_doc},
            upsert=True,
            **({"session": session} if session else {})
        )
        return loc_doc


poi_repo = POIRepository()
