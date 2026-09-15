from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository):
    def __init__(self):
        super().__init__("content_jobs")

    async def claim_next_job(self) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        # Atomically find a queued job or a retry-eligible job and set to running
        query = {
            "status": "queued",
            "$or": [
                {"next_retry_at": None},
                {"next_retry_at": {"$lte": now}}
            ]
        }
        update = {
            "$set": {
                "status": "running",
                "started_at": now,
                "updated_at": now
            },
            "$inc": {"attempts": 1}
        }
        doc = await self.collection.find_one_and_update(
            query,
            update,
            return_document=True
        )
        return doc

    async def mark_succeeded(
        self,
        job_id: str,
        output_content_id: Optional[str] = None,
        output_audio_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update: Dict[str, Any] = {
            "status": "succeeded",
            "finished_at": now,
            "updated_at": now,
            "error_message": None
        }
        if output_content_id:
            update["output_content_id"] = output_content_id
        if output_audio_id:
            update["output_audio_id"] = output_audio_id

        await self.collection.update_one({"_id": job_id}, {"$set": update})
        return await self.get_by_id(job_id)

    async def mark_failed_or_retry(
        self,
        job_id: str,
        error_message: str,
        max_attempts: int = 3
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        job = await self.get_by_id(job_id)
        if not job:
            return None

        attempts = job.get("attempts", 1)
        if attempts >= max_attempts:
            # Mark permanently failed
            update = {
                "status": "failed",
                "finished_at": now,
                "updated_at": now,
                "error_message": error_message
            }
        else:
            # Schedule retry with exponential backoff (e.g. 15s * attempts)
            retry_delay = 15 * attempts
            update = {
                "status": "queued",
                "next_retry_at": now + timedelta(seconds=retry_delay),
                "updated_at": now,
                "error_message": f"[Attempt {attempts}] {error_message}"
            }

        await self.collection.update_one({"_id": job_id}, {"$set": update})
        return await self.get_by_id(job_id)


job_repo = JobRepository()
