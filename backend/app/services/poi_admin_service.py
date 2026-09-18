"""Service for Admin POI operations, optimistic concurrency, and publication readiness gate.

C01 / C02 / C03 / C04 / SD03 / AD03.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.repositories.poi_repo import poi_repo


class POIAdminService:
    async def create_poi(self, payload: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Creates a new POI with UUID string ID."""
        poi_id = f"poi_{uuid.uuid4().hex[:12]}"
        poi_doc = {
            "_id": poi_id,
            "owner_id": payload.get("owner_id"),
            "name": payload["name"],
            "description": payload["description"],
            "category": payload.get("category", "sightseeing"),
            "address": payload.get("address", ""),
            "location": payload["location"],  # GeoJSON Point
            "images": payload.get("images", []),
            "trigger_radius": float(payload.get("trigger_radius", 30.0)),
            "audio_priority": int(payload.get("audio_priority", 1)),
            "audio_status": "none",
            "is_active": False,  # Initially false until readiness gate passed
            "activation_requested": bool(payload.get("activation_requested", False)),
            "source_lang": payload.get("source_lang", "vi"),
        }

        created = await poi_repo.create_poi(poi_doc)

        # Initialize default source localization (e.g. vi)
        loc_doc = {
            "_id": f"{poi_id}_{poi_doc['source_lang']}",
            "poi_id": poi_id,
            "lang": poi_doc["source_lang"],
            "name": poi_doc["name"],
            "description": poi_doc["description"],
            "audio_url": None,
            "audio_storage_key": None,
            "audio_content_hash": None,
            "audio_duration_ms": 0,
            "translation_status": "ready",
            "audio_status": "none",
            "audio_source": "none",
            "version": 1,
            "source_version": 1,
            "active_task_id": None,
            "last_error": None,
        }
        await poi_repo.upsert_localization(loc_doc)

        return created

    async def update_poi(
        self,
        poi_id: str,
        update_fields: Dict[str, Any],
        expected_version: int,
        content_changed: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Updates POI with optimistic concurrency check."""
        updated = await poi_repo.update_poi_with_version(
            poi_id=poi_id,
            update_fields=update_fields,
            expected_version=expected_version,
            content_changed=content_changed
        )
        if updated and ("location" in update_fields or "coordinates" in update_fields):
            from app.repositories.route_cache_repo import route_cache_repo
            await route_cache_repo.invalidate_all()
        return updated

    async def soft_delete_poi(self, poi_id: str) -> bool:
        return await poi_repo.soft_delete(poi_id)

    async def toggle_activation(self, poi_id: str, request_active: bool) -> Dict[str, Any]:
        """
        Manages POI publication with the Readiness Gate check.
        Readiness Gate requirement:
        - Valid English (en) content and audio ready for the current content_version.
        """
        poi = await poi_repo.get_by_id(poi_id)
        if not poi:
            return {"success": False, "error": "POI not found"}

        if not request_active:
            # Turning off publication is always permitted
            await poi_repo.update_by_id(poi_id, {
                "is_active": False,
                "activation_requested": False
            })
            return {
                "success": True,
                "is_active": False,
                "activation_requested": False,
                "message": "POI deactivated successfully."
            }

        # Requesting activation: evaluate Readiness Gate
        locs = await poi_repo.get_localizations(poi_id)
        en_loc = next((l for l in locs if l["lang"] == "en"), None)

        readiness_passed = False
        reasons = []

        if not en_loc:
            reasons.append("Chưa có bản dịch tiếng Anh (English translation required)")
        else:
            if not en_loc.get("name") or not en_loc.get("description"):
                reasons.append("Bản dịch tiếng Anh chưa hoàn chỉnh")
            if en_loc.get("audio_status") != "ready" or not en_loc.get("audio_url"):
                reasons.append("Audio thuyết minh tiếng Anh chưa sẵn sàng (Audio not ready)")

        if not reasons:
            readiness_passed = True

        if readiness_passed:
            await poi_repo.update_by_id(poi_id, {
                "is_active": True,
                "activation_requested": True
            })
            return {
                "success": True,
                "is_active": True,
                "activation_requested": True,
                "message": "POI đã vượt qua readiness gate và được công bố công khai."
            }
        else:
            # Keep activation_requested = True, but is_active = False (preparing)
            await poi_repo.update_by_id(poi_id, {
                "is_active": False,
                "activation_requested": True
            })
            return {
                "success": False,
                "is_active": False,
                "activation_requested": True,
                "gate_passed": False,
                "reasons": reasons,
                "message": "POI đang ở trạng thái chuẩn bị. Cần hoàn tất bản dịch và audio tiếng Anh trước khi công bố."
            }


poi_admin_service = POIAdminService()
