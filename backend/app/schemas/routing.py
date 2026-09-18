"""Schemas for routing requests, normalized route preview, and tour summary."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field
from app.schemas.map import CoordinateDTO


class TravelMode(str, Enum):
    WALKING = "walking"
    DRIVING = "driving"
    CYCLING = "cycling"


class RouteStepDTO(BaseModel):
    """A turn-by-turn navigation step."""
    instruction: str
    distance_m: float
    duration_s: float
    distance_display: str
    duration_display: str
    street_name: Optional[str] = ""
    maneuver_type: Optional[str] = "turn"


class RouteLegDTO(BaseModel):
    """A segment between two waypoints."""
    distance_m: float
    duration_s: float
    distance_display: str
    duration_display: str
    steps: List[RouteStepDTO] = Field(default_factory=list)


class RouteResultDTO(BaseModel):
    """Normalized routing response contract for Web and Mobile."""
    route_id: str
    mode: str = "walking"
    route_distance_m: float
    route_duration_s: float
    distance_display: str
    duration_display: str
    geometry: Dict[str, Any]  # GeoJSON LineString
    coordinates: List[List[float]] = Field(default_factory=list)  # [[lon, lat], ...]
    legs: List[RouteLegDTO] = Field(default_factory=list)
    steps: List[RouteStepDTO] = Field(default_factory=list)
    snapped_origin_distance_m: Optional[float] = 0.0
    snapped_destination_distance_m: Optional[float] = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    warning: Optional[str] = None


class RoutePreviewRequest(BaseModel):
    """Request to calculate a route preview between origin and destination."""
    origin: Optional[CoordinateDTO] = None
    origin_poi_id: Optional[str] = None
    destination: Optional[CoordinateDTO] = None
    destination_poi_id: Optional[str] = None
    mode: TravelMode = TravelMode.WALKING
    locale: str = "vi"


class TourRouteSummaryResponse(BaseModel):
    """Calculated routing summary for sequential stops in a tour."""
    tour_id: str
    tour_name: str
    stop_count: int
    total_distance_m: float
    total_duration_s: float
    total_distance_display: str
    total_duration_display: str
    geometry: Dict[str, Any]  # Full GeoJSON LineString
    legs: List[Dict[str, Any]]
