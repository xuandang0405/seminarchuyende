"""Router for Audio & TTS generation endpoints.

C10 / C11 / C12 / C13 / SD07 / AD07.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
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
    lang: str = "vi"
    provider: str = "google"


class TTSSynthesizeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize into speech")
    lang: str = "vi"
    provider: str = "google"


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
    current_user: dict = Depends(get_current_user)
):
    """Synthesizes arbitrary description text into MP3 using Google TTS with automated multi-language translation."""
    clean_text = req.text.strip()
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
            logger.warning(f"Auto-translation before TTS failed for {target_lang}: {e}")

    if req.provider == "google":
        res = await tts_service.generate_with_google_tts(text_to_synthesize, lang=target_lang)
    else:
        res = await tts_service.generate_audio_for_text(text_to_synthesize, lang=target_lang)

    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))

    res["translated_text"] = text_to_synthesize
    res["target_lang"] = target_lang
    return res


ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "aac", "ogg"}
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25MB


@router.post("/upload/{poi_id}")
async def upload_audio_file(
    poi_id: str,
    lang: str = Query("vi"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin)
):
    """Use Case C10: Upload pre-recorded MP3 audio for a POI localization with security checks."""
    # 1. Validate file extension (fail-fast before database lookup)
    raw_ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "mp3"
    if raw_ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng tệp '{raw_ext}' không được hỗ trợ. Chỉ chấp nhận các định dạng âm thanh: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}."
        )

    # 2. Validate file content and size limits
    content_bytes = await file.read()
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Tệp tải lên rỗng.")

    if len(content_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dung lượng tệp vượt quá giới hạn cho phép (Tối đa {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB)."
        )

    # 3. Check POI existence
    poi = await poi_repo.get_by_id(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI không tồn tại.")

    # 4. Sanitize file name against path traversal (SEC-004)
    safe_poi_id = re.sub(r"[^a-zA-Z0-9_-]", "", os.path.basename(poi_id))
    safe_lang = re.sub(r"[^a-zA-Z0-9_-]", "", os.path.basename(lang)) or "vi"
    filename = f"{safe_poi_id}_{safe_lang}_manual.{raw_ext}"
    audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    file_path = os.path.join(audio_dir, filename)

    # Non-blocking async file write
    def _write_bytes(target: str, data: bytes):
        with open(target, "wb") as f:
            f.write(data)

    await asyncio.to_thread(_write_bytes, file_path, content_bytes)

    storage_key = f"audio/{filename}"
    audio_url = f"/storage/{storage_key}"
    sha256 = hashlib.sha256(content_bytes).hexdigest()

    # Calculate audio duration accurately if mutagen is available, with safe fallback
    duration_ms = 10000
    try:
        import mutagen
        import io
        m = mutagen.File(io.BytesIO(content_bytes))
        if m and m.info and hasattr(m.info, "length") and m.info.length > 0:
            duration_ms = int(m.info.length * 1000)
        else:
            duration_ms = max(int((len(content_bytes) / 16000.0) * 1000), 5000)
    except Exception:
        duration_ms = max(int((len(content_bytes) / 16000.0) * 1000), 5000)

    updated = await audio_repo.update_audio_metadata(
        poi_id=poi_id,
        lang=lang,
        audio_url=audio_url,
        audio_storage_key=storage_key,
        audio_content_hash=sha256,
        audio_duration_ms=duration_ms,
        audio_source="uploaded"
    )

    return {
        "success": True,
        "audio_url": audio_url,
        "audio_duration_ms": duration_ms,
        "localization": updated
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, current_user: dict = Depends(get_current_user)):
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
async def get_audio_info(audio_asset_id: str):
    """Returns audio asset metadata for audio playback."""
    audio = await audio_repo.get_by_id(audio_asset_id)
    storage_key = audio.get("storage_key") if audio else f"{audio_asset_id}.mp3"
    duration = audio.get("duration_ms", 15000) if audio else 15000
    return {
        "_id": audio_asset_id,
        "storage_key": storage_key,
        "stream_url": f"/api/v1/audio/{storage_key}/stream",
        "duration_ms": duration,
    }


from fastapi import Request


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
    is_authorized = False
    if grant_token:
        is_authorized = await access_service.verify_grant_token(grant_token, storage_key)

    if not is_authorized:
        # Check if caller has Bearer token with admin role
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                import jwt
                from app.core.config import settings
                from app.repositories.auth_repo import auth_repo
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user = await auth_repo.get_user_by_id(payload.get("sub"))
                if user and user.get("role") in ("admin", "super_admin"):
                    is_authorized = True
            except Exception:
                pass

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yêu cầu Playback Grant hợp lệ hoặc quyền sở hữu tour để phát âm thanh."
        )

    range_header = request.headers.get("range")
    return audio_service.stream_audio_file(storage_key, range_header=range_header)

