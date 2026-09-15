from datetime import datetime
from typing import Dict, Literal, Optional, Any
from pydantic import BaseModel, Field

JobType = Literal["translate", "tts"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


class ContentJobBase(BaseModel):
    job_type: JobType
    input_content_id: str
    provider: str = "edge-tts"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    target_language_code: Optional[str] = None


class ContentJobCreate(ContentJobBase):
    idempotency_key: Optional[str] = None


class ContentJobResponse(ContentJobBase):
    id: str = Field(..., alias="_id")
    status: JobStatus
    attempts: int = 0
    max_attempts: int = 3
    idempotency_key: str
    requested_by: str
    output_content_id: Optional[str] = None
    output_audio_id: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }
