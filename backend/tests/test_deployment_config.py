"""Tests for Deployment Configuration, CORS normalization, and Same-Origin / Proxy support."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import Settings


def test_settings_cors_origins_parsing():
    s = Settings(
        CORS_ORIGINS="http://1.55.58.251:8000, https://tour.quan4.vn",
        PUBLIC_WEB_URL="https://tour.quan4.vn"
    )
    assert "http://1.55.58.251:8000" in s.CORS_ORIGINS
    assert "https://tour.quan4.vn" in s.CORS_ORIGINS


def test_settings_public_web_url():
    s = Settings(PUBLIC_WEB_URL="https://custom.domain.com")
    assert s.PUBLIC_WEB_URL == "https://custom.domain.com"


@pytest.mark.asyncio
async def test_cors_preflight_options():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send an OPTIONS preflight request
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization, x-csrf-token",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:8000"
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_health_check_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "degraded"]
