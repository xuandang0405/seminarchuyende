"""Repository for MenuItem collection.

CRITICAL INVARIANT:
- Uses COLLECTION_MENU_ITEM ("MenuItem").
- Soft delete via 'deleted_at'.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository
from app.db.collections import COLLECTION_MENU_ITEM


class MenuRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_MENU_ITEM)

    async def find_by_poi(self, poi_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "poi_id": poi_id,
            "deleted_at": None,
        }
        if not include_inactive:
            query["is_active"] = True

        cursor = self.collection.find(query).sort("price", 1)
        return await cursor.to_list(length=100)

    async def get_by_id_active(self, item_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({
            "_id": item_id,
            "deleted_at": None,
        })

    async def create_menu_item(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc.setdefault("version", 1)
        doc.setdefault("is_active", True)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        doc.setdefault("deleted_at", None)
        await self.collection.insert_one(doc)
        return doc

    async def update_menu_item(
        self,
        item_id: str,
        update_fields: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now

        query: Dict[str, Any] = {"_id": item_id, "deleted_at": None}
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

    async def soft_delete(self, item_id: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"_id": item_id, "deleted_at": None},
            {"$set": {
                "deleted_at": now,
                "is_active": False,
                "updated_at": now,
            }}
        )
        return res.modified_count > 0


menu_repo = MenuRepository()
