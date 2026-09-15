from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository


class OwnerRepository(BaseRepository):
    def __init__(self):
        super().__init__("admin_users")

    @property
    def submissions_collection(self):
        return self.db["owner_submissions"]

    async def list_pending_owners(self) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"role": "owner", "owner_status": "pending"})
        return await cursor.to_list(length=100)

    async def update_owner_status(
        self,
        owner_id: str,
        status: str,
        admin_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update = {
            "owner_status": status,
            "admin_notes": admin_notes,
            "updated_at": now
        }
        await self.collection.update_one({"_id": owner_id}, {"$set": update})
        return await self.get_by_id(owner_id)

    async def create_submission(self, sub_doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.submissions_collection.insert_one(sub_doc)
        return sub_doc

    async def list_submissions(
        self,
        owner_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if owner_id:
            query["owner_id"] = owner_id
        if status:
            query["status"] = status
        cursor = self.submissions_collection.find(query).sort([("created_at", -1)])
        return await cursor.to_list(length=100)

    async def review_submission(
        self,
        submission_id: str,
        status: str,
        admin_id: str,
        admin_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update = {
            "status": status,
            "reviewed_by": admin_id,
            "reviewed_at": now,
            "admin_notes": admin_notes,
            "updated_at": now
        }
        await self.submissions_collection.update_one({"_id": submission_id}, {"$set": update})
        return await self.submissions_collection.find_one({"_id": submission_id})


owner_repo = OwnerRepository()
