import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_consent_and_batch_ingestion(client: AsyncClient):
    """Test consent recording and idempotent event batch ingestion."""
    device_id = "device_test_12345"

    # 1. Grant consent
    consent_resp = await client.post("/api/v1/analytics/consent", json={
        "device_id": device_id,
        "consent_granted": True,
        "scopes": ["events", "route_sampling"]
    })
    assert consent_resp.status_code == 200
    assert consent_resp.json()["consent_granted"] is True

    # 2. Ingest batch of events (with 1 duplicate event_id)
    events = [
        {
            "event_id": "ev_001",
            "session_id": "sess_test_1",
            "poi_id": "poi_ben_nha_rong",
            "event_type": "audio_start",
            "properties": {"playback_id": "pb_1", "lang": "vi"}
        },
        {
            "event_id": "ev_002",
            "session_id": "sess_test_1",
            "poi_id": "poi_ben_nha_rong",
            "event_type": "audio_end",
            "properties": {"playback_id": "pb_1", "listened_ms": 45000}
        },
        # Duplicate of ev_001
        {
            "event_id": "ev_001",
            "session_id": "sess_test_1",
            "poi_id": "poi_ben_nha_rong",
            "event_type": "audio_start",
            "properties": {"playback_id": "pb_1", "lang": "vi"}
        }
    ]

    ingest_resp = await client.post("/api/v1/analytics/events/batch", json={"events": events})
    assert ingest_resp.status_code == 200
    res_data = ingest_resp.json()
    assert res_data["success_count"] == 2
    assert res_data["duplicate_count"] == 1
    assert "ev_001" in res_data["acked_ids"]
    assert "ev_002" in res_data["acked_ids"]


@pytest.mark.asyncio
async def test_analytics_dashboard(client: AsyncClient):
    """Test dashboard stats calculation (safe average duration without division by zero)."""
    admin_login = await client.post("/api/v1/admin/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dash_resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    data = dash_resp.json()
    assert "total_active_pois" in data
    assert "avg_listen_duration_seconds" in data
    assert isinstance(data["avg_listen_duration_seconds"], (int, float))
