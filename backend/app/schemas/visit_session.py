from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VisitSessionCreate(BaseModel):
    initial_language_code: str = Field(default="vi", min_length=2, max_length=10)
    tour_id: Optional[str] = None


class VisitSessionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    initial_language_code: str
    tour_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }
