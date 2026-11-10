"""Router for Audio & TTS generation endpoints.

C10 / C11 / C12 / C13 / SD07 / AD07.
"""

from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field
from fastapi import Request, APIRouter, Depends, HTTPException, UploadFile, File, Query, status
import re
import os
import asyncio
import hashlib
from app.core.config import settings

from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.services.tts_service import tts_service
from app.repositories.audio_repo import audio_repo
from app.repositories.poi_repo import poi_repo

router = APIRouter(prefix="/audio", tags=["Audio & TTS"])


class TTSGenerateRequest(BaseModel):
    lang: Literal["vi", "en", "fr", "ja", "ko", "zh"] = "vi"
    provider: Literal["edge", "google"] = "google"


class TTSSynthesizeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize into speech")
    lang: Literal["vi", "en", "fr", "ja", "ko", "zh"] = "vi"
    provider: Literal["edge", "google"] = "google"


@router.post("/generate/{poi_id}")
async def generate_tts(
    poi_id: str,
    req: TTSGenerateRequest,
    current_user: dict = Depends(get_current_admin)
):
    """Use Case C11 / SD07 / AD07: Generates speech audio for a POI localization using Google TTS / Edge-TTS."""
    res = await tts_service.schedule_poi_tts_task(
        poi_id=poi_id,
        lang=req.lang,
        requested_by=current_user["_id"],
        provider=req.provider
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=res.get("error"))
    return res


@router.post("/synthesize-text")
async def synthesize_text_tts(
    req: TTSSynthesizeTextRequest,
    current_user: dict = Depends(get_current_admin)
):
    """Synthesizes arbitrary description text into MP3 using Google TTS with automated multi-language translation."""
    clean_text = req.text.strip()
    from app.services.rate_limit_service import enforce_rate_limit
    await enforce_rate_limit("tts:" + current_user["_id"], 100, 86400)
    if not clean_text:
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    target_lang = (req.lang or "vi").lower()
    text_to_synthesize = clean_text

    # If target language is not Vietnamese, automatically translate text first
    # so Google TTS reads authentic native text instead of reading Vietnamese with a foreign accent
    if target_lang != "vi":
        try:
            from app.services.translation_service import translation_service
            translated = await translation_service.translate_text(clean_text, target_lang)
            if translated and len(translated.strip()) > 0:
                text_to_synthesize = translated
        except Exception as e:
            raise HTTPException(502, "Dịch nội dung thất bại; chưa tạo audio sai ngôn ngữ.") from e

    if req.provider == "google":
        res = await tts_service.generate_with_google_tts(text_to_synthesize, lang=target_lang)
    else:
        res = await tts_service.generate_audio_for_text(text_to_synthesize, lang=target_lang)

    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))

    res["translated_text"] = text_to_synthesize
    res["target_lang"] = target_lang
    return res


ALLOWED_AUDIO_EXTENSIONS = {"mp3"}
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25MB


