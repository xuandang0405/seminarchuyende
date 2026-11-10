"""Visitor requests for missing audio on already-published places."""

import hashlib
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.v1.endpoints.access import resolve_subject
from app.repositories.poi_repo import poi_repo
from app.services.audio_service import audio_service
from app.services.rate_limit_service import enforce_rate_limit
from app.services.tts_service import tts_service

router = APIRouter(prefix="/localizations", tags=["Localization"])


class PrepareNarration(BaseModel):
    poi_id: str = Field(min_length=1, max_length=128)
    lang: str = Field(pattern=r"^(vi|en|ja|ko|fr|zh)$")


class PrepareHotset(BaseModel):
    poi_ids: list[str] = Field(min_length=1, max_length=3)
    lang: str = Field(pattern=r"^(vi|en|ja|ko|fr|zh)$")


async def _subject_for_preparation(request: Request):
    user, guest = await resolve_subject(request)
    if not user and not guest:
        raise HTTPException(401, "Cần phiên tham quan hợp lệ.")
    subject = (user or guest)["_id"]
    await enforce_rate_limit(f"localization:visitor:{subject}", 6, 600)
    await enforce_rate_limit("localization:visitor:global", 50, 600)
    return subject


async def _prepare(poi_id: str, lang: str, subject: str):
    poi = await poi_repo.get_public_by_id(poi_id)
    if not poi:
        return "unavailable"
    version = poi.get("content_version", 1)
    loc = await poi_repo.get_localization_by_lang(poi_id, lang)
    if loc and loc.get("source_version", 1) == version and loc.get("audio_status") == "ready" and audio_service.localization_file_exists(loc):
        return "ready"
    retry_window = int(time.time()) // 1800
    fingerprint = hashlib.sha256(f"{poi['_id']}:{version}:{lang}:{retry_window}".encode()).hexdigest()
    result = await tts_service.schedule_poi_tts_task(
        poi["_id"], lang, f"visitor:{subject}", task_id="task_demand_" + fingerprint
    )
    return "queued" if result["success"] and result["status"] in ("queued", "running") else "unavailable"


@router.post("/on-demand", status_code=202)
async def prepare_narration(payload: PrepareNarration, request: Request):
    subject = await _subject_for_preparation(request)
    status = await _prepare(payload.poi_id, payload.lang, subject)
    if status == "unavailable":
        raise HTTPException(404, "Địa điểm chưa sẵn sàng.")
    return {"status": status}


@router.post("/prepare-hotset", status_code=202)
async def prepare_hotset(payload: PrepareHotset, request: Request):
    subject = await _subject_for_preparation(request)
    items = [
        {"poi_id": poi_id, "status": await _prepare(poi_id, payload.lang, subject)}
        for poi_id in dict.fromkeys(payload.poi_ids) if 0 < len(poi_id) <= 128
    ]
    return {"items": items}
