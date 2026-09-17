"""Repository for Guest Sessions.

G01 / BR-ACCESS-02.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
import uuid

from app.db.collections import COLLECTION_GUEST_SESSIONS
from app.repositories.base import BaseRepository


class GuestRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_GUEST_SESSIONS)

    async def create_guest_session(
        self,
        credential_hash: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        days_valid: int = 30
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        session_id = str(uuid.uuid4())
        doc = {
            "_id": session_id,
            "credential_hash": credential_hash,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": now,
            "expires_at": now + timedelta(days=days_valid),
            "claimed_user_id": None,
            "claimed_at": None,
            "revoked_at": None
        }
        await self.insert_one(doc)
        return doc

    async def get_by_credential_hash(self, credential_hash: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return await self.find_one({
            "credential_hash": credential_hash,
            "revoked_at": None,
            "expires_at": {"$gt": now}
        })

    async def claim_session(self, guest_session_id: str, user_id: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {
                "_id": guest_session_id,
                "claimed_user_id": None,
                "revoked_at": None
            },
            {
                "$set": {
                    "claimed_user_id": user_id,
                    "claimed_at": now,
                    "revoked_at": now  # Revoke guest credential upon claiming
                }
            }
        )
        return res.modified_count > 0

    async def revoke_session(self, guest_session_id: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"_id": guest_session_id},
            {"$set": {"revoked_at": now}}
        )
        return res.modified_count > 0


guest_repo = GuestRepository()
