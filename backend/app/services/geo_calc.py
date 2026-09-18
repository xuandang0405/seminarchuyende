"""Pure mathematical geospatial calculation utilities (Haversine distance, bounds, coordinate validation).

Implements BR-GEO-01 / BR-ROUTE-01 / UC T04 / T14 / T16.
Independent from database or third-party web services.
"""

import math
from typing import Tuple

EARTH_RADIUS_METERS = 6371000.0


def validate_coordinates(lat: float, lon: float) -> Tuple[float, float]:
    """Validates latitude and longitude ranges and numeric validity.
    
    BR-GEO-01: -90 <= lat <= 90 and -180 <= lon <= 180, finite numeric only.
    """
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise ValueError("Tọa độ phải là giá trị số thực.")
    if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
        raise ValueError("Tọa độ không được là NaN hoặc Infinity.")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Vĩ độ {lat} không hợp lệ (phải nằm trong khoảng [-90, 90]).")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Kinh độ {lon} không hợp lệ (phải nằm trong khoảng [-180, 180]).")
    return float(lat), float(lon)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic coordinates in meters.
    
    Pure Haversine formula with clamping against floating-point errors.
    """
    lat1, lon1 = validate_coordinates(lat1, lon1)
    lat2, lon2 = validate_coordinates(lat2, lon2)

    # Identical points check
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(EARTH_RADIUS_METERS * c, 2)


def format_distance_display(meters: float) -> str:
    """Formats numeric distance in meters to user-friendly string (e.g., '350 m' or '2.4 km')."""
    if meters < 0:
        return "0 m"
    if meters < 1000:
        return f"{int(round(meters))} m"
    km = round(meters / 1000.0, 1)
    return f"{km} km"


def format_duration_display(seconds: float) -> str:
    """Formats duration in seconds to user-friendly string (e.g., '45 giây', '4 phút', '1 giờ 15 phút')."""
    if seconds <= 0:
        return "0 phút"
    if seconds < 60:
        return f"{int(round(seconds))} giây"
    minutes = int(round(seconds / 60.0))
    if minutes < 60:
        return f"{minutes} phút"
    hours = minutes // 60
    remain_min = minutes % 60
    if remain_min == 0:
        return f"{hours} giờ"
    return f"{hours} giờ {remain_min} phút"
