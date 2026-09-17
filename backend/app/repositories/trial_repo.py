"""Repository for Trial Usage with Atomic Operations.

G02 / G03 / BR-TRIAL-01..05.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
import uuid

from app.db.collections import COLLECTION_TRIAL_USAGE
from app.repositories.base import BaseRepository


class TrialRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_TRIAL_USAGE)

    async def get_or_create_usage(
        self,
        subject_type: str,
        subject_id: str,
        policy_version: int = 1
    ) -> Dict[str, Any]:
        """Fetches trial usage document or initializes a new available quota."""
        doc = await self.find_one({
            "subject_type": subject_type,
            "subject_id": subject_id,
            "policy_version": policy_version
        })
        if doc:
            # Check if a pending reservation has expired; if so, recover to available
            if doc.get("state") == "reserved":
                expires_at = doc.get("reservation_expires_at")
                if expires_at and expires_at < datetime.now(timezone.utc):
                    await self.collection.update_one(
                        {"_id": doc["_id"], "state": "reserved"},
                        {"$set": {"state": "available", "reservation_id": None, "updated_at": datetime.now(timezone.utc)}}
                    )
                    doc["state"] = "available"
            return doc

        now = datetime.now(timezone.utc)
        new_doc = {
            "_id": str(uuid.uuid4()),
            "subject_type": subject_type,
            "subject_id": subject_id,
            "policy_version": policy_version,
            "state": "available",  # "available" | "reserved" | "consumed"
            "reservation_id": None,
            "reserved_at": None,
            "reservation_expires_at": None,
            "consumed_at": None,
            "tour_id": None,
            "poi_id": None,
            "lang": None,
            "playback_id": None,
            "created_at": now,
            "updated_at": now
        }
        try:
            await self.insert_one(new_doc)
            return new_doc
        except Exception:
            # In case of concurrent insert race condition
            return await self.find_one({
                "subject_type": subject_type,
                "subject_id": subject_id,
                "policy_version": policy_version
            })

    async def reserve_quota_atomic(
        self,
        subject_type: str,
        subject_id: str,
        policy_version: int,
        tour_id: str,
        poi_id: str,
        lang: str,
        idempotency_key: Optional[str] = None,
        duration_minutes: int = 15
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Atomically reserves the single free trial quota using conditional update."""
        now = datetime.now(timezone.utc)
        reservation_id = idempotency_key or str(uuid.uuid4())
        expires_at = now + timedelta(minutes=duration_minutes)

        # 1. First ensure the document exists
        usage = await self.get_or_create_usage(subject_type, subject_id, policy_version)
        if not usage:
            return False, "CANNOT_INITIALIZE_USAGE", None

        # 2. Check if already reserved with the same idempotency_key/reservation_id
        if usage.get("state") == "reserved" and usage.get("reservation_id") == reservation_id:
            return True, reservation_id, usage

        if usage.get("state") == "consumed":
            return False, "TRIAL_EXHAUSTED", usage

        # 3. Conditional atomic update: state must be 'available' OR ('reserved' with expired time)
        res = await self.collection.find_one_and_update(
            {
                "subject_type": subject_type,
                "subject_id": subject_id,
                "policy_version": policy_version,
                "$or": [
                    {"state": "available"},
                    {"state": "reserved", "reservation_expires_at": {"$lt": now}}
                ]
            },
            {
                "$set": {
                    "state": "reserved",
                    "reservation_id": reservation_id,
                    "reserved_at": now,
                    "reservation_expires_at": expires_at,
                    "tour_id": tour_id,
                    "poi_id": poi_id,
                    "lang": lang,
                    "updated_at": now
                }
            },
            return_document=True
        )

        if res:
            return True, reservation_id, res
        return False, "TRIAL_EXHAUSTED", None

    async def consume_quota_atomic(
        self,
        subject_type: str,
        subject_id: str,
        policy_version: int,
        reservation_id: str,
        playback_id: str
    ) -> bool:
        """Transitions state from 'reserved' to 'consumed' on first media delivery."""
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {
                "subject_type": subject_type,
                "subject_id": subject_id,
                "policy_version": policy_version,
                "state": "reserved",
                "reservation_id": reservation_id
            },
            {
                "$set": {
                    "state": "consumed",
                    "consumed_at": now,
                    "playback_id": playback_id,
                    "updated_at": now
                }
            }
        )
        return res.modified_count > 0

    async def release_quota_atomic(
        self,
        subject_type: str,
        subject_id: str,
        policy_version: int,
        reservation_id: str
    ) -> bool:
        """Rolls back reservation to 'available' if error occurred before media delivery."""
        now = datetime.now(timezone.utc)
        res = await self.collection.update_one(
            {
                "subject_type": subject_type,
                "subject_id": subject_id,
                "policy_version": policy_version,
                "state": "reserved",
                "reservation_id": reservation_id
            },
            {
                "$set": {
                    "state": "available",
                    "reservation_id": None,
                    "reservation_expires_at": None,
                    "updated_at": now
                }
            }
        )
        return res.modified_count > 0

    async def merge_quota_into_user(
        self,
        guest_session_id: str,
        user_id: str,
        policy_version: int = 1
    ) -> Tuple[bool, str]:
        """Idempotently and atomically merges guest trial quota into user account.

        Rule BR-ACCESS-04:
        - If either guest or user is 'consumed', final state is 'consumed'.
        - If both are available, final state is 'available' (no quota stacking).
        """
        now = datetime.now(timezone.utc)
        guest_doc = await self.find_one({
            "subject_type": "guest",
            "subject_id": guest_session_id,
            "policy_version": policy_version
        })
        user_doc = await self.get_or_create_usage("user", user_id, policy_version)

        guest_consumed = guest_doc and guest_doc.get("state") in ("consumed", "reserved")
        user_consumed = user_doc and user_doc.get("state") in ("consumed", "reserved")

        final_state = "consumed" if (guest_consumed or user_consumed) else "available"

        # Update user doc
        await self.collection.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {
                    "state": final_state,
                    "consumed_at": user_doc.get("consumed_at") or (guest_doc.get("consumed_at") if guest_doc else None) or (now if final_state == "consumed" else None),
                    "updated_at": now
                }
            }
        )

        # Deactivate / mark guest record as merged
        if guest_doc:
            await self.collection.update_one(
                {"_id": guest_doc["_id"]},
                {"$set": {"state": "consumed", "merged_into_user_id": user_id, "updated_at": now}}
            )

        return True, final_state


trial_repo = TrialRepository()
