"""Tests for serminar.bkpvp.top domain, Cloudflare headers, and Google OAuth callback."""

import pytest
from httpx import AsyncClient, ASGITransport
from urllib.parse import parse_qs, urlparse

from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_cors_allows_serminar_bkpvp_top():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test HTTPS origin
        res_https = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://serminar.bkpvp.top",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization, x-csrf-token",
            },
        )
        assert res_https.status_code == 200
        assert res_https.headers.get("access-control-allow-origin") == "https://serminar.bkpvp.top"
        assert res_https.headers.get("access-control-allow-credentials") == "true"

        # Test HTTP origin
        res_http = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://serminar.bkpvp.top",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization, x-csrf-token",
            },
        )
        assert res_http.status_code == 200
        assert res_http.headers.get("access-control-allow-origin") == "http://serminar.bkpvp.top"


@pytest.mark.asyncio
async def test_google_start_returns_serminar_redirect_uri():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/auth/google/start?return_to=/dashboard",
            headers={
                "Host": "serminar.bkpvp.top",
                "cf-visitor": '{"scheme":"https"}',
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") is True
        auth_url = data.get("auth_url")
        assert auth_url is not None

        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)
        assert "redirect_uri" in params
        assert params["redirect_uri"][0] == "https://serminar.bkpvp.top/api/v1/auth/google/callback"


@pytest.mark.asyncio
async def test_root_browser_redirects_to_admin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Browser request with Accept: text/html
        res = await client.get(
            "/",
            headers={"Accept": "text/html,application/xhtml+xml"},
            follow_redirects=False
        )
        assert res.status_code == 302
        assert res.headers.get("location") == "/admin/"

        # API client request with Accept: application/json
        res_api = await client.get(
            "/",
            headers={"Accept": "application/json"}
        )
        assert res_api.status_code == 200
        data = res_api.json()
        assert "documentation" in data
