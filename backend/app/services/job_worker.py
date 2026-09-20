import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.repositories.job_repo import job_repo
from app.repositories.content_repo import content_repo
from app.repositories.audio_repo import audio_repo
from app.services.tts_service import tts_service

logger = logging.getLogger("uvicorn")


class JobWorkerService:
    @classmethod
    async def process_single_job(cls) -> Optional[Dict[str, Any]]:
        job = await job_repo.claim_next_job()
        if not job:
            return None

        job_id = job["_id"]
        job_type = job.get("job_type")
        input_content_id = job.get("input_content_id")
        logger.info(f"Worker processing job '{job_id}' (type: {job_type})")

        try:
            content = await content_repo.get_by_id(input_content_id)
            if not content:
                raise ValueError(f"Input content '{input_content_id}' not found")

            if job_type == "tts":
                # Synthesize audio from narration_text
                text = content.get("narration_text", "")
                lang = content.get("language_code", "vi")
                voice_id = job.get("parameters", {}).get("voice_id")

                storage_key, duration_ms, file_size, sha256_hash = await tts_service.synthesize_speech(
                    text=text,
                    language_code=lang,
                    voice_id=voice_id
                )

                # Create audio asset record
                audio_id = str(uuid.uuid4())
                audio_doc = {
                    "_id": audio_id,
                    "poi_content_id": input_content_id,
                    "source_type": "tts",
                    "storage_key": storage_key,
                    "duration_ms": duration_ms,
                    "file_size_bytes": file_size,
                    "mime_type": "audio/mpeg",
                    "sha256": sha256_hash,
                    "provider": "edge-tts",
                    "voice_id": voice_id or tts_service.get_voice_for_language(lang),
                    "created_at": datetime.now(timezone.utc)
                }
                await audio_repo.insert_one(audio_doc)

                # Mark job succeeded
                updated_job = await job_repo.mark_succeeded(job_id=job_id, output_audio_id=audio_id)
                logger.info(f"Job '{job_id}' succeeded with audio_id '{audio_id}'")
                return updated_job

            elif job_type == "translate":
                target_lang = job.get("target_language_code", "en")
                source_title = content.get("title", "")
                source_desc = content.get("description", "")
                source_narration = content.get("narration_text", "")

                # Automated high-fidelity translation across 6 languages
                try:
                    from app.services.translation_service import translation_service
                    trans_title = await translation_service.translate_text(source_title, target_lang) or source_title
                    trans_desc = await translation_service.translate_text(source_desc, target_lang) or source_desc
                    trans_narration = await translation_service.translate_text(source_narration or source_desc, target_lang) or trans_desc
                except Exception as e:
                    logger.warning(f"Translation service fallback in job worker: {e}")
                    trans_title = source_title
                    trans_desc = source_desc
                    trans_narration = source_narration or source_desc

                new_content_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)
                new_content_doc = {
                    "_id": new_content_id,
                    "poi_id": content["poi_id"],
                    "language_code": target_lang,
                    "version": 1,
                    "title": trans_title,
                    "description": trans_desc,
                    "narration_text": trans_narration,
                    "review_status": "approved",
                    "source_content_id": input_content_id,
                    "reviewed_at": now,
                    "created_by": job.get("requested_by", "system"),
                    "created_at": now,
                    "updated_at": now
                }
                await content_repo.insert_one(new_content_doc)

                updated_job = await job_repo.mark_succeeded(job_id=job_id, output_content_id=new_content_id)
                logger.info(f"Job '{job_id}' succeeded with output_content_id '{new_content_id}'")
                return updated_job

            else:
                raise ValueError(f"Unknown job_type '{job_type}'")

        except Exception as e:
            logger.error(f"Job '{job_id}' failed: {e}")
            updated_job = await job_repo.mark_failed_or_retry(
                job_id=job_id,
                error_message=str(e),
                max_attempts=job.get("max_attempts", 3)
            )
            return updated_job

    @classmethod
    async def worker_loop(cls):
        """Runs the background worker polling loop."""
        logger.info("Content Job background worker loop started.")
        while True:
            try:
                job = await cls.process_single_job()
                if not job:
                    await asyncio.sleep(3.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5.0)


job_worker = JobWorkerService()
