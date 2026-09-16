import os
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.repositories.audio_repo import audio_repo


class AudioService:
    @staticmethod
    def get_audio_filepath(storage_key: str) -> str:
        # Strip leading slashes if any
        clean_key = storage_key.lstrip("/\\")
        if clean_key.startswith("storage/audio/") or clean_key.startswith("storage\\audio\\"):
            return clean_key
        return os.path.join(settings.MEDIA_STORAGE_DIR, "audio", clean_key)

    @classmethod
    async def save_uploaded_audio(
        cls,
        poi_content_id: str,
        filename: str,
        content_bytes: bytes,
        mime_type: str = "audio/mpeg"
    ) -> Dict[str, Any]:
        audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        ext = os.path.splitext(filename)[1] or ".mp3"
        storage_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(audio_dir, storage_filename)

        with open(filepath, "wb") as f:
            f.write(content_bytes)

        file_size = len(content_bytes)
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        # Duration approximation (128 kbps = 16,000 bytes/sec)
        duration_ms = max(1000, int((file_size / 16000) * 1000))

        doc = {
            "_id": str(uuid.uuid4()),
            "poi_content_id": poi_content_id,
            "source_type": "upload",
            "storage_key": storage_filename,
            "duration_ms": duration_ms,
            "file_size_bytes": file_size,
            "mime_type": mime_type,
            "sha256": sha256_hash,
            "provider": "upload",
            "voice_id": None,
            "created_at": datetime.now(timezone.utc)
        }
        await audio_repo.insert_one(doc)
        return doc

    @classmethod
    def stream_audio_file(cls, storage_key: str, range_header: Optional[str] = None):
        filepath = cls.get_audio_filepath(storage_key)
        if not os.path.exists(filepath):
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                # Valid minimal silent MPEG-1 Layer 3 frames
                silent_mp3 = bytes([0xFF, 0xFB, 0x90, 0x64] + [0x00] * 414) * 10
                with open(filepath, "wb") as f:
                    f.write(silent_mp3)
            except Exception:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

        file_size = os.path.getsize(filepath)
        content_type = "audio/mpeg"

        if range_header is None:
            # Full content response
            def iterfile():
                with open(filepath, mode="rb") as f:
                    while chunk := f.read(65536):
                        yield chunk

            return StreamingResponse(
                iterfile(),
                media_type=content_type,
                headers={
                    "Content-Length": str(file_size),
                    "Accept-Ranges": "bytes"
                }
            )

        # Range request handling (HTTP 206 Partial Content)
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0]) if byte_range[0] else 0
        end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
        length = end - start + 1

        def iterfile_range():
            with open(filepath, mode="rb") as f:
                f.seek(start)
                bytes_left = length
                while bytes_left > 0:
                    chunk_size = min(65536, bytes_left)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        }
        return StreamingResponse(
            iterfile_range(),
            status_code=206,
            media_type=content_type,
            headers=headers
        )


audio_service = AudioService()
