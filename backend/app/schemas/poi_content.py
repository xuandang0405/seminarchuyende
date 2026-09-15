from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

ReviewStatus = Literal["draft", "approved", "archived"]


class POIContentBase(BaseModel):
    poi_id: str
    language_code: str = Field(..., min_length=2, max_length=10, description="e.g., 'vi', 'en'")
    version: int = Field(default=1, ge=1)
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    narration_text: str = Field(..., min_length=1, description="Script for text-to-speech audio")
    review_status: ReviewStatus = "draft"
    source_content_id: Optional[str] = None


class POIContentCreate(BaseModel):
    poi_id: str
    language_code: str
    title: str
    description: Optional[str] = ""
    narration_text: str
    source_content_id: Optional[str] = None


class POIContentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    narration_text: Optional[str] = None
    review_status: Optional[ReviewStatus] = None


class POIContentResponse(POIContentBase):
    id: str = Field(..., alias="_id")
    reviewed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }
