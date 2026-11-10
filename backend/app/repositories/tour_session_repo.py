"""Repository for Tour Sessions in tour_sessions collection.

Implements BR-TOUR-SESSION-01 / Section 10.3:
- Idempotent start with client idempotency_key (double-click/retry protection).
- Progress tracking and state transitions: active -> completed / cancelled / abandoned / expired.
"""

import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.collections import COLLECTION_TOUR_SESSIONS
from app.repositories.base import BaseRepository
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError


class TourSessionRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_TOUR_SESSIONS)

    async def start_tour_session(
        self,
        idempotency_key: str,
        tour_id: str,
        visitor_session_id: str,
        device_id: str,
        start_poi_id: Optional[str] = None,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        tour_version: int = 1,
    ) -> Dict[str, Any]:
        """Starts a new tour session with idempotency key deduplication."""
        now = datetime.now(timezone.utc)

        # 1. Idempotency check: if session with this idempotency_key exists, return it
        scoped_key = hashlib.sha256(f"{device_id}:{idempotency_key}".encode()).hexdigest()
        lookup = {"device_id": device_id, "idempotency_key": {"$in": [scoped_key, idempotency_key]}}
        existing = await self.collection.find_one(lookup)
        if existing:
            if existing["tour_id"] != tour_id or existing["visitor_session_id"] != visitor_session_id:
                raise HTTPException(409, "Mã yêu cầu đã dùng cho một phiên tour khác.")
            return existing

        tour_session_id = f"tsess_{uuid.uuid4().hex[:12]}"
        doc = {
            "_id": tour_session_id,
            "tour_session_id": tour_session_id,
            "tour_id": tour_id,
            "tour_version": tour_version,
            "visitor_session_id": visitor_session_id,
            "device_id": device_id,
            "user_id": user_id,
            "guest_session_id": guest_session_id,
            "idempotency_key": scoped_key,
            "started_at": now,
            "last_activity_at": now,
            "ended_at": None,
            "status": "active",
            "start_poi_id": start_poi_id,
            "last_poi_id": start_poi_id,
            "completed_poi_ids": [],
            "progress_percentage": 0.0,
            "created_at": now,
            "updated_at": now,
        }

        try:
            await self.collection.insert_one(doc)
        except DuplicateKeyError:
            existing = await self.collection.find_one(lookup)
            if not existing or existing["tour_id"] != tour_id or existing["visitor_session_id"] != visitor_session_id:
                raise HTTPException(409, "Mã yêu cầu đã dùng cho một phiên tour khác.")
            return existing
        # Only the most recently started session should remain active for this device.
        winner = await self.collection.find_one({"device_id": device_id, "status": "active"},
                                                sort=[("started_at", -1), ("_id", -1)])
        if winner:
            await self.collection.update_many(
                {"device_id": device_id, "status": "active", "$or": [
                    {"started_at": {"$lt": winner["started_at"]}},
                    {"started_at": winner["started_at"], "_id": {"$lt": winner["_id"]}},
                ]}, {"$set": {"status": "abandoned", "ended_at": now, "updated_at": now}},
            )
        doc = await self.collection.find_one({"_id": tour_session_id})
        return doc

    async def update_progress(
        self,
        tour_session_id: str,
        device_id: str,
        last_poi_id: Optional[str] = None,
        completed_poi_ids: Optional[List[str]] = None,
        progress_percentage: Optional[float] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates progress, visited POIs or state transitions with device ownership check."""
        now = datetime.now(timezone.utc)
        update_fields: Dict[str, Any] = {
            "last_activity_at": now,
            "updated_at": now
        }

        if last_poi_id:
            update_fields["last_poi_id"] = last_poi_id
        if completed_poi_ids is not None:
            update_fields["completed_poi_ids"] = completed_poi_ids
        if progress_percentage is not None:
            update_fields["progress_percentage"] = min(100.0, max(0.0, progress_percentage))

        if status:
            update_fields["status"] = status
            if status != "active":
                update_fields["ended_at"] = now

        res = await self.collection.find_one_and_update(
            {
                "_id": tour_session_id,
                "device_id": device_id,
                "status": "active",
            },
            {"$set": update_fields},
            return_document=True
        )
        return res

    async def get_active_by_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one(
            {"device_id": device_id, "status": "active"},
            sort=[("last_activity_at", -1)]
        )


tour_session_repo = TourSessionRepository()
