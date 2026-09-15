import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, status
from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.repositories.content_repo import content_repo
from app.repositories.audio_repo import audio_repo
from app.schemas.audio_asset import AudioAssetResponse
from app.services.audio_service import audio_service
from app.services.tts_service import tts_service

router = APIRouter(prefix="/audio", tags=["Audio & Streaming"])


@router.post("/upload/{poi_content_id}", response_model=AudioAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    poi_content_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin)
):
    """Upload pre-recorded MP3 audio for a POI content."""
    content = await content_repo.get_by_id(poi_content_id)
    if not content:
        raise HTTPException(status_code=404, detail="POI content not found")

    content_bytes = await file.read()
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    doc = await audio_service.save_uploaded_audio(
        poi_content_id=poi_content_id,
        filename=file.filename or "narration.mp3",
        content_bytes=content_bytes,
        mime_type=file.content_type or "audio/mpeg"
    )
    doc["stream_url"] = f"/api/v1/audio/{doc['storage_key']}/stream"
    return doc


@router.post("/generate-tts/{poi_content_id}", response_model=AudioAssetResponse, status_code=status.HTTP_201_CREATED)
async def generate_tts_audio(
    poi_content_id: str,
    voice_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Synthesize speech audio directly from POI content narration_text."""
    content = await content_repo.get_by_id(poi_content_id)
    if not content:
        raise HTTPException(status_code=404, detail="POI content not found")

    text = content.get("narration_text")
    if not text:
        raise HTTPException(status_code=400, detail="Content has empty narration text")

    lang = content.get("language_code", "vi")
    storage_key, duration_ms, file_size, sha256_hash = await tts_service.synthesize_speech(
        text=text,
        language_code=lang,
        voice_id=voice_id
    )

    audio_doc = {
        "_id": str(uuid.uuid4()),
        "poi_content_id": poi_content_id,
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
    audio_doc["stream_url"] = f"/api/v1/audio/{storage_key}/stream"
    return audio_doc


@router.get("/{storage_key}/stream")
async def stream_audio(
    storage_key: str,
    range: Optional[str] = Header(None)
):
    """Stream audio with support for Range requests (HTTP 206 Partial Content) for seeking."""
    return audio_service.stream_audio_file(storage_key, range)


@router.get("/info/{audio_id}", response_model=AudioAssetResponse)
async def get_audio_info(audio_id: str):
    audio = await audio_repo.get_by_id(audio_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio asset not found")
    audio["stream_url"] = f"/api/v1/audio/{audio['storage_key']}/stream"
    return audio
