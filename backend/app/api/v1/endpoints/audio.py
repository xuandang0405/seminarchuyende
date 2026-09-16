"""Router for Audio & TTS generation endpoints.

C10 / C11 / C12 / C13 / SD07 / AD07.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status

from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.services.tts_service import tts_service
from app.repositories.audio_repo import audio_repo
from app.repositories.poi_repo import poi_repo

router = APIRouter(prefix="/audio", tags=["Audio & TTS"])


class TTSGenerateRequest(BaseModel):
    lang: str = "vi"


@router.post("/generate/{poi_id}")
async def generate_tts(
    poi_id: str,
    req: TTSGenerateRequest,
    current_user: dict = Depends(get_current_admin)
):
    """Use Case C11 / SD07 / AD07: Generates speech audio for a POI localization using Edge-TTS."""
    res = await tts_service.schedule_poi_tts_task(
        poi_id=poi_id,
        lang=req.lang,
        requested_by=current_user["_id"]
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=res.get("error"))
    return res


@router.post("/upload/{poi_id}")
async def upload_audio_file(
    poi_id: str,
    lang: str = Query("vi"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin)
):
    """Use Case C10: Upload pre-recorded MP3 audio for a POI localization."""
    poi = await poi_repo.get_by_id(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI không tồn tại.")

    content_bytes = await file.read()
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="File rỗng.")

    import os
    from app.core.config import settings
    import hashlib

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "mp3"
    filename = f"{poi_id}_{lang}_manual.{ext}"
    audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    file_path = os.path.join(audio_dir, filename)

    with open(file_path, "wb") as f:
        f.write(content_bytes)

    storage_key = f"audio/{filename}"
    audio_url = f"/storage/{storage_key}"
    sha256 = hashlib.sha256(content_bytes).hexdigest()

    # Duration estimate
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
async def stream_audio_endpoint(storage_key: str, request: Request):
    """Streams audio file with HTTP 206 Partial Content range support."""
    from app.services.audio_service import audio_service
    range_header = request.headers.get("range")
    return audio_service.stream_audio_file(storage_key, range_header=range_header)
