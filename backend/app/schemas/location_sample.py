from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from app.schemas.common import GeoPoint


class LocationSampleIn(BaseModel):
    session_id: str
    location: GeoPoint
    accuracy_m: float = Field(default=5.0, ge=0)
    recorded_at: datetime


class LocationBatchIn(BaseModel):
    samples: List[LocationSampleIn]


class LocationSampleResponse(LocationSampleIn):
    id: str = Field(..., alias="_id")
    received_at: datetime

    model_config = {
        "populate_by_name": True
    }
