"""Service for Public POI viewing, searching, nearby calculation, and language fallback.

AD01 / SD01 / T01 / T04 / T05 / N01.
"""

import hashlib
import json
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from app.repositories.poi_repo import poi_repo


class POIService:
    def __init__(self):
        self._catalog_versions = OrderedDict()

    async def sync_public_pois(self, lang: str, updated_after: Optional[str]):
        """Return a consistent snapshot or a delta against a recent revision."""
        items = []
        skip = 0
        while True:
            page = await poi_repo.find_public(skip=skip, limit=100)
            items.extend([await self._resolve_poi_localization(poi, lang) for poi in page])
            if len(page) < 100:
                break
            skip += len(page)
        revisions = {
            item["id"]: hashlib.sha256(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest()
            for item in items
        }
        version = hashlib.sha256(json.dumps(revisions, sort_keys=True).encode()).hexdigest()
        previous = self._catalog_versions.get((lang, updated_after))
        self._catalog_versions[(lang, version)] = revisions
        self._catalog_versions.move_to_end((lang, version))
        if len(self._catalog_versions) > 24:
            self._catalog_versions.popitem(last=False)
        return {
            "dataset_version": version,
            "sync_cursor": version,
            "sync_mode": "delta" if previous is not None else "full",
            "removed_poi_ids": sorted(previous.keys() - revisions.keys()) if previous is not None else [],
            "ordered_poi_ids": list(revisions),
            "items": [item for item in items if previous.get(item["id"]) != revisions[item["id"]]] if previous is not None else items,
        }

    async def get_public_pois(
        self,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        search: Optional[str] = None,
        lang: str = "vi"
    ) -> Dict[str, Any]:
        """Fetch list of public POIs with resolved localization fallback (lang -> en -> vi)."""
        pois = await poi_repo.find_public(skip=skip, limit=limit, category=category, search=search)
        total = await poi_repo.count_public(category=category)

        items = []
        for p in pois:
            resolved = await self._resolve_poi_localization(p, lang)
            items.append(resolved)

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    async def search_public_pois(
        self,
        query: str,
        category: Optional[str] = None,
        origin_lat: Optional[float] = None,
        origin_lon: Optional[float] = None,
        lang: str = "vi",
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search published POIs by keyword across multilingual content."""
        from app.services.geo_service import haversine_distance_meters, format_distance_display

        pois = await poi_repo.search_pois(query=query, category=category, skip=skip, limit=limit)
        items = []
        for p in pois:
            resolved = await self._resolve_poi_localization(p, lang)
            if origin_lat is not None and origin_lon is not None:
                loc = resolved.get("location", {}).get("coordinates")
                if loc and len(loc) >= 2:
                    dist = haversine_distance_meters(origin_lat, origin_lon, loc[1], loc[0])
                    resolved["straight_line_distance_m"] = round(dist, 1)
                    resolved["distance_display"] = format_distance_display(dist, lang=lang)
            items.append(resolved)
        return items

    async def get_nearby_pois(
        self,
        longitude: float,
        latitude: float,
        max_distance_meters: float = 2000.0,
        category: Optional[str] = None,
        limit: int = 20,
        lang: str = "vi"
    ) -> List[Dict[str, Any]]:
        """Geospatial nearby POIs using MongoDB aggregation $geoNear with SI distance."""
        from app.services.geo_service import format_distance_display

        pois = await poi_repo.find_nearby_geo_near(
            longitude=longitude,
            latitude=latitude,
            max_distance_meters=max_distance_meters,
            category=category,
            limit=limit
        )
        items = []
        for p in pois:
            dist = p.get("straight_line_distance_m")
            resolved = await self._resolve_poi_localization(p, lang)
            if dist is not None:
                resolved["straight_line_distance_m"] = round(float(dist), 1)
                resolved["distance_display"] = format_distance_display(float(dist), lang=lang)
            items.append(resolved)
        return items

    async def get_pois_in_bounds(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        category: Optional[str] = None,
        limit: int = 50,
        lang: str = "vi"
    ) -> List[Dict[str, Any]]:
        """Fetch POIs within map viewport bounding box."""
        pois = await poi_repo.find_in_bounds(
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            category=category,
            limit=limit
        )
        return [await self._resolve_poi_localization(p, lang) for p in pois]

    async def get_poi_detail(self, poi_id: str, lang: str = "vi") -> Optional[Dict[str, Any]]:
        """Get detail of a public POI."""
        poi = await poi_repo.get_public_by_id(poi_id)
        if not poi:
            return None
        return await self._resolve_poi_localization(poi, lang, include_all_localizations=True)

    async def _resolve_poi_localization(
        self,
        poi: Dict[str, Any],
        requested_lang: str,
        include_all_localizations: bool = False
    ) -> Dict[str, Any]:
        """Resolves content by fallback order: requested_lang -> en -> vi."""
        from app.services.audio_service import audio_service

        def audio_ready(localization):
            return bool(localization and localization.get("audio_status") == "ready" and audio_service.localization_file_exists(localization))

        poi_id = poi["_id"]
        
        locs = await poi_repo.get_localizations(poi_id)
        source_version = poi.get("content_version", 1)
        loc_map = {(l.get("lang") or l.get("language_code")): l for l in locs if (l.get("lang") or l.get("language_code")) and l.get("source_version", source_version) == source_version
                   and l.get("translation_status") in (None, "ready")}

        resolved_lang = requested_lang
        is_fallback = False
        target_loc = loc_map.get(requested_lang)

        if not audio_ready(target_loc):
            fallback = next((code for code in ("en", "vi") if code != requested_lang and audio_ready(loc_map.get(code))), None)
            if fallback:
                resolved_lang = fallback
                target_loc = loc_map[fallback]
            elif target_loc is None:
                resolved_lang = "vi"
                target_loc = loc_map.get("vi")
            # Keep a translated description visible if all narration files are missing.
            is_fallback = requested_lang != resolved_lang
        narration_ready = audio_ready(target_loc)

        # Build published_contents map for multi-language access
        published_contents = {}
        for l_code, l_doc in loc_map.items():
            published_contents[l_code] = {
                "title": l_doc.get("name", poi.get("name")),
                "name": l_doc.get("name", poi.get("name")),
                "description": l_doc.get("description", poi.get("description")),
                "narration_text": l_doc.get("description", poi.get("description")),
                "audio_url": l_doc.get("audio_url") if l_doc.get("audio_status") == "ready" else None,
                "audio_asset_id": l_doc.get("audio_asset_id"),
                "duration_ms": l_doc.get("audio_duration_ms", 0),
            }

        name_val = (target_loc or {}).get("name") or poi.get("name") or poi.get("code", "POI")
        desc_val = (target_loc or {}).get("description") or poi.get("description", "")
        images = poi.get("images", [])
        image_key = (images[0] if images else None) or poi.get("image_key")
        trigger_radius = float(poi.get("trigger_radius") or poi.get("radius_enter_m") or 30.0)
        radius_enter_m = float(poi.get("radius_enter_m") or trigger_radius)
        radius_exit_m = float(poi.get("radius_exit_m") or (trigger_radius * 1.5))
        cooldown_seconds = int(poi.get("cooldown_seconds") or 300)

        loc_data = poi.get("location", {"type": "Point", "coordinates": [106.7035, 10.7655]})
        coords = loc_data.get("coordinates", [106.7035, 10.7655]) if isinstance(loc_data, dict) else [106.7035, 10.7655]
        poi_lon = float(coords[0]) if len(coords) >= 1 else 106.7035
        poi_lat = float(coords[1]) if len(coords) >= 2 else 10.7655

        active_audio = published_contents.get(resolved_lang, {}).get("audio_url") if narration_ready else None
        # Map to client DTO (dual schema compatibility)
        result = {
            "id": poi["_id"],
            "_id": poi["_id"],
            "code": poi.get("code") or name_val,
            "title": name_val,
            "name": name_val,
            "description": desc_val,
            "category": poi.get("category", "attraction"),
            "address": poi.get("address", ""),
            "location": loc_data,
            "latitude": poi_lat,
            "longitude": poi_lon,
            "images": images,
            "image_key": image_key,
            "trigger_radius": trigger_radius,
            "radius_enter_m": radius_enter_m,
            "radius_exit_m": radius_exit_m,
            "cooldown_seconds": cooldown_seconds,
            "audio_priority": poi.get("audio_priority", 1),
            "priority": poi.get("audio_priority", poi.get("priority", 1)),
            "audio_url": active_audio,
            "narration_ready": narration_ready,
            "audio_duration_ms": (target_loc.get("audio_duration_ms", 0) if target_loc else 0) or 0,
            "requested_lang": requested_lang,
            "resolved_lang": resolved_lang,
            "is_fallback": is_fallback,
            "published_contents": published_contents,
            "translations": published_contents,
            "available_languages": list(loc_map.keys()),
            "version": poi.get("version", 1),
        }

        return result


poi_service = POIService()
