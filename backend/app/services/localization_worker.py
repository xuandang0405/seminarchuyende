"""Durable multilingual work with leases, progress, cooperative cancel and bounded retries."""
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from app.core.database import db_manager
from app.repositories.audio_repo import audio_repo
from app.repositories.poi_repo import poi_repo
from app.services.unit_of_work import run_transaction


async def run_job_loop():
    from app.services.job_worker import job_worker

    while True:
        try:
            worked = await process_one()
            legacy = await job_worker.process_single_job()
            if not worked and not legacy:
                await asyncio.sleep(2)
        except Exception:
            logging.getLogger("uvicorn").exception("Background job loop failed")
            await asyncio.sleep(5)


async def process_one():
    worker_id = uuid.uuid4().hex
    task = await audio_repo.claim_task(worker_id, lease_duration_seconds=120)
    if not task:
        return False
    async def heartbeat():
        while True:
            await asyncio.sleep(5)
            if not await audio_repo.update_heartbeat(task["_id"], worker_id, 120):
                return
    def lease_query():
        return {"_id": task["_id"], "lease_owner": worker_id, "status": "running",
                "lease_until": {"$gt": datetime.now(timezone.utc)},
                "cancel_requested": {"$ne": True}, "pause_requested": {"$ne": True}}
    async def can_commit(session=None, fence=False):
        if fence:
            result = await audio_repo.collection.update_one(
                lease_query(), {"$inc": {"commit_revision": 1}}, **({"session": session} if session else {}),
            )
            return bool(result.matched_count)
        return bool(await audio_repo.collection.find_one(lease_query(), {"_id": 1}))
    pulse = asyncio.create_task(heartbeat())
    completed = 0
    try:
        from app.services.translation_service import translation_service
        from app.services.tts_service import tts_service
        for item in task["items"]:
            if not await can_commit():
                raise RuntimeError("Task interrupted")
            poi = await poi_repo.get_by_id(item["poi_id"])
            version = item.get("input_version", 1)
            if not poi or poi.get("deleted_at") or poi.get("content_version", 1) != version:
                completed += 1
                await audio_repo.collection.update_one(lease_query(), {"$set": {"progress.completed": completed}})
                continue
            if item.get("lang"):
                lang = item["lang"]
                loc = await poi_repo.get_localization_by_lang(poi["_id"], lang)
                if not loc or loc.get("source_version") != poi.get("content_version", 1):
                    name = await translation_service.translate_text(poi["name"], lang) if lang != "vi" else poi["name"]
                    text = await translation_service.translate_text(poi["description"], lang) if lang != "vi" else poi["description"]
                else:
                    name, text = loc["name"], loc["description"]
                generator = tts_service.generate_with_google_tts if item.get("provider") == "google" else tts_service.generate_audio_for_text
                audio = await generator(f"{name}. {text}", lang)
                if not audio.get("success"):
                    raise RuntimeError(audio.get("error", "TTS failed"))
                async def commit(session):
                    if not await can_commit(session, fence=True):
                        raise RuntimeError("Task interrupted")
                    if not await poi_repo.fence_content(poi["_id"], version, session):
                        return False
                    await poi_repo.localizations_collection.update_one(
                        {"poi_id": poi["_id"], "lang": lang}, {"$set": {
                            "poi_id": poi["_id"], "lang": lang, "name": name, "description": text,
                            "translation_status": "ready", "audio_status": "ready", "audio_url": audio["audio_url"],
                            "audio_storage_key": audio["audio_storage_key"], "audio_duration_ms": audio["audio_duration_ms"],
                            "source_version": version,
                        }}, upsert=True, **({"session": session} if session else {}),
                    )
                    return True
                if await run_transaction(commit) and lang == "en":
                    from app.services.poi_admin_service import poi_admin_service
                    await poi_admin_service.toggle_activation(poi["_id"], True, expected_version=version, automatic=True)
            else:
                await translation_service.sync_poi_multilingual(poi["_id"], poi["name"], poi["description"],
                    db_manager.db, expected_version=version, can_commit=can_commit)
            completed += 1
            await audio_repo.collection.update_one({"_id": task["_id"], "lease_owner": worker_id},
                {"$set": {"progress.completed": completed, "updated_at": datetime.now(timezone.utc)}})
        if not await audio_repo.finish_task(task["_id"], "succeeded", worker_id=worker_id):
            raise RuntimeError("Task interrupted before completion")
    except Exception as exc:
        latest = await audio_repo.get_by_id(task["_id"])
        if not latest or latest.get("lease_owner") != worker_id:
            return True
        if latest.get("cancel_requested"):
            await audio_repo.finish_task(task["_id"], "cancelled", worker_id=worker_id)
        elif latest.get("pause_requested"):
            await audio_repo.collection.update_one({"_id": task["_id"], "lease_owner": worker_id},
                {"$set": {"status": "paused", "lease_owner": None, "lease_until": None}})
        elif task["attempts"] < task.get("max_attempts", 3):
            await audio_repo.collection.update_one({"_id": task["_id"], "lease_owner": worker_id},
                {"$set": {"status": "queued", "lease_owner": None, "lease_until": None, "error_message": str(exc),
                 "next_retry_at": datetime.now(timezone.utc) + timedelta(seconds=15 * 2 ** (task["attempts"] - 1))}})
        else:
            logging.getLogger("uvicorn").exception("Localization task failed")
            await audio_repo.finish_task(task["_id"], "failed", str(exc), worker_id=worker_id)
    finally:
        pulse.cancel()
        await asyncio.gather(pulse, return_exceptions=True)
    return True
