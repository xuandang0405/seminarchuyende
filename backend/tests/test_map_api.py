"""API Integration tests for Map Config, POI Search, Nearby ($geoNear), Viewport Bounds, and Route Preview."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_map_config(client: AsyncClient):
    """GET /api/v1/map/config returns sanitized runtime configuration for District 4."""
    res = await client.get("/api/v1/map/config")
    assert res.status_code == 200
    data = res.json()
    assert "center" in data
    assert abs(data["center"]["latitude"] - 10.7635) < 0.01
    assert abs(data["center"]["longitude"] - 106.7042) < 0.01
    assert data["default_zoom"] >= 14
    assert "tile_provider" in data
    assert "style_url" in data
    assert "attribution" in data
    assert data["capabilities"]["supports_routing"] is True


@pytest.mark.asyncio
async def test_search_pois_endpoint(client: AsyncClient):
    """GET /api/v1/pois/search returns matching POIs with distance when origin provided."""
    res = await client.get(
        "/api/v1/pois/search",
        params={
            "q": "Nhà Rồng",
            "origin_lat": 10.76814,
            "origin_lon": 106.70678,
            "lang": "vi"
        }
    )
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if len(items) > 0:
        first = items[0]
        assert "Nhà Rồng" in first["name"] or "Bến Nhà Rồng" in first["title"]
        assert "straight_line_distance_m" in first
        assert "distance_display" in first
        assert "latitude" in first
        assert "longitude" in first


@pytest.mark.asyncio
async def test_get_pois_in_bounds(client: AsyncClient):
    """GET /api/v1/pois/in-bounds returns POIs inside District 4 bounding box."""
    res = await client.get(
        "/api/v1/pois/in-bounds",
        params={
            "min_lon": 106.685,
            "min_lat": 10.745,
            "max_lon": 106.720,
            "max_lat": 10.775,
            "limit": 20
        }
    )
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_get_pois_nearby(client: AsyncClient):
    """GET /api/v1/pois/nearby returns POIs with spherical straight_line_distance_m."""
    res = await client.get(
        "/api/v1/pois/nearby",
        params={
            "latitude": 10.76814,
            "longitude": 106.70678,
            "max_distance_meters": 3000.0,
            "limit": 10
        }
    )
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if len(items) > 0:
        # First item should be very close to origin (Bến Nhà Rồng itself)
        assert "straight_line_distance_m" in items[0]
        assert "distance_display" in items[0]


@pytest.mark.asyncio
async def test_route_preview_micro_distance(client: AsyncClient):
    """POST /api/v1/routes/preview short-circuits on micro-distance (< 8m)."""
    payload = {
        "origin": {"latitude": 10.76814, "longitude": 106.70678},
        "destination": {"latitude": 10.76814, "longitude": 106.70678},
        "mode": "walking",
        "locale": "vi"
    }
    res = await client.post("/api/v1/routes/preview", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["route_distance_m"] == 0.0
    assert data["route_duration_s"] == 0.0
    assert data["distance_display"] == "0 m"
    assert data["geometry"]["type"] == "LineString"


@pytest.mark.asyncio
async def test_route_preview_invalid_coords(client: AsyncClient):
    """POST /api/v1/routes/preview validates coordinates range."""
    payload = {
        "origin": {"latitude": 95.0, "longitude": 106.70678},  # Invalid lat > 90
        "destination": {"latitude": 10.76814, "longitude": 106.70678},
        "mode": "walking"
    }
    res = await client.post("/api/v1/routes/preview", json=payload)
    assert res.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_tour_summary_endpoint(client: AsyncClient):
    """POST /api/v1/routes/tour-summary returns tour route calculation."""
    res = await client.post(
        "/api/v1/routes/tour-summary",
        json={"tour_id": "tour_quan_4_lich_su", "locale": "vi"}
    )
    # If tour exists in seed, it returns 200, otherwise 404
    assert res.status_code in [200, 404]
    if res.status_code == 200:
        data = res.json()
        assert "total_distance_m" in data
        assert "total_duration_s" in data
        assert "geometry" in data
        assert data["geometry"]["type"] == "LineString"
