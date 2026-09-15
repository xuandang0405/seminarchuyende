from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class TourPackageManifest(BaseModel):
    package_id: str
    tour_id: str
    language_code: str
    revision: int
    generated_at: datetime
    pois: List[Dict[str, Any]]
    audio_assets: List[Dict[str, Any]]
    total_files: int
    total_bytes: int


class TourPackageResponse(BaseModel):
    id: str = Field(..., alias="_id")
    tour_id: str
    language_code: str
    source_revision: int
    manifest: Dict[str, Any]
    total_bytes: int
    created_at: datetime

    model_config = {
        "populate_by_name": True
    }
