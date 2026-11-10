"""Repository for Tour Entitlements.

Section 8 & 9 of prompt.
BR-PAY-06..08.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.db.collections import COLLECTION_TOUR_ENTITLEMENTS
from app.repositories.base import BaseRepository


class EntitlementRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_TOUR_ENTITLEMENTS)

    async def create_entitlement(
        self,
        user_id: str,
        tour_id: str,
        source_order_id: str,
        session=None
    ) -> Dict[str, Any]:
        """Idempotently creates an active tour entitlement for a user."""
        now = datetime.now(timezone.utc)
        kwargs = {"session": session} if session else {}
        return await self.collection.find_one_and_update(
            {"user_id": user_id, "tour_id": tour_id},
            {"$set": {"status": "active", "source_order_id": source_order_id,
                      "revoked_at": None, "revocation_reason": None, "updated_at": now},
             "$setOnInsert": {"_id": str(uuid.uuid4()), "user_id": user_id, "tour_id": tour_id, "granted_at": now}},
            upsert=True, return_document=True, **kwargs)

    async def get_entitlement(self, user_id: str, tour_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({
            "user_id": user_id,
            "tour_id": tour_id,
            "status": "active"
        })

    async def list_user_entitlements(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.list(
            query={"user_id": user_id, "status": "active"},
            limit=100,
            sort=[("granted_at", -1)]
        )

    async def revoke_entitlement(self, user_id: str, tour_id: str, reason: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {"user_id": user_id, "tour_id": tour_id, "status": "active"},
            {"$set": {"status": "revoked", "revoked_at": now, "revocation_reason": reason, "updated_at": now}}
        )
        return res.modified_count > 0


entitlement_repo = EntitlementRepository()
