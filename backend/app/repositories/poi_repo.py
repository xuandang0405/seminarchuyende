"""Repository for POI collection.

CRITICAL INVARIANT:
- Uses COLLECTION_POI ("POI").
- Public queries MUST filter { "is_active": True, "deleted_at": None }.
- Uses 2dsphere index for find_nearby.
- Optimistic locking via 'version'.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository
from app.db.collections import COLLECTION_POI, COLLECTION_POI_LOCALIZATIONS


class POIRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_POI)

    @property
    def localizations_collection(self):
        return self.db[COLLECTION_POI_LOCALIZATIONS]

    async def get_public_by_id(self, poi_id: str) -> Optional[Dict[str, Any]]:
        """Fetch POI if active and not soft-deleted."""
        return await self.collection.find_one({
            "_id": poi_id,
            "is_active": True,
            "deleted_at": None,
        })

    async def find_public(
        self,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "is_active": True,
            "deleted_at": None,
        }
        if category:
            query["category"] = category
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"address": {"$regex": search, "$options": "i"}},
            ]
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("audio_priority", -1)
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
            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
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
        """Searches POIs across name, description, address, and localized content."""
        clean_q = query.strip()
        if not clean_q:
            return []

        # Find POI IDs matching localized names (e.g. English or French search terms)
        loc_cursor = self.localizations_collection.find(
            {
                "$or": [
                    {"name": {"$regex": clean_q, "$options": "i"}},
                    {"description": {"$regex": clean_q, "$options": "i"}}
                ]
            },
            {"poi_id": 1}
        ).limit(50)
        matched_loc_ids = [doc["poi_id"] for doc in await loc_cursor.to_list(length=50) if "poi_id" in doc]

        poi_query: Dict[str, Any] = {
            "is_active": True,
            "deleted_at": None,
            "$or": [
                {"name": {"$regex": clean_q, "$options": "i"}},
                {"description": {"$regex": clean_q, "$options": "i"}},
                {"address": {"$regex": clean_q, "$options": "i"}},
                {"code": {"$regex": clean_q, "$options": "i"}},
                {"_id": {"$in": matched_loc_ids}}
            ]
        }
        if category and category != "all":
            poi_query["category"] = category

        cursor = self.collection.find(poi_query).skip(skip).limit(limit).sort("audio_priority", -1)
        return await cursor.to_list(length=limit)

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

    async def count_public(self, category: Optional[str] = None) -> int:
        query: Dict[str, Any] = {"is_active": True, "deleted_at": None}
        if category:
            query["category"] = category
        return await self.collection.count_documents(query)

    async def create_poi(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc.setdefault("version", 1)
        doc.setdefault("content_version", 1)
        doc.setdefault("is_active", False)
        doc.setdefault("activation_requested", False)
        doc.setdefault("deleted_at", None)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        await self.collection.insert_one(doc)
        return doc

    async def update_poi_with_version(
        self,
        poi_id: str,
        update_fields: Dict[str, Any],
        expected_version: int,
        content_changed: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Optimistic concurrency update."""
        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now

        inc_fields = {"version": 1}
        if content_changed:
            inc_fields["content_version"] = 1

        result = await self.collection.find_one_and_update(
            {"_id": poi_id, "version": expected_version, "deleted_at": None},
            {
                "$set": update_fields,
                "$inc": inc_fields
            },
            return_document=True
        )
        return result

    async def soft_delete(self, poi_id: str) -> bool:
        now = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": poi_id, "deleted_at": None},
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

    async def upsert_localization(self, loc_doc: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        loc_doc["updated_at"] = now
        await self.localizations_collection.update_one(
            {"poi_id": loc_doc["poi_id"], "lang": loc_doc["lang"]},
            {"$set": loc_doc},
            upsert=True
        )
        return loc_doc


poi_repo = POIRepository()
