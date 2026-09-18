"""Comprehensive tests for Device Bootstrap, Visitor Sessions, Tour Sessions, and Analytics Events.

Tests BR-DEVICE-*, BR-SESSION-*, BR-TOUR-SESSION-*, BR-LISTEN-*, BR-SYNC-*.
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.main import app
from app.db.collections import (
    COLLECTION_ANALYTICS_DEVICES,
    COLLECTION_ANALYTICS_SESSIONS,
    COLLECTION_TOUR_SESSIONS,
    COLLECTION_ANALYTICS_EVENTS,
    COLLECTION_ANALYTICS_POI_DAILY_METRICS,
)


@pytest.mark.asyncio
async def test_device_bootstrap_generates_token_and_hash():
    """BR-DEVICE-01: Server generates 256-bit token, stores hash, returns device_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/device/bootstrap", json={"platform": "web"})
        assert res.status_code == 200
        data = res.json()
        assert "device_id" in data
        assert "device_token" in data
        assert data["is_new"] is True
        assert data["device_id"].startswith("dev_")

        # Calling bootstrap again with the same token should recover the identity (not create new)
        res2 = await ac.post("/api/v1/device/bootstrap", json={
            "device_token": data["device_token"],
            "platform": "web"
        })
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["device_id"] == data["device_id"]
        assert data2["is_new"] is False


@pytest.mark.asyncio
async def test_distinct_devices_same_ip():
    """BR-DEVICE-02: Two distinct devices bootstrapped from same client IP get distinct identities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac1:
        res1 = await ac1.post("/api/v1/device/bootstrap", json={"platform": "web"})
    async with AsyncClient(transport=transport, base_url="http://test") as ac2:
        res2 = await ac2.post("/api/v1/device/bootstrap", json={"platform": "android"})

    dev1 = res1.json()
    dev2 = res2.json()
    assert dev1["device_id"] != dev2["device_id"]
    assert dev1["device_token"] != dev2["device_token"]


@pytest.mark.asyncio
async def test_visitor_session_lifecycle_and_heartbeat():
    """BR-SESSION-01: Visitor session start-or-resume and conditional heartbeat."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Bootstrap device
        boot_res = await ac.post("/api/v1/device/bootstrap", json={"platform": "web"})
        dev_token = boot_res.json()["device_token"]

        # 2. Start visitor session
        sess_res = await ac.post(
            "/api/v1/visitor-sessions/start-or-resume",
            json={"device_token": dev_token, "platform": "web", "locale": "vi"},
            headers={"x-device-token": dev_token}
        )
        assert sess_res.status_code == 200
        sess_data = sess_res.json()
        session_id = sess_data["_id"]
        assert sess_data["status"] == "active"

        # 3. Resume session within 15 min returns the same session_id (idempotent)
        sess_resume = await ac.post(
            "/api/v1/visitor-sessions/start-or-resume",
            json={"device_token": dev_token, "platform": "web"},
            headers={"x-device-token": dev_token}
        )
        assert sess_resume.json()["_id"] == session_id

        # 4. Heartbeat updates last_seen_at
        hb_res = await ac.post(
            f"/api/v1/visitor-sessions/{session_id}/heartbeat",
            headers={"x-device-token": dev_token}
        )
        assert hb_res.status_code == 200
        assert hb_res.json()["status"] == "active"

        # 5. End session
        end_res = await ac.post(
            f"/api/v1/visitor-sessions/{session_id}/end",
            headers={"x-device-token": dev_token}
        )
        assert end_res.status_code == 200
        assert end_res.json()["status"] == "ended"


