"""Integration tests for TourVoice District 4 standard endpoints."""

import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_admin_login(client: AsyncClient):
    """Test login via standard /admin/auth/login."""
    response = await client.post("/api/v1/admin/auth/login", json={
        "email": "superadmin@tourvoice.vn",
        "password": "Admin@123456"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "superadmin@tourvoice.vn"


@pytest.mark.asyncio
async def test_list_pois_standard(client: AsyncClient):
    """Test standard public POI listing."""
    res = await client.get("/api/v1/pois")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_qr_resolution_standard(client: AsyncClient):
    """Test QR resolution with seeded QR code."""
    res = await client.get("/api/v1/qr/Q4-BNR-01")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["poi_id"] == "poi_ben_nha_rong"
    assert "Nhà Rồng" in data["name"]


@pytest.mark.asyncio
async def test_tours_listing(client: AsyncClient):
    """Test tour listing and detail."""
    res = await client.get("/api/v1/tours")
    assert res.status_code == 200
    tours = res.json()
    assert len(tours) >= 2

    first_tour_id = tours[0]["id"]
    detail_res = await client.get(f"/api/v1/tours/{first_tour_id}")
    assert detail_res.status_code == 200
    assert "pois" in detail_res.json()
