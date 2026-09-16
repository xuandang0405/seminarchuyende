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

    async def get_nearby_pois(
        self,
        longitude: float,
        latitude: float,
        max_distance_meters: float = 1000.0,
        category: Optional[str] = None,
        limit: int = 50,
        lang: str = "vi"
    ) -> List[Dict[str, Any]]:
        """Geospatial nearby POIs with localization."""
        pois = await poi_repo.find_nearby(
            longitude=longitude,
            latitude=latitude,
            max_distance_meters=max_distance_meters,
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

        # Build published_contents map for multi-language legacy access
        published_contents = {}
        for l_code, l_doc in loc_map.items():
            published_contents[l_code] = {
                "title": l_doc.get("name", poi.get("name")),
                "description": l_doc.get("description", poi.get("description")),
                "narration_text": l_doc.get("description", poi.get("description")),
                "audio_url": l_doc.get("audio_url"),
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
            "location": poi.get("location", {"type": "Point", "coordinates": [106.7035, 10.7655]}),
            "images": images,
            "image_key": image_key,
            "trigger_radius": trigger_radius,
            "radius_enter_m": radius_enter_m,
            "radius_exit_m": radius_exit_m,
            "cooldown_seconds": cooldown_seconds,
            "audio_priority": poi.get("audio_priority", 1),
            "audio_url": target_loc.get("audio_url") if target_loc else None,
            "audio_duration_ms": target_loc.get("audio_duration_ms", 0) if target_loc else 0,
            "requested_lang": requested_lang,
            "resolved_lang": resolved_lang,
            "is_fallback": is_fallback,
            "published_contents": published_contents,
            "version": poi.get("version", 1),
        }

        if include_all_localizations:
            result["available_languages"] = list(loc_map.keys())

        return result


poi_service = POIService()