@pytest.mark.asyncio
async def test_tour_session_idempotent_start_and_progress():
    """BR-TOUR-SESSION-01: Idempotent tour session start and progress updates."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        boot_res = await ac.post("/api/v1/device/bootstrap", json={"platform": "web"})
        dev_token = boot_res.json()["device_token"]

        sess_res = await ac.post(
            "/api/v1/visitor-sessions/start-or-resume",
            json={"device_token": dev_token, "platform": "web"},
            headers={"x-device-token": dev_token}
        )
        vis_session_id = sess_res.json()["_id"]

        idempotency_key = f"idemp_{uuid.uuid4().hex}"

        # 1. Start tour session
        tour_start_res = await ac.post(
            "/api/v1/tour-sessions",
            json={
                "tour_id": "tour_quan_4_lich_su",
                "visitor_session_id": vis_session_id,
                "idempotency_key": idempotency_key,
                "start_poi_id": "poi_ben_nha_rong"
            },
            headers={"x-device-token": dev_token}
        )
        assert tour_start_res.status_code == 201
        tour_sess = tour_start_res.json()
        ts_id = tour_sess["_id"]
        assert tour_sess["status"] == "active"

        # 2. Retry with same idempotency_key returns identical session (no duplicate)
        retry_res = await ac.post(
            "/api/v1/tour-sessions",
            json={
                "tour_id": "tour_quan_4_lich_su",
                "visitor_session_id": vis_session_id,
                "idempotency_key": idempotency_key
            },
            headers={"x-device-token": dev_token}
        )
        assert retry_res.status_code == 201
        assert retry_res.json()["_id"] == ts_id

        # 3. Patch progress
        patch_res = await ac.patch(
            f"/api/v1/tour-sessions/{ts_id}",
            json={
                "last_poi_id": "poi_cau_mong",
                "completed_poi_ids": ["poi_ben_nha_rong", "poi_cau_mong"],
                "progress_percentage": 50.0
            },
            headers={"x-device-token": dev_token}
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["progress_percentage"] == 50.0

        # 4. Complete tour session
        comp_res = await ac.patch(
            f"/api/v1/tour-sessions/{ts_id}",
            json={"status": "completed", "progress_percentage": 100.0},
            headers={"x-device-token": dev_token}
        )
        assert comp_res.status_code == 200
        assert comp_res.json()["status"] == "completed"
        assert comp_res.json()["ended_at"] is not None


@pytest.mark.asyncio
async def test_analytics_batch_ingest_with_per_item_ack():
    """BR-SYNC-01: Ingest batch events returning per-item ACKs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        boot_res = await ac.post("/api/v1/device/bootstrap", json={"platform": "web"})
        dev_token = boot_res.json()["device_token"]

        ev1_id = f"ev_{uuid.uuid4().hex}"
        ev2_id = f"ev_{uuid.uuid4().hex}"

        batch_payload = {
            "events": [
                {
                    "event_id": ev1_id,
                    "event_type": "poi_viewed",
                    "poi_id": "poi_ben_nha_rong",
                    "source": "gps"
                },
                {
                    "event_id": ev2_id,
                    "event_type": "qr_scanned",
                    "poi_id": "poi_cau_mong",
                    "source": "qr"
                }
            ]
        }

        # First ingestion -> all accepted
        res = await ac.post(
            "/api/v1/analytics/events/batch",
            json=batch_payload,
            headers={"x-device-token": dev_token}
        )
        assert res.status_code == 200
        ack_data = res.json()
        assert ack_data["total"] == 2
        assert ack_data["accepted_count"] == 2
        assert ack_data["duplicate_count"] == 0
        assert all(a["status"] == "accepted" for a in ack_data["acks"])

        # Re-sending same events -> all acknowledged as duplicate
        res_dup = await ac.post(
            "/api/v1/analytics/events/batch",
            json=batch_payload,
            headers={"x-device-token": dev_token}
        )
        assert res_dup.status_code == 200
        dup_data = res_dup.json()
        assert dup_data["accepted_count"] == 0
        assert dup_data["duplicate_count"] == 2
        assert all(a["status"] == "duplicate" for a in dup_data["acks"])


