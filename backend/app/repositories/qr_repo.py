"""Repository for qr_codes collection.

CRITICAL INVARIANT:
- Uses COLLECTION_QR_CODES ("qr_codes").
- Code is unique and opaque.
- Service verifies expiration date.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.base import BaseRepository
from app.db.collections import COLLECTION_QR_CODES


class QRRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_QR_CODES)

    def _build_poi_filter(self, poi_id: str) -> Dict[str, Any]:
        if isinstance(poi_id, str) and ObjectId.is_valid(poi_id):
            return {"poi_id": {"$in": [poi_id, ObjectId(poi_id)]}}
        return {"poi_id": poi_id}

    async def find_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({
            "code": code,
            "is_active": True,
        })

    async def find_by_poi(self, poi_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find(self._build_poi_filter(poi_id))
        return await cursor.to_list(length=50)

    async def delete_by_poi(self, poi_id: str) -> int:
        """Permanently deletes all QR codes associated with a POI (cascading deletion)."""
        res = await self.collection.delete_many(self._build_poi_filter(poi_id))
        return res.deleted_count

    async def create_qr(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc.setdefault("version", 1)
        doc.setdefault("is_active", True)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        await self.collection.insert_one(doc)
        return doc

    async def find_all(self, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        cursor = self.collection.find({}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def activate_qr(self, qr_id: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"_id": qr_id},
            {"$set": {"is_active": True, "updated_at": now}}
        )
        return res.modified_count > 0

    async def deactivate_qr(self, qr_id: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"_id": qr_id},
            {"$set": {"is_active": False, "updated_at": now}}
        )
        return res.modified_count > 0


qr_repo = QRRepository()
