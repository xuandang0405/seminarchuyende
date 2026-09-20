"""Repository for tours collection.

CRITICAL INVARIANT:
- Uses COLLECTION_TOURS ("tours").
- Preserves ordered list of poi_ids.
- Optimistic locking via 'version'.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository, build_id_filter, serialize_mongo_doc
from app.db.collections import COLLECTION_TOURS


class TourRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_TOURS)

    async def list_public_tours(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.collection.find({
            "is_active": True,
            "deleted_at": None,
        }).skip(skip).limit(limit).sort("created_at", -1)
        items = await cursor.to_list(length=limit)
        return [serialize_mongo_doc(it) for it in items]

    async def get_public_tour(self, tour_id: str) -> Optional[Dict[str, Any]]:
        query = build_id_filter(tour_id)
        query["is_active"] = True
        query["deleted_at"] = None
        doc = await self.collection.find_one(query)
        return serialize_mongo_doc(doc)

    async def find_by_id(self, tour_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_by_id(tour_id)

    async def create_tour(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc.setdefault("version", 1)
        doc.setdefault("is_active", True)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        doc.setdefault("deleted_at", None)
        await self.collection.insert_one(doc)
        return serialize_mongo_doc(doc)

    async def update_tour(
        self,
        tour_id: str,
        update_fields: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now

        query: Dict[str, Any] = build_id_filter(tour_id)
        query["deleted_at"] = None
        if expected_version is not None:
            query["version"] = expected_version

        res = await self.collection.find_one_and_update(
            query,
            {
                "$set": update_fields,
                "$inc": {"version": 1}
            },
            return_document=True
        )
        return serialize_mongo_doc(res)

    async def soft_delete(self, tour_id: str) -> bool:
        now = datetime.now(timezone.utc)
        query = build_id_filter(tour_id)
        query["deleted_at"] = None
        res = await self.collection.update_one(
            query,
            {"$set": {
                "deleted_at": now,
                "is_active": False,
                "updated_at": now,
            }}
        )
        return res.modified_count > 0

    async def update_tour_pricing(
        self,
        tour_id: str,
        price_amount: int,
        currency: str = "VND",
        is_purchasable: bool = True,
        preview_enabled: bool = True,
        preview_poi_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update_fields: Dict[str, Any] = {
            "price_amount": price_amount,
            "currency": currency,
            "is_purchasable": is_purchasable,
            "preview_enabled": preview_enabled,
            "updated_at": now
        }
        if preview_poi_ids is not None:
            update_fields["preview_poi_ids"] = preview_poi_ids

        query = build_id_filter(tour_id)
        query["deleted_at"] = None
        res = await self.collection.find_one_and_update(
            query,
            {
                "$set": update_fields,
                "$inc": {"pricing_version": 1, "version": 1}
            },
            return_document=True
        )
        return serialize_mongo_doc(res)


tour_repo = TourRepository()

