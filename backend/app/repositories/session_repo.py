"""Repository for Visitor Sessions in analytics_sessions.

Implements BR-SESSION-01 / Section 10.2:
- Idempotent start-or-resume per device within inactivity window.
- Conditional heartbeat updating last_seen_at without document proliferation.
- Explicit end and background expiration of inactive sessions.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.db.collections import COLLECTION_ANALYTICS_SESSIONS
from app.repositories.base import BaseRepository

SESSION_INACTIVITY_TIMEOUT_MINUTES = 15


class SessionRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_ANALYTICS_SESSIONS)

    async def start_or_resume_session(
        self,
        device_id: str,
        platform: str = "web",
        app_version: Optional[str] = "1.0.0",
        locale: str = "vi",
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        consent_granted: bool = True,
        consent_version: int = 1,
    ) -> Dict[str, Any]:
        """Starts a new visitor session or resumes an active one for the same device."""
        now = datetime.now(timezone.utc)
        inactivity_threshold = now - timedelta(minutes=SESSION_INACTIVITY_TIMEOUT_MINUTES)

        # Look for existing active session for this device
        existing = await self.collection.find_one(
            {
                "device_id": device_id,
                "status": "active",
                "last_seen_at": {"$gte": inactivity_threshold}
            },
            sort=[("last_seen_at", -1)]
        )

        if existing:
            # Idempotently resume session
            update_fields: Dict[str, Any] = {
                "last_seen_at": now,
                "updated_at": now,
                "platform": platform,
            }
            if user_id and not existing.get("user_id"):
                update_fields["user_id"] = user_id
            if guest_session_id and not existing.get("guest_session_id"):
                update_fields["guest_session_id"] = guest_session_id

            await self.collection.update_one(
                {"_id": existing["_id"]},
                {"$set": update_fields}
            )
            existing.update(update_fields)
            return existing

        # Create new visitor session
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        doc = {
            "_id": session_id,
            "device_id": device_id,
            "user_id": user_id,
            "guest_session_id": guest_session_id,
            "platform": platform,
            "app_version": app_version,
            "locale": locale,
            "started_at": now,
            "last_seen_at": now,
            "ended_at": None,
            "status": "active",
            "consent_granted": consent_granted,
            "consent_version": consent_version,
            "created_at": now,
            "updated_at": now,
        }

        await self.collection.insert_one(doc)
        return doc

    async def heartbeat(self, session_id: str, device_id: str) -> Optional[Dict[str, Any]]:
        """Conditional heartbeat updating last_seen_at with ownership verification."""
        now = datetime.now(timezone.utc)
        res = await self.collection.find_one_and_update(
            {
                "_id": session_id,
                "device_id": device_id,
                "status": "active"
            },
            {
                "$set": {
                    "last_seen_at": now,
                    "updated_at": now
                }
            },
            return_document=True
        )
        return res

    async def end_session(self, session_id: str, device_id: str) -> Optional[Dict[str, Any]]:
        """Explicitly terminates an active visitor session."""
        now = datetime.now(timezone.utc)
        res = await self.collection.find_one_and_update(
            {
                "_id": session_id,
                "device_id": device_id,
                "status": "active"
            },
            {
                "$set": {
                    "status": "ended",
                    "ended_at": now,
                    "updated_at": now
                }
            },
            return_document=True
        )
        return res

    async def expire_inactive_sessions(self, timeout_minutes: int = 15) -> int:
        """Transitions inactive sessions past timeout threshold to expired."""
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(minutes=timeout_minutes)
        res = await self.collection.update_many(
            {
                "status": "active",
                "last_seen_at": {"$lt": threshold}
            },
            {
                "$set": {
                    "status": "expired",
                    "ended_at": now,
                    "updated_at": now
                }
            }
        )
        return res.modified_count


session_repo = SessionRepository()
