import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "connected"


@pytest.mark.asyncio
async def test_admin_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/login", json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": settings.SUPERADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == settings.SUPERADMIN_EMAIL


@pytest.mark.asyncio
async def test_list_and_nearby_pois():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List POIs
        res = await ac.get("/api/v1/pois")
        assert res.status_code == 200
        pois = res.json()
        assert len(pois) >= 1

        # 2. Nearby POIs centered at Nha Rong Harbor (106.70678, 10.76814)
        nearby_res = await ac.get("/api/v1/pois/nearby", params={
            "longitude": 106.70678,
            "latitude": 10.76814,
            "max_distance_meters": 3000
        })
        assert nearby_res.status_code == 200
        nearby_pois = nearby_res.json()
        assert len(nearby_pois) >= 1
        assert any("NHA-RONG" in p["code"] for p in nearby_pois)


@pytest.mark.asyncio
async def test_owner_registration_and_approval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_login = await ac.post("/api/v1/auth/login", json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": settings.SUPERADMIN_PASSWORD
        })
        admin_token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        unique_email = f"owner_test_{int(time.time() * 1000)}@vinhkhanh.vn"
        reg_res = await ac.post("/api/v1/auth/owner-register", json={
            "email": unique_email,
            "password": "Password@123",
            "full_name": "Nguyen Van Chu Quan",
            "phone": "0901234567",
            "store_name": "Quan Oc Oanh Vinh Khanh",
            "store_address": "534 Vinh Khanh, Q4",
            "notes": "Quan lau doi nhat pho oc"
        })
        assert reg_res.status_code == 201
        owner_data = reg_res.json()
        assert owner_data["owner_status"] == "pending"
        owner_id = owner_data["_id"]

        review_res = await ac.post(f"/api/v1/admin/owners/{owner_id}/review", headers=headers, json={
            "action": "approve",
            "admin_notes": "Xac minh giay phep kinh doanh hop le"
        })
        assert review_res.status_code == 200
        assert review_res.json()["owner_status"] == "approved"


@pytest.mark.asyncio
async def test_qr_resolution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        pois_res = await ac.get("/api/v1/pois")
        poi = pois_res.json()[0]
        poi_id = poi["_id"]

        qr_list_res = await ac.get(f"/api/v1/qr/poi/{poi_id}")
        assert qr_list_res.status_code == 200
        qr_list = qr_list_res.json()
        if qr_list:
            qr_id = qr_list[0]["_id"]
            resolve_res = await ac.get(f"/api/v1/qr/resolve/{qr_id}", params={"language_code": "vi"})
            assert resolve_res.status_code == 200
            res_data = resolve_res.json()
            assert res_data["poi"]["_id"] == poi_id


@pytest.mark.asyncio
async def test_tts_generation_and_streaming():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_login = await ac.post("/api/v1/auth/login", json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": settings.SUPERADMIN_PASSWORD
        })
        token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get POI content
        pois_res = await ac.get("/api/v1/pois")
        poi_id = pois_res.json()[0]["_id"]
        contents_res = await ac.get(f"/api/v1/pois/{poi_id}/contents")
        content_id = contents_res.json()[0]["_id"]

        # Generate TTS audio
        tts_res = await ac.post(f"/api/v1/audio/generate-tts/{content_id}", headers=headers)
        assert tts_res.status_code == 201
        tts_data = tts_res.json()
        assert tts_data["duration_ms"] > 0
        assert len(tts_data["sha256"]) == 64
        storage_key = tts_data["storage_key"]

        # Stream audio file
        stream_res = await ac.get(f"/api/v1/audio/{storage_key}/stream")
        assert stream_res.status_code in (200, 206)
        assert stream_res.headers.get("content-type") == "audio/mpeg"


@pytest.mark.asyncio
async def test_offline_tour_package():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_login = await ac.post("/api/v1/auth/login", json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": settings.SUPERADMIN_PASSWORD
        })
        token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        tours_res = await ac.get("/api/v1/tours")
        assert tours_res.status_code == 200
        tours = tours_res.json()
        assert len(tours) >= 1
        tour_id = tours[0]["_id"]

        # Generate package
        pkg_res = await ac.post(f"/api/v1/packages/tours/{tour_id}/generate", headers=headers, params={"language_code": "vi"})
        assert pkg_res.status_code == 200
        pkg = pkg_res.json()
        assert "manifest" in pkg
        assert pkg["manifest"]["tour_id"] == tour_id
        assert pkg["manifest"]["language_code"] == "vi"
        assert len(pkg["manifest"]["pois"]) >= 1


@pytest.mark.asyncio
async def test_ai_narration_generation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_login = await ac.post("/api/v1/auth/login", json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": settings.SUPERADMIN_PASSWORD
        })
        token = admin_login.json()["access_token"]

        res = await ac.post("/api/v1/ai/generate-narration", headers={"Authorization": f"Bearer {token}"}, json={
            "poi_name": "Quan Oc Oanh",
            "category": "food",
            "specialties": ["Oc huong nuong moi", "Cang ghe rang muoi"],
            "weather": "mưa se se lạnh",
            "language_code": "vi"
        })
        assert res.status_code == 200
        data = res.json()
        assert "Oc Oanh" in data["title"]
        assert len(data["narration_text"]) > 20
        assert data["weather_context_applied"] == "mưa se se lạnh"


@pytest.mark.asyncio
async def test_telemetry_and_analytics_dashboard():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_login = await ac.post("/api/v1/auth/login", json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": settings.SUPERADMIN_PASSWORD
        })
        token = admin_login.json()["access_token"]

        session_res = await ac.post("/api/v1/sessions", json={"initial_language_code": "vi"})
        assert session_res.status_code == 201
        session_id = session_res.json()["_id"]

        playback_res = await ac.post("/api/v1/analytics/playbacks", json={
            "session_id": session_id,
            "audio_asset_id": "test-audio-uuid",
            "trigger_type": "gps"
        })
        assert playback_res.status_code == 201
        playback_id = playback_res.json()["_id"]

        batch_res = await ac.post("/api/v1/analytics/playback-events", json={
            "events": [
                {
                    "playback_id": playback_id,
                    "seq_no": 1,
                    "event_type": "start",
                    "listened_ms_total": 0,
                    "position_ms": 0,
                    "occurred_at": "2026-09-16T00:00:00Z"
                },
                {
                    "playback_id": playback_id,
                    "seq_no": 2,
                    "event_type": "progress",
                    "listened_ms_total": 15000,
                    "position_ms": 15000,
                    "occurred_at": "2026-09-16T00:00:15Z"
                }
            ]
        })
        assert batch_res.status_code == 200
        assert batch_res.json()["saved_count"] == 2

        dup_res = await ac.post("/api/v1/analytics/playback-events", json={
            "events": [
                {
                    "playback_id": playback_id,
                    "seq_no": 1,
                    "event_type": "start",
                    "listened_ms_total": 0,
                    "position_ms": 0,
                    "occurred_at": "2026-09-16T00:00:00Z"
                }
            ]
        })
        assert dup_res.json()["duplicates_count"] == 1
        assert dup_res.json()["saved_count"] == 0

        dash_res = await ac.get("/api/v1/analytics/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert dash_data["total_playbacks"] >= 1
        assert dash_data["total_sessions"] >= 1
