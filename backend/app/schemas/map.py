"""Schemas for Map configuration, Coordinate boundaries, and POI Geospatial queries."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CoordinateDTO(BaseModel):
    """Normalized coordinate boundary object."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")


class MapBoundsDTO(BaseModel):
    """Bounding box for viewport rendering."""
    min_longitude: float = Field(..., ge=-180.0, le=180.0)
    min_latitude: float = Field(..., ge=-90.0, le=90.0)
    max_longitude: float = Field(..., ge=-180.0, le=180.0)
    max_latitude: float = Field(..., ge=-90.0, le=90.0)


class MapConfigResponse(BaseModel):
    """Public runtime map configuration sanitized for web and mobile clients."""
    center: CoordinateDTO
    default_zoom: int = Field(default=15)
    bounds: MapBoundsDTO
    tile_provider: str
    style_url: str
    attribution: str
    capabilities: Dict[str, bool] = Field(default_factory=lambda: {
        "supports_offline": False,
        "supports_routing": True,
        "supports_search": True,
        "supports_geofencing": True
    })


class POISummaryDTO(BaseModel):
    """Summary item for POI lists, search results, and map pins."""
    id: str
    code: str
    name: str
    category: str
    address: Optional[str] = ""
    location: Dict[str, Any]  # GeoJSON Point
    latitude: float
    longitude: float
    straight_line_distance_m: Optional[float] = None
    distance_display: Optional[str] = None
    trigger_radius: float = 30.0
    image_url: Optional[str] = None
    is_active: bool = True
    audio_url: Optional[str] = None
