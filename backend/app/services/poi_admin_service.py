"""Service for Admin POI operations, optimistic concurrency, and publication readiness gate.

C01 / C02 / C03 / C04 / SD03 / AD03.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import BackgroundTasks

from app.repositories.poi_repo import poi_repo

logger = logging.getLogger("uvicorn")


async def background_sync_poi_multilingual(poi_id: str, name: str, description: str, session=None):
    """Enqueue durable multilingual work in the same transaction as the POI."""
    from app.repositories.audio_repo import audio_repo
    poi = await poi_repo.get_by_id(poi_id, session=session)
    if poi and not poi.get("deleted_at"):
        return await audio_repo.create_task("system", [{"poi_id": poi_id, "input_version": poi.get("content_version", 1)}], session=session)


class POIAdminService:
    async def create_poi(
        self,
        payload: Dict[str, Any],
        created_by: str,
        background_tasks: Optional[BackgroundTasks] = None,
        session=None
    ) -> Dict[str, Any]:
        """Commit the POI, source localization and queued work together."""
        from app.core.database import db_manager
        from app.services.unit_of_work import run_transaction
        if session is None and not db_manager.is_mock:
            return await run_transaction(lambda s: self.create_poi(payload, created_by, background_tasks, session=s))
        poi_id = f"poi_{uuid.uuid4().hex[:12]}"
        audio_url = payload.get("audio_url")
        audio_duration_ms = payload.get("audio_duration_ms", 0)
        audio_status = "ready" if audio_url else "none"

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
            "audio_url": audio_url,
            "audio_duration_ms": audio_duration_ms,
            "audio_status": audio_status,
            "is_active": False,
            "activation_requested": bool(payload.get("activation_requested", True)),
            "source_lang": payload.get("source_lang", "vi"),
        }

        created = await poi_repo.create_poi(poi_doc, session=session)

        # Initialize default source localization (e.g. vi)
        loc_doc = {
            "_id": f"{poi_id}_{poi_doc['source_lang']}",
            "poi_id": poi_id,
            "lang": poi_doc["source_lang"],
            "name": poi_doc["name"],
            "description": poi_doc["description"],
            "audio_url": audio_url,
            "audio_storage_key": None,
            "audio_content_hash": None,
            "audio_duration_ms": audio_duration_ms,
            "translation_status": "ready",
            "audio_status": audio_status,
            "audio_source": "tts" if audio_url else "none",
            "version": 1,
            "source_version": 1,
            "active_task_id": None,
            "last_error": None,
        }
        await poi_repo.upsert_localization(loc_doc, session=session)

        await background_sync_poi_multilingual(poi_id, poi_doc["name"], poi_doc["description"], session=session)
        return created

    async def update_poi(
        self,
        poi_id: str,
        update_fields: Dict[str, Any],
        expected_version: int,
        content_changed: bool = False,
        session=None
    ) -> Optional[Dict[str, Any]]:
        """Updates POI with optimistic concurrency check."""
        from app.core.database import db_manager
        from app.services.unit_of_work import run_transaction
        if session is None and not db_manager.is_mock:
            return await run_transaction(lambda s: self.update_poi(poi_id, dict(update_fields), expected_version, content_changed, session=s))
        previous = await poi_repo.get_by_id(poi_id, session=session)
        if content_changed:
            update_fields.update(is_active=False, activation_requested=bool(previous and (previous.get("is_active") or previous.get("activation_requested"))),
                                 audio_url=None, audio_status="processing", translations={}, published_contents={})
        updated = await poi_repo.update_poi_with_version(
            poi_id=poi_id,
            update_fields=update_fields,
            expected_version=expected_version,
            content_changed=content_changed,
            session=session
        )
        if updated and ("location" in update_fields or "coordinates" in update_fields):
            from app.repositories.route_cache_repo import route_cache_repo
            await route_cache_repo.invalidate_all()
        if updated and content_changed:
            await poi_repo.localizations_collection.update_many({"poi_id": poi_id},
                {"$set": {"audio_url": None, "audio_status": "processing", "translation_status": "pending"}},
                **({"session": session} if session else {}))
            await background_sync_poi_multilingual(poi_id, updated.get("name", ""), updated.get("description", ""), session=session)
        return updated

    async def soft_delete_poi(self, poi_id: str) -> bool:
        deleted = await poi_repo.soft_delete(poi_id)
        if deleted:
            await poi_repo.localizations_collection.delete_many({"poi_id": poi_id})
            from app.repositories.qr_repo import qr_repo
            deleted_qrs = await qr_repo.delete_by_poi(poi_id)
            logger.info(f"Cascaded deletion: Deleted {deleted_qrs} QR codes associated with POI {poi_id}")
            from app.repositories.route_cache_repo import route_cache_repo
            await route_cache_repo.invalidate_all()
        return deleted

    async def toggle_activation(self, poi_id: str, request_active: bool, expected_version=None, automatic=False) -> Dict[str, Any]:
        """
        Manages POI publication with the Readiness Gate check.
        Readiness Gate requirement:
        - Valid English (en) content and audio ready for the current content_version.
        """
        poi = await poi_repo.get_by_id(poi_id)
        if not poi or poi.get("deleted_at"):
            return {"success": False, "error": "POI not found"}
        version = poi.get("content_version", 1)
        if (expected_version is not None and version != expected_version) or (automatic and not poi.get("activation_requested")):
            return {"success": False, "error": "Yêu cầu công bố đã thay đổi."}

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
        en_loc = next((l for l in locs if l.get("lang") == "en"), None)

        readiness_passed = False
        reasons = []

        if not en_loc:
            reasons.append("Chưa có bản dịch tiếng Anh (English translation required)")
        else:
            if en_loc.get("source_version") != poi.get("content_version", 1):
                reasons.append("Bản dịch/audio không thuộc phiên bản nội dung hiện tại")
            if not en_loc.get("name") or not en_loc.get("description"):
                reasons.append("Bản dịch tiếng Anh chưa hoàn chỉnh")
            if en_loc.get("audio_status") != "ready" or not en_loc.get("audio_url"):
                reasons.append("Audio thuyết minh tiếng Anh chưa sẵn sàng (Audio not ready)")
            else:
                from pathlib import Path
                from app.services.audio_service import audio_service
                key = en_loc.get("audio_storage_key") or en_loc["audio_url"].split("?", 1)[0].removeprefix("/storage/")
                key = key.removeprefix("/api/v1/audio/").removesuffix("/stream")
                try:
                    if not Path(audio_service.get_audio_filepath(key)).is_file():
                        reasons.append("File audio tiếng Anh không tồn tại")
                except Exception:
                    reasons.append("Đường dẫn audio tiếng Anh không hợp lệ")

        if not reasons:
            readiness_passed = True

        query = poi_repo.content_query(poi_id, version)
        query["localization_revision"] = poi.get("localization_revision")
        if automatic:
            query["activation_requested"] = True
        updated = await poi_repo.collection.update_one(query, {"$set": {
            "is_active": readiness_passed, "activation_requested": True, "updated_at": datetime.now(timezone.utc),
        }})
        if not updated.matched_count:
            return {"success": False, "error": "Nội dung đã thay đổi. Vui lòng thử lại."}
        if readiness_passed:
            return {
                "success": True,
                "is_active": True,
                "activation_requested": True,
                "message": "POI đã vượt qua readiness gate và được công bố công khai."
            }
        else:
            # Keep activation_requested = True, but is_active = False (preparing)
            return {
                "success": False,
                "is_active": False,
                "activation_requested": True,
                "gate_passed": False,
                "reasons": reasons,
                "message": "POI đang ở trạng thái chuẩn bị. Cần hoàn tất bản dịch và audio tiếng Anh trước khi công bố."
            }


poi_admin_service = POIAdminService()