@pytest.mark.asyncio
async def test_idempotent_listen_counting():
    """BR-LISTEN-01 & BR-LISTEN-02:
    - listen_started_count increments once on genuine narration_started.
    - pause/resume/progress/duplicate events do NOT increment.
    - listen_completed_count increments once on narration_completed.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        boot_res = await ac.post("/api/v1/device/bootstrap", json={"platform": "web"})
        dev_token = boot_res.json()["device_token"]

        playback_id = f"pb_{uuid.uuid4().hex[:12]}"
        poi_id = "poi_pho_oc_vinh_khanh"

        ev_start_id = f"ev_start_{uuid.uuid4().hex}"
        ev_pause_id = f"ev_pause_{uuid.uuid4().hex}"
        ev_resume_id = f"ev_resume_{uuid.uuid4().hex}"
        ev_complete_id = f"ev_comp_{uuid.uuid4().hex}"

        # 1. Send narration_started
        r1 = await ac.post(
            "/api/v1/analytics/events/batch",
            json={"events": [{
                "event_id": ev_start_id,
                "event_type": "narration_started",
                "playback_id": playback_id,
                "poi_id": poi_id,
                "source": "gps"
            }]},
            headers={"x-device-token": dev_token}
        )
        assert r1.status_code == 200
        assert r1.json()["accepted_count"] == 1

        # Check POI metrics: started = 1
        top_pois_res = await ac.get("/api/v1/analytics/pois")
        assert top_pois_res.status_code == 200
        pois_list = top_pois_res.json()
        poi_metric = next((p for p in pois_list if p["poi_id"] == poi_id), None)
        assert poi_metric is not None
        assert poi_metric["listen_started_count"] == 1
        assert poi_metric["listen_completed_count"] == 0

        # 2. Send pause and resume -> count MUST NOT increase
        r2 = await ac.post(
            "/api/v1/analytics/events/batch",
            json={"events": [
                {
                    "event_id": ev_pause_id,
                    "event_type": "narration_paused",
                    "playback_id": playback_id,
                    "poi_id": poi_id
                },
                {
                    "event_id": ev_resume_id,
                    "event_type": "narration_resumed",
                    "playback_id": playback_id,
                    "poi_id": poi_id
                }
            ]},
            headers={"x-device-token": dev_token}
        )
        assert r2.status_code == 200

        # Check again: started is STILL 1
        pois_list2 = (await ac.get("/api/v1/analytics/pois")).json()
        poi_metric2 = next((p for p in pois_list2 if p["poi_id"] == poi_id), None)
        assert poi_metric2["listen_started_count"] == 1

        # 3. Send duplicate narration_started with different event_id but same playback_id -> MUST NOT increase
        ev_start2_id = f"ev_start2_{uuid.uuid4().hex}"
        r3 = await ac.post(
            "/api/v1/analytics/events/batch",
            json={"events": [{
                "event_id": ev_start2_id,
                "event_type": "narration_started",
                "playback_id": playback_id,
                "poi_id": poi_id
            }]},
            headers={"x-device-token": dev_token}
        )
        assert r3.status_code == 200
        pois_list3 = (await ac.get("/api/v1/analytics/pois")).json()
        poi_metric3 = next((p for p in pois_list3 if p["poi_id"] == poi_id), None)
        assert poi_metric3["listen_started_count"] == 1

        # 4. Send narration_completed -> listen_completed_count increments to 1
        r4 = await ac.post(
            "/api/v1/analytics/events/batch",
            json={"events": [{
                "event_id": ev_complete_id,
                "event_type": "narration_completed",
                "playback_id": playback_id,
                "poi_id": poi_id
            }]},
            headers={"x-device-token": dev_token}
        )
        assert r4.status_code == 200
        pois_list4 = (await ac.get("/api/v1/analytics/pois")).json()
        poi_metric4 = next((p for p in pois_list4 if p["poi_id"] == poi_id), None)
        assert poi_metric4["listen_completed_count"] == 1


@pytest.mark.asyncio
async def test_admin_analytics_overview_and_tours():
    """Section 17: Admin analytics overview and tour stats with non-zero safe metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        overview_res = await ac.get("/api/v1/analytics/overview")
        assert overview_res.status_code == 200
        overview = overview_res.json()
        assert "active_visitor_sessions_now" in overview
        assert "unique_devices_count" in overview
        assert "tour_completion_rate_percent" in overview
        assert "data_freshness_watermark" in overview
        assert isinstance(overview["unique_devices_count"], int)

        tours_res = await ac.get("/api/v1/analytics/tours")
        assert tours_res.status_code == 200
        tours = tours_res.json()
        assert isinstance(tours, list)