@router.post("/upload/{poi_id}")
async def upload_audio_file(
    poi_id: str,
    lang: str = Query("vi"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin)
):
    """Use Case C10: Upload pre-recorded MP3 audio for a POI localization with security checks."""
    from app.services.translation_service import SUPPORTED_LANGUAGES
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(422, "Ngôn ngữ không được hỗ trợ.")
    # 1. Validate file extension (fail-fast before database lookup)
    raw_ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "mp3"
    if raw_ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng tệp '{raw_ext}' không được hỗ trợ. Chỉ chấp nhận các định dạng âm thanh: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}."
        )

    # 2. Validate file content and size limits
    content_bytes = await file.read(MAX_AUDIO_SIZE_BYTES + 1)
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Tệp tải lên rỗng.")

    if len(content_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dung lượng tệp vượt quá giới hạn cho phép (Tối đa {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB)."
        )

    # 3. Check POI existence
    poi = await poi_repo.get_by_id(poi_id)
    if not poi or poi.get("deleted_at"):
        raise HTTPException(status_code=404, detail="POI không tồn tại.")
    version = poi.get("content_version", 1)
    from app.services.audio_metadata import mp3_duration_ms
    try:
        duration_ms = mp3_duration_ms(content_bytes)
    except Exception as exc:
        raise HTTPException(422, "Tệp không phải audio MP3 hợp lệ.") from exc
    loc = await poi_repo.get_localization_by_lang(poi_id, lang)
    if not loc or loc.get("source_version") != version:
        raise HTTPException(409, "Cần tạo bản nội dung đúng ngôn ngữ và phiên bản trước khi tải audio.")

    # 4. Sanitize file name against path traversal (SEC-004)
    safe_poi_id = re.sub(r"[^a-zA-Z0-9_-]", "", os.path.basename(poi_id))
    safe_lang = re.sub(r"[^a-zA-Z0-9_-]", "", os.path.basename(lang)) or "vi"
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    filename = f"{safe_poi_id}_{safe_lang}_{sha256[:16]}.{raw_ext}"
    audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    file_path = os.path.join(audio_dir, filename)

    # Non-blocking async file write
    def _write_bytes(target: str, data: bytes):
        import tempfile
        with tempfile.NamedTemporaryFile(dir=audio_dir, delete=False) as temp:
            try:
                temp.write(data)
                temp.close()
                os.replace(temp.name, target)
            finally:
                temp.close()
                if os.path.exists(temp.name):
                    os.unlink(temp.name)

    await asyncio.to_thread(_write_bytes, file_path, content_bytes)

    storage_key = f"audio/{filename}"
    audio_url = f"/storage/{storage_key}"
    from app.services.unit_of_work import run_transaction
    async def commit(session):
        if not await poi_repo.fence_content(poi_id, version, session):
            raise HTTPException(409, "Nội dung đã đổi. Hãy tải lại trước khi gắn audio.")
        updated = await audio_repo.update_audio_metadata(
            poi_id, lang, audio_url, storage_key, sha256, duration_ms, version, "uploaded", session
        )
        if not updated:
            raise HTTPException(409, "Bản nội dung đã thay đổi.")
        return updated
    updated = await run_transaction(commit)

    return {
        "success": True,
        "audio_url": audio_url,
        "audio_duration_ms": duration_ms,
        "localization": updated
    }


@router.get("/tasks/events")
async def task_batch_events(
    request: Request,
    task_id: list[str] = Query(min_length=1, max_length=24),
    current_user: dict = Depends(get_current_admin),
):
    """Send the current task states over one connection."""
    import json
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import StreamingResponse

    ids = tuple(dict.fromkeys(task_id))

    async def snapshot():
        return await asyncio.gather(*(audio_repo.get_by_id(id_) for id_ in ids))

    initial = await snapshot()
    if any(task is None for task in initial):
        raise HTTPException(404, "Có tác vụ không tồn tại.")

    async def events():
        tasks = initial
        for _ in range(180):
            if await request.is_disconnected():
                return
            yield "data: " + json.dumps(jsonable_encoder(tasks), ensure_ascii=False) + "\n\n"
            if any(task is None for task in tasks) or all(
                task["status"] in ("succeeded", "failed", "cancelled") for task in tasks
            ):
                return
            await asyncio.sleep(2)
            tasks = await snapshot()

    return StreamingResponse(events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, current_user: dict = Depends(get_current_admin)):
    """Use Case C12: View progress and status of an audio generation task."""
    task = await audio_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task không tồn tại.")
    return task


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, current_user: dict = Depends(get_current_admin)):
    """Use Case C13: Cancel or request stop for an audio task."""
    success = await audio_repo.request_cancel(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Không thể hủy tác vụ ở trạng thái hiện tại.")
    return {"success": True, "message": "Đã gửi yêu cầu hủy tác vụ."}


@router.get("/info/{audio_asset_id}")
async def get_audio_info(audio_asset_id: str, current_user: dict = Depends(get_current_admin)):
    """Returns audio asset metadata for audio playback."""
    from app.repositories.audio_asset_repo import audio_asset_repo
    audio = await audio_asset_repo.get_by_id(audio_asset_id)
    if not audio:
        raise HTTPException(404, "Audio không tồn tại.")
    storage_key = audio["storage_key"]
    duration = audio["duration_ms"]
    return {
        "_id": audio_asset_id,
        "storage_key": storage_key,
        "stream_url": f"/api/v1/audio/{storage_key}/stream",
        "duration_ms": duration,
    }


@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str, current_user: dict = Depends(get_current_admin)):
    if not await audio_repo.request_pause(task_id):
        raise HTTPException(409, "Không thể tạm dừng tác vụ này.")
    return {"success": True}

@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, current_user: dict = Depends(get_current_admin)):
    result = await audio_repo.collection.update_one({"_id": task_id, "pause_requested": True,
        "status": {"$in": ["paused", "queued"]}}, {"$set": {"status": "queued", "pause_requested": False, "next_retry_at": None}})
    if not result.matched_count:
        raise HTTPException(409, "Tác vụ chưa tạm dừng hoặc đã kết thúc.")
    return {"success": True}

@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request, current_user: dict = Depends(get_current_admin)):
    import json
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import StreamingResponse
    if not await audio_repo.get_by_id(task_id):
        raise HTTPException(404, "Task không tồn tại.")
    async def events():
        for _ in range(180):
            if await request.is_disconnected():
                return
            task = await audio_repo.get_by_id(task_id)
            yield "data: " + json.dumps(jsonable_encoder(task), ensure_ascii=False) + "\n\n"
            if not task or task.get("status") in ("succeeded", "failed", "cancelled"):
                return
            await asyncio.sleep(2)
    return StreamingResponse(events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/{storage_key:path}/stream")
async def stream_audio_endpoint(
    storage_key: str,
    request: Request,
    grant_token: Optional[str] = Query(None)
):
    """Streams audio file with HTTP 206 Partial Content range support.

    BR-ACCESS-01 / Section 8: Strictly gates audio streaming behind verified playback grant token.
    """
    from app.services.audio_service import audio_service
    from app.services.access_service import access_service

    # Verify grant token
    grant = await access_service.verify_grant_token(grant_token, storage_key) if grant_token else None
    is_authorized = bool(grant)

    if not is_authorized:
        # Check if caller has Bearer token with admin role
        auth_header = request.headers.get("Authorization")
        if (auth_header and auth_header.startswith("Bearer ")) or request.cookies.get("tourvoice_access_token"):
            token = auth_header.split(" ")[1] if auth_header else None
            try:
                user = await get_current_admin(current_user=await get_current_user(token=token, request=request))
                is_authorized = bool(user)
            except HTTPException:
                pass

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yêu cầu Playback Grant hợp lệ hoặc quyền sở hữu tour để phát âm thanh."
        )

    range_header = request.headers.get("range")
    response = audio_service.stream_audio_file(storage_key, range_header=range_header)
    if grant and response.status_code in (200, 206):
        from app.repositories.playback_grant_repo import playback_grant_repo
        await playback_grant_repo.mark_delivery(grant["_id"])
    return response

