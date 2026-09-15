from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

PlaybackTriggerType = Literal["gps", "qr", "manual"]
PlaybackStatus = Literal["pending", "playing", "paused", "completed", "stopped", "failed"]
PlaybackEventType = Literal["start", "progress", "pause", "resume", "seek", "complete", "stop", "error"]


class PlaybackCreate(BaseModel):
    session_id: str
    audio_asset_id: str
    trigger_type: PlaybackTriggerType
    qr_code_id: Optional[str] = None


class PlaybackResponse(BaseModel):
    id: str = Field(..., alias="_id")
    session_id: str
    audio_asset_id: str
    trigger_type: PlaybackTriggerType
    status: PlaybackStatus
    listened_ms: int = 0
    last_event_seq: int = 0
    qr_code_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }


class PlaybackEventIn(BaseModel):
    playback_id: str
    seq_no: int = Field(..., ge=1)
    event_type: PlaybackEventType
    listened_ms_total: int = Field(default=0, ge=0)
    position_ms: int = Field(default=0, ge=0)
    occurred_at: datetime


class PlaybackBatchEventsRequest(BaseModel):
    events: List[PlaybackEventIn]


class PlaybackBatchEventsResult(BaseModel):
    received_count: int
    saved_count: int
    duplicates_count: int
