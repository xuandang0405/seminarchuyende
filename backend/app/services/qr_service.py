"""Service for QR Code operations.

T11 / C16 / SD05 / AD05.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.repositories.qr_repo import qr_repo
from app.repositories.poi_repo import poi_repo
from app.repositories.tour_repo import tour_repo


class QRService:
    async def resolve_qr_code(self, code: str) -> Dict[str, Any]:
        """Resolves QR code to Tour or POI public info."""
        qr_doc = await qr_repo.find_by_code(code)
        if not qr_doc:
            return {"success": False, "error": "Mã QR không tồn tại hoặc đã bị thu hồi."}

        # Check expiration if configured
        if qr_doc.get("expires_at"):
            now = datetime.now(timezone.utc)
            if qr_doc["expires_at"] < now:
                return {"success": False, "error": "Mã QR đã hết hạn sử dụng."}

        target_type = qr_doc.get("target_type") or ("tour" if qr_doc.get("tour_id") else "poi")

        if target_type == "tour":
            tour_id = qr_doc.get("tour_id") or qr_doc.get("poi_id")
            tour = await tour_repo.get_public_tour(tour_id) or await tour_repo.find_by_id(tour_id)
            if not tour or tour.get("deleted_at"):
                return {"success": False, "error": "Tuyến Tour gắn với mã QR này hiện không hoạt động."}
            return {
                "success": True,
                "type": "tour",
                "target_type": "tour",
                "tour_id": tour["_id"],
                "tour": tour,
                "name": tour.get("name"),
                "description": tour.get("description"),
                "poi_ids": tour.get("poi_ids", []),
                "price_vnd": tour.get("price_vnd") or tour.get("price_amount") or 0,
                "is_paid": tour.get("is_paid", False),
            }

        poi_id = qr_doc.get("poi_id")
        poi = await poi_repo.get_public_by_id(poi_id) or await poi_repo.get_by_id(poi_id)
        if not poi or poi.get("deleted_at"):
            await qr_repo.delete_by_id(qr_doc.get("_id"))
            return {"success": False, "error": "Địa điểm gắn với mã QR này hiện không hoạt động hoặc đã bị xóa."}

        # Fetch localizations
        locs = await poi_repo.get_localizations(poi_id)
        loc_map = {l["lang"]: l for l in locs}

        return {
            "success": True,
            "type": "poi",
            "target_type": "poi",
            "poi_id": poi["_id"],
            "poi": poi,
            "name": poi.get("name"),
            "category": poi.get("category"),
            "address": poi.get("address"),
            "coordinates": poi.get("location", {}).get("coordinates", [106.7042, 10.7635]),
            "audio_url": loc_map.get("vi", {}).get("audio_url") or loc_map.get("en", {}).get("audio_url") or poi.get("audio_url"),
            "audio_duration_ms": loc_map.get("vi", {}).get("audio_duration_ms") or poi.get("audio_duration_ms") or 0,
        }

    async def create_qr_code(
        self,
        poi_id: Optional[str],
        code: str,
        created_by: str,
        location_description: Optional[str] = None,
        tour_id: Optional[str] = None,
        target_type: Optional[str] = "poi"
    ) -> Dict[str, Any]:
        target_type = target_type or ("tour" if tour_id else "poi")

        if target_type == "tour":
            if not tour_id and poi_id:
                tour_id = poi_id
            if not tour_id:
                return {"success": False, "error": "Vui lòng cung cấp tour_id cho mã QR Tour."}
            tour = await tour_repo.get_public_tour(tour_id) or await tour_repo.get_by_id(tour_id)
            if not tour:
                return {"success": False, "error": f"Tour '{tour_id}' không tồn tại."}
            target_name = tour.get("name", tour_id)
        else:
            if not poi_id:
                return {"success": False, "error": "Vui lòng cung cấp poi_id cho mã QR POI."}
            poi = await poi_repo.get_by_id(poi_id) or await poi_repo.get_public_by_id(poi_id)
            if not poi:
                return {"success": False, "error": f"POI '{poi_id}' không tồn tại."}
            target_name = poi.get("name", poi_id)

        existing = await qr_repo.find_by_code(code)
        if existing:
            return {"success": False, "error": f"Mã QR '{code}' đã tồn tại."}

        qr_id = f"qr_{uuid.uuid4().hex[:12]}"
        doc = {
            "_id": qr_id,
            "code": code,
            "target_type": target_type,
            "poi_id": poi_id if target_type == "poi" else None,
            "tour_id": tour_id if target_type == "tour" else None,
            "target_name": target_name,
            "location_description": location_description or ("Mã QR Tuyến Tour" if target_type == "tour" else "Dán tại cổng / bàn"),
            "is_active": True,
            "created_by": created_by,
            "expires_at": None,
        }
        created = await qr_repo.create_qr(doc)
        return {"success": True, "qr": created}

    async def list_qrs(self, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        qrs = await qr_repo.find_all(limit=limit, skip=skip)
        result = []
        poi_cache = {}
        tour_cache = {}
        for qr in qrs:
            item = dict(qr)
            target_type = qr.get("target_type") or ("tour" if qr.get("tour_id") else "poi")
            item["target_type"] = target_type

            if target_type == "tour":
                tour_id = qr.get("tour_id") or qr.get("poi_id")
                tour_name = "Chưa gắn tour"
                if tour_id:
                    if tour_id not in tour_cache:
                        tour = await tour_repo.get_public_tour(tour_id) or await tour_repo.find_by_id(tour_id)
                        tour_cache[tour_id] = tour
                    tour = tour_cache[tour_id]
                    if tour:
                        tour_name = tour.get("name", tour_id)
                item["tour_id"] = tour_id
                item["target_name"] = tour_name
                item["poi_name"] = f"Tour: {tour_name}"
            else:
                poi_id = qr.get("poi_id")
                poi_name = "Chưa gắn POI"
                if poi_id:
                    if poi_id not in poi_cache:
                        poi = await poi_repo.get_by_id(poi_id) or await poi_repo.get_public_by_id(poi_id)
                        poi_cache[poi_id] = poi
                    poi = poi_cache[poi_id]
                    if not poi or poi.get("deleted_at") is not None:
                        await qr_repo.delete_by_id(qr.get("_id"))
                        continue
                    poi_name = poi.get("name", poi_id)
                item["poi_id"] = poi_id
                item["target_name"] = poi_name
                item["poi_name"] = poi_name

            item["id"] = item.get("_id")
            result.append(item)
        return result

    async def activate_qr_code(self, qr_id: str) -> bool:
        return await qr_repo.activate_qr(qr_id)

    async def deactivate_qr_code(self, qr_id: str) -> bool:
        return await qr_repo.deactivate_qr(qr_id)

    async def delete_qr_code(self, qr_id: str) -> bool:
        return await qr_repo.delete_by_id(qr_id)


qr_service = QRService()
