"""Pydantic v2 schemas for POI.

Strictly adheres to Section 25 ERD Baseline and Section 9 Extensions.
"""

from datetime import datetime
from typing import List, Optional, Any, Dict, Literal
from pydantic import BaseModel, Field

from app.schemas.menu import MenuItemCreate, MenuItemUpdate, MenuItemResponse
MenuItem = MenuItemResponse


class GeoLocation(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[longitude, latitude]")


class POIBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=5)
    category: str = Field(default="sightseeing")
    address: str = Field(default="")
    location: GeoLocation
    images: List[str] = Field(default_factory=list)
    trigger_radius: float = Field(default=30.0, ge=5.0, le=500.0)
    audio_priority: int = Field(default=1, ge=1, le=100)
    audio_url: Optional[str] = None
    audio_duration_ms: Optional[int] = 0
    auto_translate: Optional[bool] = Field(default=False, description="Automatically translate to 6 languages and generate Google TTS")
    owner_id: Optional[str] = None
    source_lang: str = Field(default="vi")
    activation_requested: bool = Field(default=False)


class POICreate(POIBase):
    pass


class POIUpdate(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    location: Optional[GeoLocation] = None
    images: Optional[List[str]] = None
    trigger_radius: Optional[float] = Field(None, ge=5.0, le=500.0)
    audio_priority: Optional[int] = Field(None, ge=1, le=100)
    audio_url: Optional[str] = None
    audio_duration_ms: Optional[int] = None
    owner_id: Optional[str] = None
    expected_version: Optional[int] = Field(None, description="Optimistic concurrency control version")
    auto_translate: Optional[bool] = Field(default=True, description="Automatically translate to 6 languages and generate Google TTS")
    translations: Optional[Dict[str, Any]] = None


class POIPublicResponse(BaseModel):
    id: str
    name: str
    description: str
    category: Optional[str] = None
    address: Optional[str] = None
    location: GeoLocation
    images: List[str] = Field(default_factory=list)
    trigger_radius: float = 30.0
    audio_priority: int = 1
    audio_url: Optional[str] = None
    audio_duration_ms: int = 0
    requested_lang: str = "vi"
    resolved_lang: str = "vi"
    is_fallback: bool = False
    version: int = 1
    available_languages: Optional[List[str]] = None
    translations: Optional[Dict[str, Any]] = None


class POIAdminResponse(BaseModel):
    id: str = Field(..., alias="_id")
    owner_id: Optional[str] = None
    name: str
    description: str
    category: str
    address: str
    location: GeoLocation
    images: List[str] = Field(default_factory=list)
    trigger_radius: float
    audio_priority: int
    audio_status: str
    is_active: bool
    activation_requested: bool
    source_lang: str
    version: int
    content_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


POIResponse = POIAdminResponse


class POINearbyQuery(BaseModel):
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in degrees")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees")
    max_distance_meters: float = Field(default=1000.0, ge=1.0, le=50000.0, description="Max search radius in meters")
    category: Optional[str] = None
