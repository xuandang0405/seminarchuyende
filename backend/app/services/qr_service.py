"""Service for QR Code operations.

T11 / C16 / SD05 / AD05.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.repositories.qr_repo import qr_repo
from app.repositories.poi_repo import poi_repo


class QRService:
    async def resolve_qr_code(self, code: str) -> Dict[str, Any]:
        """Resolves QR code to POI public info."""
        qr_doc = await qr_repo.find_by_code(code)
        if not qr_doc:
            return {"success": False, "error": "Mã QR không tồn tại hoặc đã bị thu hồi."}

        # Check expiration if configured
        if qr_doc.get("expires_at"):
            now = datetime.now(timezone.utc)
            if qr_doc["expires_at"] < now:
                return {"success": False, "error": "Mã QR đã hết hạn sử dụng."}

        poi_id = qr_doc["poi_id"]
        poi = await poi_repo.get_public_by_id(poi_id)
        if not poi:
            return {"success": False, "error": "Địa điểm gắn với mã QR này hiện không hoạt động."}

        # Fetch localizations
        locs = await poi_repo.get_localizations(poi_id)
        loc_map = {l["lang"]: l for l in locs}

        return {
            "success": True,
            "poi_id": poi["_id"],
            "name": poi.get("name"),
            "category": poi.get("category"),
            "address": poi.get("address"),
            "audio_url": loc_map.get("vi", {}).get("audio_url") or loc_map.get("en", {}).get("audio_url"),
            "audio_duration_ms": loc_map.get("vi", {}).get("audio_duration_ms") or 0,
        }

    async def create_qr_code(
        self,
        poi_id: str,
        code: str,
        created_by: str,
        location_description: Optional[str] = None
    ) -> Dict[str, Any]:
        poi = await poi_repo.get_by_id(poi_id)
        if not poi:
            poi = await poi_repo.get_public_by_id(poi_id)
        if not poi:
            return {"success": False, "error": f"POI '{poi_id}' không tồn tại."}

        existing = await qr_repo.find_by_code(code)
        if existing:
            return {"success": False, "error": f"Mã QR '{code}' đã tồn tại."}

        qr_id = f"qr_{uuid.uuid4().hex[:12]}"
        doc = {
            "_id": qr_id,
            "code": code,
            "poi_id": poi_id,
            "location_description": location_description or "Dán tại cổng / bàn",
            "is_active": True,
            "created_by": created_by,
            "expires_at": None,
        }
        created = await qr_repo.create_qr(doc)
        return {"success": True, "qr": created}

    async def deactivate_qr_code(self, qr_id: str) -> bool:
        return await qr_repo.deactivate_qr(qr_id)


qr_service = QRService()
