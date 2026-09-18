import math
import pytest
from app.services.geo_calc import (
    validate_coordinates,
    haversine_distance_meters,
    format_distance_display,
    format_duration_display,
)


def test_validate_coordinates_valid():
    lat, lon = validate_coordinates(10.7684, 106.7067)
    assert lat == 10.7684
    assert lon == 106.7067


def test_validate_coordinates_invalid_bounds():
    with pytest.raises(ValueError, match="Vĩ độ 95.0 không hợp lệ"):
        validate_coordinates(95.0, 106.7)

    with pytest.raises(ValueError, match="Kinh độ -190.0 không hợp lệ"):
        validate_coordinates(10.7, -190.0)


def test_validate_coordinates_nan_inf():
    with pytest.raises(ValueError, match="NaN hoặc Infinity"):
        validate_coordinates(float("nan"), 106.7)

    with pytest.raises(ValueError, match="NaN hoặc Infinity"):
        validate_coordinates(10.7, float("inf"))


def test_haversine_distance_same_point():
    d = haversine_distance_meters(10.7684, 106.7067, 10.7684, 106.7067)
    assert d == 0.0


def test_haversine_distance_district_4_landmarks():
    # Bến Nhà Rồng: (10.768420, 106.706790)
    # Cầu Mống: (10.769850, 106.704720)
    dist = haversine_distance_meters(10.768420, 106.706790, 10.769850, 106.704720)
    # Straight-line distance is approximately 275m
    assert 250.0 < dist < 320.0


def test_haversine_distance_symmetry():
    d1 = haversine_distance_meters(10.768420, 106.706790, 10.769850, 106.704720)
    d2 = haversine_distance_meters(10.769850, 106.704720, 10.768420, 106.706790)
    assert d1 == d2


def test_format_distance_display():
    assert format_distance_display(450.3) == "450 m"
    assert format_distance_display(1300.0) == "1.3 km"
    assert format_distance_display(0) == "0 m"


def test_format_duration_display():
    assert format_duration_display(45) == "45 giây"
    assert format_duration_display(180) == "3 phút"
    assert format_duration_display(3600) == "1 giờ"
    assert format_duration_display(4500) == "1 giờ 15 phút"
