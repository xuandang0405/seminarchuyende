"""Repository for audio_tasks and audio metadata.

CRITICAL INVARIANT:
- Uses COLLECTION_AUDIO_TASKS ("audio_tasks") and COLLECTION_POI_LOCALIZATIONS.
- Supports durable leasing, heartbeats, and cancellations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import uuid

from app.repositories.base import BaseRepository
from app.db.collections import COLLECTION_AUDIO_TASKS, COLLECTION_POI_LOCALIZATIONS


class AudioRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_AUDIO_TASKS)

    @property
    def localizations_col(self):
        return self.db[COLLECTION_POI_LOCALIZATIONS]

    async def create_task(
        self,
        requested_by: str,
        items: List[Dict[str, Any]],
        max_attempts: int = 3,
        session=None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": task_id or f"task_{uuid.uuid4().hex[:12]}",
            "requested_by": requested_by,
            "items": items,
            "status": "queued",
            "progress": {"total": len(items), "completed": 0, "failed": 0},
            "attempts": 0,
            "max_attempts": max_attempts,
            "lease_owner": None,
            "lease_until": None,
            "cancel_requested": False,
            "error_message": None,
            "heartbeat_at": now,
            "created_at": now,
            "updated_at": now,
            "expires_at": None,
        }
        options = {"session": session} if session else {}
        if task_id:
            return await self.collection.find_one_and_update(
                {"_id": task_id}, {"$setOnInsert": doc}, upsert=True, return_document=True, **options
            )
        await self.collection.insert_one(doc, **options)
        return doc

    async def claim_task(self, worker_id: str, lease_duration_seconds: int = 60) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_duration_seconds)

        expired = {"status": "running", "lease_until": {"$lte": now}}
        for flag, terminal in (("cancel_requested", "cancelled"), ("pause_requested", "paused")):
            await self.collection.update_many(
                {**expired, flag: True},
                {"$set": {"status": terminal, "lease_owner": None, "lease_until": None, "updated_at": now,
                          "expires_at": now + timedelta(days=7) if terminal == "cancelled" else None}},
            )
        maxed = {"$expr": {"$gte": ["$attempts", "$max_attempts"]}}
        await self.collection.update_many(
            {**expired, **maxed},
            {"$set": {"status": "failed", "lease_owner": None, "lease_until": None, "updated_at": now,
                      "expires_at": now + timedelta(days=7), "error_message": "Worker lease expired"}},
        )
        query = {
            "$or": [
                {"status": "queued", "$or": [{"next_retry_at": None}, {"next_retry_at": {"$lte": now}}]},
                {**expired, "cancel_requested": {"$ne": True}}
            ]
        }
        query["pause_requested"] = {"$ne": True}
        update = {
            "$set": {
                "status": "running",
                "lease_owner": worker_id,
                "lease_until": lease_until,
                "heartbeat_at": now,
                "updated_at": now,
            },
            "$inc": {"attempts": 1}
        }
        return await self.collection.find_one_and_update(query, update, return_document=True)

    async def update_heartbeat(self, task_id: str, worker_id: str, lease_duration_seconds: int = 60) -> bool:
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_duration_seconds)
        res = await self.collection.update_one(
            {"_id": task_id, "lease_owner": worker_id, "status": "running", "lease_until": {"$gt": now}},
            {"$set": {"heartbeat_at": now, "lease_until": lease_until, "updated_at": now}}
        )
        return res.modified_count > 0

    async def finish_task(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
        worker_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        # Set TTL expires_at 7 days after completion
        expires_at = now + timedelta(days=7)

        query = {"_id": task_id, "status": "running", "lease_owner": worker_id, "lease_until": {"$gt": now}}
        if status == "succeeded":
            query.update(cancel_requested={"$ne": True}, pause_requested={"$ne": True})
        return await self.collection.find_one_and_update(
            query,
            {
                "$set": {
                    "status": status,
                    "lease_owner": None,
                    "lease_until": None,
                    "error_message": error_message,
                    "updated_at": now,
                    "expires_at": expires_at,
                }
            },
            return_document=True
        )

    async def request_cancel(self, task_id: str) -> bool:
        now = datetime.now(timezone.utc)
        stopped = await self.collection.update_one(
            {"_id": task_id, "status": {"$in": ["queued", "paused"]}},
            {"$set": {"status": "cancelled", "cancel_requested": True, "pause_requested": False,
                      "updated_at": now, "expires_at": now + timedelta(days=7)}},
        )
        if stopped.matched_count:
            return True
        res = await self.collection.update_one(
            {"_id": task_id, "status": "running"},
            {"$set": {"cancel_requested": True, "pause_requested": False, "updated_at": now}}
        )
        return res.matched_count > 0

    async def request_pause(self, task_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": task_id, "status": "queued", "cancel_requested": {"$ne": True}},
            {"$set": {"status": "paused", "pause_requested": True}},
        )
        if result.matched_count:
            return True
        result = await self.collection.update_one(
            {"_id": task_id, "status": "running", "cancel_requested": {"$ne": True}},
            {"$set": {"pause_requested": True}},
        )
        return bool(result.matched_count)

    async def update_audio_metadata(
        self,
        poi_id: str,
        lang: str,
        audio_url: str,
        audio_storage_key: str,
        audio_content_hash: str,
        audio_duration_ms: int,
        source_version: int,
        audio_source: str = "tts_generated",
        session=None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return await self.localizations_col.find_one_and_update(
            {"poi_id": poi_id, "lang": lang, "source_version": source_version},
            {
                "$set": {
                    "audio_url": audio_url,
                    "audio_storage_key": audio_storage_key,
                    "audio_content_hash": audio_content_hash,
                    "audio_duration_ms": audio_duration_ms,
                    "audio_status": "ready",
                    "audio_source": audio_source,
                    "updated_at": now,
                }
            },
            return_document=True, **({"session": session} if session else {}),
        )


audio_repo = AudioRepository()
