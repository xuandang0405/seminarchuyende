"""Repository for Owner operations:
- poi_owner_registrations
- poi_submissions
- owner_notifications
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.repositories.base import BaseRepository
from app.db.collections import (
    COLLECTION_POI_OWNER_REGISTRATIONS,
    COLLECTION_POI_SUBMISSIONS,
    COLLECTION_OWNER_NOTIFICATIONS,
    COLLECTION_ADMIN_USERS,
)


class OwnerRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_POI_OWNER_REGISTRATIONS)

    @property
    def submissions_col(self):
        return self.db[COLLECTION_POI_SUBMISSIONS]

    @property
    def notifications_col(self):
        return self.db[COLLECTION_OWNER_NOTIFICATIONS]

    @property
    def users_col(self):
        return self.db[COLLECTION_ADMIN_USERS]

    # =========================================================================
    # REGISTRATIONS (poi_owner_registrations)
    # =========================================================================

    async def create_registration(self, user_id: str, business_name: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": f"reg_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "business_name": business_name,
            "status": "pending",
            "admin_note": None,
            "reviewed_by": None,
            "submitted_at": now,
            "reviewed_at": None,
            "version": 1,
        }
        await self.collection.insert_one(doc)
        return doc

    async def get_registration_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"user_id": user_id})

    async def list_pending_registrations(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"status": "pending"}).skip(skip).limit(limit).sort("submitted_at", -1)
        return await cursor.to_list(length=limit)

    async def review_registration(
        self,
        registration_id: str,
        status: str,
        admin_id: str,
        admin_note: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        query: Dict[str, Any] = {"_id": registration_id}
        if expected_version is not None:
            query["version"] = expected_version

        updated = await self.collection.find_one_and_update(
            query,
            {
                "$set": {
                    "status": status,
                    "admin_note": admin_note,
                    "reviewed_by": admin_id,
                    "reviewed_at": now,
                },
                "$inc": {"version": 1}
            },
            return_document=True
        )

        if updated and status == "approved":
            # Set is_poi_owner_verified = True in admin_users
            await self.users_col.update_one(
                {"_id": updated["user_id"]},
                {"$set": {"is_poi_owner_verified": True, "updated_at": now}}
            )

        return updated

    # =========================================================================
    # SUBMISSIONS (poi_submissions)
    # =========================================================================

    async def create_submission(
        self,
        owner_id: str,
        action: str,
        payload: Dict[str, Any],
        poi_id: Optional[str] = None,
        request_key: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": f"sub_{uuid.uuid4().hex[:12]}",
            "owner_id": owner_id,
            "poi_id": poi_id,
            "action": action,
            "payload": payload,
            "status": "pending",
            "admin_note": None,
            "reviewed_by": None,
            "created_at": now,
            "reviewed_at": None,
            "version": 1,
            "request_key": request_key,
        }
        await self.submissions_col.insert_one(doc)
        return doc

    async def list_submissions(
        self,
        owner_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if owner_id:
            query["owner_id"] = owner_id
        if status:
            query["status"] = status
        cursor = self.submissions_col.find(query).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)

    async def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        return await self.submissions_col.find_one({"_id": submission_id})

    async def review_submission(
        self,
        submission_id: str,
        status: str,
        admin_id: str,
        admin_note: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        query: Dict[str, Any] = {"_id": submission_id}
        if expected_version is not None:
            query["version"] = expected_version

        return await self.submissions_col.find_one_and_update(
            query,
            {
                "$set": {
                    "status": status,
                    "admin_note": admin_note,
                    "reviewed_by": admin_id,
                    "reviewed_at": now,
                },
                "$inc": {"version": 1}
            },
            return_document=True
        )

    # =========================================================================
    # NOTIFICATIONS (owner_notifications)
    # =========================================================================

    async def create_notification(
        self,
        owner_id: str,
        type: str,
        message: str,
        submission_id: Optional[str] = None,
        registration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": f"notif_{uuid.uuid4().hex[:12]}",
            "owner_id": owner_id,
            "submission_id": submission_id,
            "registration_id": registration_id,
            "type": type,
            "message": message,
            "is_read": False,
            "created_at": now,
        }
        await self.notifications_col.insert_one(doc)
        return doc

    async def list_notifications(self, owner_id: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.notifications_col.find({"owner_id": owner_id}).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)

    async def mark_notification_read(self, notif_id: str, owner_id: str) -> bool:
        res = await self.notifications_col.update_one(
            {"_id": notif_id, "owner_id": owner_id},
            {"$set": {"is_read": True}}
        )
        return res.modified_count > 0


owner_repo = OwnerRepository()
