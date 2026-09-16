"""Repository for audio_tasks and audio metadata.

CRITICAL INVARIANT:
- Uses COLLECTION_AUDIO_TASKS ("audio_tasks") and COLLECTION_POI_LOCALIZATIONS.
- Supports durable leasing, heartbeats, and cancellations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
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
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        doc = {
            "_id": task_id,
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
        await self.collection.insert_one(doc)
        return doc

    async def claim_task(self, worker_id: str, lease_duration_seconds: int = 60) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        lease_until = now + timedelta(seconds=lease_duration_seconds)

        # Claim queued task or expired lease
        query = {
            "$or": [
                {"status": "queued"},
                {"status": "running", "lease_until": {"$lt": now}, "cancel_requested": False}
            ]
        }
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
        from datetime import timedelta
        lease_until = now + timedelta(seconds=lease_duration_seconds)
        res = await self.collection.update_one(
            {"_id": task_id, "lease_owner": worker_id},
            {"$set": {"heartbeat_at": now, "lease_until": lease_until, "updated_at": now}}
        )
        return res.modified_count > 0

    async def finish_task(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        # Set TTL expires_at 7 days after completion
        expires_at = now + timedelta(days=7)

        return await self.collection.find_one_and_update(
            {"_id": task_id},
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
        res = await self.collection.update_one(
            {"_id": task_id, "status": {"$in": ["queued", "running"]}},
            {"$set": {"cancel_requested": True, "updated_at": now}}
        )
        return res.modified_count > 0

    async def update_audio_metadata(
        self,
        poi_id: str,
        lang: str,
        audio_url: str,
        audio_storage_key: str,
        audio_content_hash: str,
        audio_duration_ms: int,
        audio_source: str = "tts_generated"
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return await self.localizations_col.find_one_and_update(
            {"poi_id": poi_id, "lang": lang},
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
            return_document=True
        )


audio_repo = AudioRepository()
