from datetime import datetime
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field, model_validator
from app.schemas.common import GeoPoint

PoiCategory = Literal["attraction", "food", "bus_stop", "other"]
PoiStatus = Literal["draft", "active", "archived"]


class MenuItem(BaseModel):
    id: Optional[str] = None
    name: str
    price: Optional[float] = None
    currency: str = "VND"
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: bool = True
    is_specialty: bool = False


class PublicationContent(BaseModel):
    content_id: str
    audio_asset_id: str
    published_at: datetime
    published_by: str


class POIBase(BaseModel):
    code: str = Field(..., description="Unique POI code, e.g., 'Q4-BEN-NHA-RONG'")
    category: PoiCategory = "attraction"
    address: str = ""
    location: GeoPoint
    radius_enter_m: int = Field(default=25, ge=1)
    radius_exit_m: int = Field(default=50, ge=1)
    cooldown_seconds: int = Field(default=120, ge=0)
    priority: int = Field(default=1, ge=0)
    status: PoiStatus = "draft"
    image_key: Optional[str] = None
    owner_id: Optional[str] = None
    menu_items: List[MenuItem] = Field(default_factory=list)

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
    owner_id: Optional[str] = None
    menu_items: Optional[List[MenuItem]] = None


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


class POINearbyQuery(BaseModel):
    longitude: float
    latitude: float
    max_distance_meters: float = 1000
    category: Optional[PoiCategory] = None
