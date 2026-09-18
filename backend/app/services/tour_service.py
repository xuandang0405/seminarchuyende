"""Service for Tour operations.

T12 / T13 / C15 / SD14 / AD14.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.repositories.tour_repo import tour_repo
from app.repositories.poi_repo import poi_repo


class TourService:
    async def list_public_tours(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        tours = await tour_repo.list_public_tours(skip=skip, limit=limit)
        results = []
        for t in tours:
            results.append({
                "id": t["_id"],
                "_id": t["_id"],
                "code": t.get("code") or t["_id"],
                "title": t["name"],
                "name": t["name"],
                "description": t.get("description", ""),
                "localizations": t.get("localizations", {}),
                "poi_count": len(t.get("poi_ids", [])),
                "poi_ids": t.get("poi_ids", []),
                "stops": [{"poi_id": pid, "stop_order": i + 1} for i, pid in enumerate(t.get("poi_ids", []))],
                "version": t.get("version", 1),
            })
        return results

    async def get_tour_detail(self, tour_id: str, lang: str = "vi") -> Optional[Dict[str, Any]]:
        tour = await tour_repo.get_public_tour(tour_id)
        if not tour:
            return None

        # Fetch ordered POIs
        ordered_pois = []
        for pid in tour.get("poi_ids", []):
            p = await poi_repo.get_public_by_id(pid)
            if p:
                ordered_pois.append({
                    "id": p["_id"],
                    "_id": p["_id"],
                    "name": p.get("name"),
                    "category": p.get("category"),
                    "address": p.get("address"),
                    "location": p.get("location"),
                    "images": p.get("images", []),
                })

        return {
            "id": tour["_id"],
            "_id": tour["_id"],
            "code": tour.get("code") or tour["_id"],
            "title": tour["name"],
            "name": tour["name"],
            "description": tour.get("description", ""),
            "localizations": tour.get("localizations", {}),
            "pois": ordered_pois,
            "stops": [{"poi_id": pid, "stop_order": i + 1} for i, pid in enumerate(tour.get("poi_ids", []))],
            "version": tour.get("version", 1),
        }

    async def create_tour(self, payload: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        poi_ids = payload.get("poi_ids", [])
        # Verify all POIs exist
        for pid in poi_ids:
            exists = await poi_repo.get_by_id(pid)
            if not exists:
                return {"success": False, "error": f"POI '{pid}' không tồn tại."}

        tour_id = f"tour_{uuid.uuid4().hex[:12]}"
        doc = {
            "_id": tour_id,
            "name": payload["name"],
            "description": payload.get("description", ""),
            "localizations": payload.get("localizations", {}),
            "poi_ids": poi_ids,
            "is_active": payload.get("is_active", True),
            "created_by": created_by,
        }
        created = await tour_repo.create_tour(doc)
        return {"success": True, "tour": created}

    async def update_tour(
        self,
        tour_id: str,
        payload: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        updated = await tour_repo.update_tour(tour_id, payload, expected_version)
        if not updated:
            return {"success": False, "error": "Xung đột phiên bản tour (Version conflict)."}
        if "poi_ids" in payload:
            from app.repositories.route_cache_repo import route_cache_repo
            await route_cache_repo.invalidate_all()
        return {"success": True, "tour": updated}

    async def delete_tour(self, tour_id: str) -> bool:
        return await tour_repo.soft_delete(tour_id)


tour_service = TourService()
