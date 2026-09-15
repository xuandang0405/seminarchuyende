from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

AudioSourceType = Literal["upload", "tts"]


class AudioAssetBase(BaseModel):
    poi_content_id: str
    source_type: AudioSourceType
    storage_key: str
    duration_ms: int = Field(..., ge=1)
    file_size_bytes: int = Field(..., ge=1)
    mime_type: str = "audio/mpeg"
    sha256: str = Field(..., pattern="^[0-9a-f]{64}$")
    provider: Optional[str] = None
    voice_id: Optional[str] = None


class AudioAssetCreate(AudioAssetBase):
    pass


class AudioAssetResponse(AudioAssetBase):
    id: str = Field(..., alias="_id")
    stream_url: Optional[str] = None
    created_at: datetime

    model_config = {
        "populate_by_name": True
    }
