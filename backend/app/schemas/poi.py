from datetime import datetime
from typing import Dict, Literal, Optional, Any
from pydantic import BaseModel, Field, model_validator
from app.schemas.common import GeoPoint

PoiCategory = Literal["attraction", "food", "bus_stop", "other"]
PoiStatus = Literal["draft", "active", "archived"]


class PublicationContent(BaseModel):
    content_id: str
    audio_asset_id: str
    published_at: datetime
    published_by: str


class POIBase(BaseModel):
    code: str = Field(..., description="Unique POI code, e.g., 'POI_001'")
    category: PoiCategory = "attraction"
    address: str = ""
    location: GeoPoint
    radius_enter_m: int = Field(default=20, ge=1)
    radius_exit_m: int = Field(default=30, ge=1)
    cooldown_seconds: int = Field(default=300, ge=0)
    priority: int = Field(default=1, ge=0)
    status: PoiStatus = "draft"
    image_key: Optional[str] = None

    @model_validator(mode="after")
    def validate_radii(self):
        if self.radius_exit_m <= self.radius_enter_m:
            raise ValueError("radius_exit_m must be strictly greater than radius_enter_m")
        return self


class POICreate(POIBase):
    pass


class POIUpdate(BaseModel):
    code: Optional[str] = None
    category: Optional[PoiCategory] = None
    address: Optional[str] = None
    location: Optional[GeoPoint] = None
    radius_enter_m: Optional[int] = Field(None, ge=1)
    radius_exit_m: Optional[int] = Field(None, ge=1)
    cooldown_seconds: Optional[int] = Field(None, ge=0)
    priority: Optional[int] = Field(None, ge=0)
    status: Optional[PoiStatus] = None
    image_key: Optional[str] = None


class POIResponse(POIBase):
    id: str = Field(..., alias="_id")
    revision: int = 1
    published_contents: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True
    }
