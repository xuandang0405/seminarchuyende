"""Service for Public POI viewing, searching, nearby calculation, and language fallback.

AD01 / SD01 / T01 / T04 / T05 / N01.
"""

from typing import Any, Dict, List, Optional
from app.repositories.poi_repo import poi_repo


class POIService:
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
        poi_id = poi["_id"]
        
        # Fast path: Check embedded translations to eliminate N+1 DB round-trips
        poi_trans = poi.get("translations") or poi.get("published_contents") or {}
        if poi_trans and isinstance(poi_trans, dict) and len(poi_trans) > 0:
            loc_map = {}
            for l_code, t_doc in poi_trans.items():
                if isinstance(t_doc, dict):
                    loc_map[l_code] = {
                        "lang": l_code,
                        "name": t_doc.get("name") or t_doc.get("title") or poi.get("name"),
                        "description": t_doc.get("description") or poi.get("description"),
                        "audio_url": t_doc.get("audio_url"),
                        "audio_duration_ms": t_doc.get("audio_duration_ms", 12000),
                    }
        else:
            locs = await poi_repo.get_localizations(poi_id)
            loc_map = {l["lang"]: l for l in locs}

        resolved_lang = requested_lang
        is_fallback = False
        target_loc = loc_map.get(requested_lang)

        if not target_loc:
            # Fallback to en, then vi
            if "en" in loc_map:
                target_loc = loc_map["en"]
                resolved_lang = "en"
                is_fallback = (requested_lang != "en")
            elif "vi" in loc_map:
                target_loc = loc_map["vi"]
                resolved_lang = "vi"
                is_fallback = (requested_lang != "vi")

        # Build published_contents map for multi-language access
        published_contents = {}
        for l_code, l_doc in loc_map.items():
            published_contents[l_code] = {
                "title": l_doc.get("name", poi.get("name")),
                "name": l_doc.get("name", poi.get("name")),
                "description": l_doc.get("description", poi.get("description")),
                "narration_text": l_doc.get("description", poi.get("description")),
                "audio_url": l_doc.get("audio_url") or f"/storage/audio/{poi_id}_{l_code}.mp3",
                "audio_asset_id": l_doc.get("audio_asset_id") or f"audio_{poi_id}_{l_code}",
                "duration_ms": l_doc.get("audio_duration_ms", 0),
            }

        name_val = target_loc["name"] if target_loc else poi.get("name", poi.get("code", "POI"))
        desc_val = target_loc["description"] if target_loc else poi.get("description", "")
        images = poi.get("images", [])
        image_key = (images[0] if images else None) or poi.get("image_key")
        trigger_radius = float(poi.get("trigger_radius") or poi.get("radius_enter_m") or 30.0)
        radius_enter_m = float(poi.get("radius_enter_m") or trigger_radius)
        radius_exit_m = float(poi.get("radius_exit_m") or (trigger_radius * 1.5))
        cooldown_seconds = int(poi.get("cooldown_seconds") or 60)

        loc_data = poi.get("location", {"type": "Point", "coordinates": [106.7035, 10.7655]})
        coords = loc_data.get("coordinates", [106.7035, 10.7655]) if isinstance(loc_data, dict) else [106.7035, 10.7655]
        poi_lon = float(coords[0]) if len(coords) >= 1 else 106.7035
        poi_lat = float(coords[1]) if len(coords) >= 2 else 10.7655

        # Audio URL for requested/resolved language
        active_audio = (
            (target_loc.get("audio_url") if target_loc else None)
            or published_contents.get(resolved_lang, {}).get("audio_url")
            or f"/storage/audio/{poi_id}_{resolved_lang}.mp3"
            or poi.get("audio_url")
        )

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
            "audio_url": active_audio,
            "audio_duration_ms": (target_loc.get("audio_duration_ms", 0) if target_loc else 0) or poi.get("audio_duration_ms", 12000),
            "requested_lang": requested_lang,
            "resolved_lang": resolved_lang,
            "is_fallback": is_fallback,
            "published_contents": published_contents,
            "translations": published_contents,
            "available_languages": list(set(list(loc_map.keys()) + ["vi", "en", "fr", "ja", "ko", "zh"])),
            "version": poi.get("version", 1),
        }

        return result


poi_service = POIService()
