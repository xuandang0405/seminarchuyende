"""Geospatial helper service: pure functions for Haversine distance, coordinate validation, SI formatting, and GeoJSON conversions.

Rules:
- Coordinates at boundary API use (latitude, longitude).
- GeoJSON in MongoDB uses [longitude, latitude].
- SI units: distance in meters, duration in seconds.
"""

import math
from typing import Any, Dict, Tuple


EARTH_RADIUS_METERS = 6371000.0  # WGS-84 mean radius


def validate_coordinates(latitude: float, longitude: float) -> None:
    """Validates latitude and longitude ranges.

    Raises:
        ValueError: if latitude or longitude is NaN, infinite, or out of range.
    """
    if latitude is None or longitude is None:
        raise ValueError("Latitude and longitude cannot be None.")
    if math.isnan(latitude) or math.isnan(longitude) or math.isinf(latitude) or math.isinf(longitude):
        raise ValueError("Latitude and longitude must be valid finite numbers.")
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude must be between -90 and 90 degrees. Got: {latitude}")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude must be between -180 and 180 degrees. Got: {longitude}")


def validate_bbox(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> None:
    """Validates a bounding box [min_lon, min_lat, max_lon, max_lat]."""
    validate_coordinates(min_lat, min_lon)
    validate_coordinates(max_lat, max_lon)
    if min_lon > max_lon:
        raise ValueError(f"min_lon ({min_lon}) cannot be greater than max_lon ({max_lon}).")
    if min_lat > max_lat:
        raise ValueError(f"min_lat ({min_lat}) cannot be greater than max_lat ({max_lat}).")


def haversine_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """Calculates the great-circle straight-line distance between two coordinates in meters using the Haversine formula.

    Returns:
        float: straight-line distance in SI meters (>= 0.0).
    """
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)

    # Fast-path: exact same point
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Numerical stability clamp
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_METERS * c


def format_distance_display(meters: float, lang: str = "vi") -> str:
    """Formats straight_line_distance_m or route_distance_m for UI display.

    - Under 1000m: rounded integer meter e.g. "450 m"
    - 1000m and above: 1 decimal place km e.g. "1.2 km"
    """
    if meters is None or meters < 0:
        return "0 m"
    if meters < 1000.0:
        return f"{int(round(meters))} m"
    km = meters / 1000.0
    return f"{km:.1f} km"


def format_duration_display(seconds: float, lang: str = "vi") -> str:
    """Formats route_duration_s for UI display."""
    if seconds is None or seconds <= 0:
        return "< 1 phút" if lang == "vi" else "< 1 min"

    minutes = int(round(seconds / 60.0))
    if minutes < 1:
        return "< 1 phút" if lang == "vi" else "< 1 min"
    if minutes < 60:
        return f"{minutes} phút" if lang == "vi" else f"{minutes} mins"

    hours = minutes // 60
    rem_mins = minutes % 60
    if rem_mins == 0:
        return f"{hours} giờ" if lang == "vi" else f"{hours} hrs"
    return f"{hours} giờ {rem_mins} phút" if lang == "vi" else f"{hours}h {rem_mins}m"


def coords_to_geojson_point(latitude: float, longitude: float) -> Dict[str, Any]:
    """Converts (latitude, longitude) to GeoJSON Point format: [longitude, latitude]."""
    validate_coordinates(latitude, longitude)
    return {
        "type": "Point",
        "coordinates": [float(longitude), float(latitude)]
    }


def geojson_point_to_coords(point_doc: Dict[str, Any]) -> Tuple[float, float]:
    """Extracts (latitude, longitude) safely from a GeoJSON Point.

    Returns:
        Tuple[float, float]: (latitude, longitude)
    """
    if not isinstance(point_doc, dict):
        raise ValueError("Invalid GeoJSON point: must be a dictionary.")
    coords = point_doc.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        raise ValueError(f"Invalid GeoJSON coordinates: {coords}")
    lon, lat = float(coords[0]), float(coords[1])
    validate_coordinates(lat, lon)
    return lat, lon


def quantize_coordinate(lat: float, lon: float, precision: int = 4) -> Tuple[float, float]:
    """Quantizes coordinate for route caching (4 decimals ~ 11.1 meters at the equator)."""
    validate_coordinates(lat, lon)
    return round(float(lat), precision), round(float(lon), precision)
