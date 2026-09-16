"""Repository for tours collection.

CRITICAL INVARIANT:
- Uses COLLECTION_TOURS ("tours").
- Preserves ordered list of poi_ids.
- Optimistic locking via 'version'.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository
from app.db.collections import COLLECTION_TOURS


class TourRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_TOURS)

    async def list_public_tours(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.collection.find({
            "is_active": True,
            "deleted_at": None,
        }).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)

    async def get_public_tour(self, tour_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({
            "_id": tour_id,
            "is_active": True,
            "deleted_at": None,
        })

    async def create_tour(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc.setdefault("version", 1)
        doc.setdefault("is_active", True)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        doc.setdefault("deleted_at", None)
        await self.collection.insert_one(doc)
        return doc

    async def update_tour(
        self,
        tour_id: str,
        update_fields: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now

        query: Dict[str, Any] = {"_id": tour_id, "deleted_at": None}
        if expected_version is not None:
            query["version"] = expected_version

        return await self.collection.find_one_and_update(
            query,
            {
                "$set": update_fields,
                "$inc": {"version": 1}
            },
            return_document=True
        )

    async def soft_delete(self, tour_id: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"_id": tour_id, "deleted_at": None},
            {"$set": {
                "deleted_at": now,
                "is_active": False,
                "updated_at": now,
            }}
        )
        return res.modified_count > 0


tour_repo = TourRepository()
