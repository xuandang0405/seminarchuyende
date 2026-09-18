"""Unit tests for GeoService (pure geospatial calculations, Haversine, validation, formatting)."""

import pytest
import math
from app.services.geo_service import (
    haversine_distance_meters,
    validate_coordinates,
    validate_bbox,
    format_distance_display,
    format_duration_display,
    coords_to_geojson_point,
    geojson_point_to_coords,
    quantize_coordinate,
)


def test_haversine_identical_points():
    """Distance between identical coordinates must be exactly 0.0."""
    d = haversine_distance_meters(10.76814, 106.70678, 10.76814, 106.70678)
    assert d == 0.0


def test_haversine_known_district_4_coords():
    """Distance between Bến Nhà Rồng (10.76814, 106.70678) and Cầu Mống (10.76890, 106.70420).

    Expected geographic straight-line distance is ~290 - 310 meters.
    """
    d = haversine_distance_meters(10.76814, 106.70678, 10.76890, 106.70420)
    assert 280.0 <= d <= 320.0


def test_haversine_symmetry():
    """Distance from A to B must equal distance from B to A."""
    d1 = haversine_distance_meters(10.76814, 106.70678, 10.76045, 106.70012)
    d2 = haversine_distance_meters(10.76045, 106.70012, 10.76814, 106.70678)
    assert abs(d1 - d2) < 1e-6


def test_validate_coordinates_valid():
    """Valid coordinates should not raise exceptions."""
    validate_coordinates(10.76, 106.70)
    validate_coordinates(-90.0, -180.0)
    validate_coordinates(90.0, 180.0)


def test_validate_coordinates_invalid():
    """Invalid latitude or longitude should raise ValueError."""
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        validate_coordinates(91.0, 106.70)

    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        validate_coordinates(-90.1, 106.70)

    with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
        validate_coordinates(10.76, 180.5)

    with pytest.raises(ValueError, match="valid finite numbers"):
        validate_coordinates(float("nan"), 106.70)


def test_validate_bbox():
    """Valid bbox passes, inverted bbox raises ValueError."""
    validate_bbox(106.685, 10.745, 106.720, 10.775)

    with pytest.raises(ValueError, match="min_lon .* cannot be greater than max_lon"):
        validate_bbox(106.730, 10.745, 106.720, 10.775)

    with pytest.raises(ValueError, match="min_lat .* cannot be greater than max_lat"):
        validate_bbox(106.685, 10.780, 106.720, 10.775)


def test_format_distance_display():
    """Under 1000m shows 'X m', >= 1000m shows 'X.X km'."""
    assert format_distance_display(0) == "0 m"
    assert format_distance_display(450.4) == "450 m"
    assert format_distance_display(999.4) == "999 m"
    assert format_distance_display(1000.0) == "1.0 km"
    assert format_distance_display(1249.0) == "1.2 km"
    assert format_distance_display(2580.0) == "2.6 km"


def test_format_duration_display():
    """Duration formatted in Vietnamese and English."""
    assert format_duration_display(25, lang="vi") == "< 1 phút"
    assert format_duration_display(25, lang="en") == "< 1 min"
    assert format_duration_display(300, lang="vi") == "5 phút"
    assert format_duration_display(300, lang="en") == "5 mins"
    assert format_duration_display(3600, lang="vi") == "1 giờ"
    assert format_duration_display(3900, lang="vi") == "1 giờ 5 phút"
    assert format_duration_display(3900, lang="en") == "1h 5m"


def test_coords_to_geojson_and_back():
    """Coordinates (lat, lon) <-> GeoJSON Point [lon, lat]. NEVER invert."""
    lat, lon = 10.76814, 106.70678
    point = coords_to_geojson_point(lat, lon)
    assert point["type"] == "Point"
    assert point["coordinates"] == [106.70678, 10.76814]  # Longitude first in GeoJSON

    extracted_lat, extracted_lon = geojson_point_to_coords(point)
    assert extracted_lat == lat
    assert extracted_lon == lon


def test_quantize_coordinate():
    """Quantization to 4 decimal places."""
    qlat, qlon = quantize_coordinate(10.7681492, 106.7067814, precision=4)
    assert qlat == 10.7681
    assert qlon == 106.7068
