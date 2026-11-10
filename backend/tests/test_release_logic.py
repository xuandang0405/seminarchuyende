import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException
from app.core.config import settings
from app.core.database import db_manager
from app.db.collections import COLLECTION_POI, COLLECTION_TOURS
from app.services.translation_service import translation_service
from app.services.access_service import access_service
from app.services.tts_service import tts_service

@pytest.fixture
async def catalog():
    poi = {"_id": "logic-poi", "name": "Saved source", "description": "Latest editor text", "version": 1,
           "content_version": 1, "is_active": True, "deleted_at": None}
    await db_manager.db[COLLECTION_POI].insert_one(poi)
    await db_manager.db[COLLECTION_TOURS].insert_one({"_id": "logic-tour", "name": "Logic tour", "poi_ids": [poi["_id"]],
        "price_amount": 99000, "is_active": True, "is_purchasable": True, "preview_enabled": True})
    return poi

@pytest.mark.asyncio
async def test_missing_audio_does_not_consume_trial_and_guest_resumes(client, catalog, monkeypatch):
    synthesize = AsyncMock(return_value={"success": False})
    monkeypatch.setattr(tts_service, "generate_with_google_tts", synthesize)
    guest = (await client.post("/api/v1/guest-sessions")).json()
    again = (await client.post("/api/v1/guest-sessions")).json()
    assert guest["guest_session_id"] == again["guest_session_id"]
    intent = {"tour_id": "logic-tour", "poi_id": catalog["_id"]}
    pending = await client.post("/api/v1/playback-grants", json={**intent, "trigger_source": "gps"})
    assert pending.status_code == 403
    assert pending.json()["detail"]["error_code"] == "TRIAL_CONSENT_REQUIRED"
    synthesize.assert_not_awaited()
    response = await client.post("/api/v1/playback-grants", json={**intent, "consent_trial": True})
    assert response.status_code == 409
    synthesize.assert_awaited_once()
    access = await client.get("/api/v1/tours/logic-tour/access")
    assert access.json()["trial_remaining"] == 1
    assert not Path(settings.MEDIA_STORAGE_DIR, "audio", "logic-poi_vi.mp3").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("paid", [False, True])
async def test_missing_mp3_streams_google_tts_for_authorized_playback(client, catalog, monkeypatch, paid):
    if not paid:
        await db_manager.db[COLLECTION_TOURS].delete_one({"_id": "logic-tour"})
    await db_manager.db["poi_localizations"].insert_one({"poi_id": catalog["_id"], "lang": "ja",
        "description": "日本語の案内です。", "translation_status": "ready", "source_version": 1,
        "audio_status": "ready", "audio_storage_key": "audio/missing.mp3"})
    Path(settings.MEDIA_STORAGE_DIR, "audio", "missing.mp3").touch()
    audio = b"ID3-test-narration"

    async def synthesize(text, lang, output_filename):
        assert text == "日本語の案内です。" and lang == "ja"
        Path(settings.MEDIA_STORAGE_DIR, "audio", output_filename).write_bytes(audio)
        return {"success": True}

    generate = AsyncMock(side_effect=synthesize)
    monkeypatch.setattr(tts_service, "generate_with_google_tts", generate)
    await client.post("/api/v1/guest-sessions")
    body = {"poi_id": catalog["_id"], "lang": "ja", "consent_trial": paid, "idempotency_key": "tts-click"}
    for _ in range(2):
        response = await client.post("/api/v1/playback-grants", json=body)
        assert response.status_code == 200
        grant = response.json()
        assert grant["lang"] == "ja" and grant["scope"] == ("trial" if paid else "public")
        assert grant["trial_consumed"] is paid
        stream = await client.get(grant["stream_url"], headers={"Range": "bytes=4-"})
        assert stream.status_code == 206 and stream.content == audio[4:]
    generate.assert_awaited_once()
    denied = await client.get(grant["stream_url"].split("?", 1)[0])
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_trial_grant_retry_reuses_authorization(client, catalog):
    Path(settings.MEDIA_STORAGE_DIR, "audio", "logic-poi_vi.mp3").write_bytes(b"ID3-test-stream")
    await client.post("/api/v1/guest-sessions")
    body = {"tour_id": "logic-tour", "poi_id": catalog["_id"], "consent_trial": True, "idempotency_key": "same-click"}
    first = await client.post("/api/v1/playback-grants", json=body)
    second = await client.post("/api/v1/playback-grants", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["grant_token"] == second.json()["grant_token"]
    stream = await client.get(first.json()["stream_url"], headers={"Range": "bytes=-6"})
    assert stream.status_code == 206 and stream.content == b"stream"
    invalid = await client.get(first.json()["stream_url"], headers={"Range": "bytes=9999-"})
    assert invalid.status_code == 416


@pytest.mark.asyncio
async def test_live_presence_without_device_tracking_is_idempotent(client):
    path = "/api/v1/analytics/live-snapshot"
    assert (await client.get(path)).status_code == 401
    lease = {"lease_id": uuid4().hex, "active": True}
    for _ in range(2):
        assert (await client.post("/api/v1/analytics/runtime/presence", json=lease)).status_code == 204
    login = await client.post("/api/v1/auth/admin/login", json={"email": "admin@tourvoice.vn", "password": "Admin@123456"})
    assert login.status_code == 200
    snapshot = (await client.get(path)).json()["overview"]
    assert snapshot["live_web_sessions"] == 1
    assert snapshot["active_visitor_sessions_now"] == 0
    assert await db_manager.db["analytics_devices"].count_documents({}) == 0
    await client.post("/api/v1/analytics/runtime/presence", json={**lease, "active": False})
    assert (await client.get(path)).json()["overview"]["live_web_sessions"] == 0


@pytest.mark.asyncio
async def test_live_listening_counts_only_delivered_audio_without_duplicate_metrics(client, catalog):
    Path(settings.MEDIA_STORAGE_DIR, "audio", "logic-poi_vi.mp3").write_bytes(b"ID3-test-stream")
    await client.post("/api/v1/guest-sessions")
    response = await client.post("/api/v1/playback-grants", json={"tour_id": "logic-tour",
        "poi_id": catalog["_id"], "consent_trial": True})
    assert response.status_code == 200
    grant = response.json()
    path = "/api/v1/analytics/runtime/listen"
    body = {"grant_token": grant["grant_token"]}
    assert (await client.post(path, json=body)).status_code == 404
    assert (await client.get(grant["stream_url"], headers={"Range": "bytes=0-5"})).status_code == 206
    await db_manager.db["playback_grants"].update_one({"_id": grant["playback_id"]},
        {"$set": {"first_delivered_at": datetime.now(timezone.utc) - timedelta(seconds=5)}})
    for extra in ({}, {"listened_ms": 2000}, {"listened_ms": 1500}, {"listened_ms": 3200, "completed": True},
                  {"listened_ms": 3200, "completed": True}):
        assert (await client.post(path, json={**body, **extra})).status_code == 204
    await client.post("/api/v1/auth/admin/login", json={"email": "admin@tourvoice.vn", "password": "Admin@123456"})
    overview = (await client.get("/api/v1/analytics/live-snapshot")).json()
    poi = next(item for item in overview["pois"] if item["poi_id"] == catalog["_id"])
    assert poi["listen_started_count"] == poi["listen_completed_count"] == 1
    assert poi["total_listened_seconds"] == 3.2 and poi["unique_devices"] == 0
    assert not await db_manager.db["analytics_events"].find_one({"playback_id": grant["playback_id"]})


@pytest.mark.asyncio
async def test_saved_text_cannot_be_overwritten_by_stale_translation(catalog):
    async def change_version(*args):
        await db_manager.db[COLLECTION_POI].update_one({"_id": catalog["_id"]},
            {"$set": {"content_version": 2, "description": "New revision", "is_active": False}})
        return {"en": {"success": True, "status": "ready", "audio_url": "/storage/audio/old.mp3"}}
    with patch.object(translation_service, "get_or_create_translations", new=AsyncMock(return_value={
        "vi": {"name": catalog["name"], "description": catalog["description"]},
        "en": {"name": "English", "description": "Old English"}})), patch.object(
            translation_service, "generate_tts_for_poi", new=change_version):
        with pytest.raises(RuntimeError, match="Stale"):
            await translation_service.sync_poi_multilingual(catalog["_id"], catalog["name"], catalog["description"], db_manager.db, 1)
    poi = await db_manager.db[COLLECTION_POI].find_one({"_id": catalog["_id"]})
    assert poi["description"] == "New revision" and not poi["is_active"]
    assert not await db_manager.db["poi_localizations"].find_one({"poi_id": catalog["_id"]})

@pytest.mark.asyncio
async def test_legacy_content_has_no_cross_owner_write_or_fake_publish(client, catalog):
    from app.repositories.content_repo import content_repo
    content = {"_id": "private-content", "poi_id": catalog["_id"], "language_code": "en", "version": 1,
               "source_version": 1, "review_status": "approved", "title": "Private", "narration_text": "Private narration"}
    await content_repo.insert_one(content)
    login = await client.post("/api/v1/auth/login", json={"email": "owner.verified@quan4.vn", "password": "Owner@123456"})
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    changed = await client.put("/api/v1/pois/logic-poi/contents/private-content",
        headers=headers, json={"narration_text": "Attempted overwrite"})
    assert changed.status_code == 403
    assert (await client.get("/api/v1/jobs", headers=headers)).status_code == 403
    login = await client.post("/api/v1/auth/login", json={"email": "admin@tourvoice.vn", "password": "Admin@123456"})
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    result = await client.post("/api/v1/pois/logic-poi/contents/private-content/publish", headers=headers)
    assert result.status_code == 409

@pytest.mark.asyncio
async def test_owner_cannot_smuggle_publication_fields(client):
    login = await client.post("/api/v1/auth/login", json={"email": "owner.verified@quan4.vn", "password": "Owner@123456"})
    response = await client.post("/api/v1/owner/submissions", headers={"Authorization": "Bearer " + login.json()["access_token"]},
        json={"action": "update", "poi_id": "other", "payload": {"owner_id": "another-owner", "is_active": True}})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_cancelled_task_cannot_publish_results(catalog):
    from app.repositories.audio_repo import audio_repo
    from app.services.localization_worker import process_one
    task = await audio_repo.create_task("admin", [{"poi_id": catalog["_id"], "input_version": 1}])
    await audio_repo.request_cancel(task["_id"])
    with patch.object(translation_service, "sync_poi_multilingual", new_callable=AsyncMock) as sync:
        assert not await process_one()
        sync.assert_not_awaited()
    assert (await audio_repo.get_by_id(task["_id"]))["status"] == "cancelled"

@pytest.mark.asyncio
async def test_single_language_worker_discards_a_result_after_a_source_edit(catalog, monkeypatch):
    from app.repositories.audio_repo import audio_repo
    from app.services.localization_worker import process_one
    from app.services.tts_service import tts_service

    async def tts_during_edit(*args):
        await db_manager.db[COLLECTION_POI].update_one({"_id": catalog["_id"]}, {"$set": {"content_version": 2}})
        return {"success": True, "audio_url": "/storage/audio/old.mp3", "audio_storage_key": "audio/old.mp3",
                "audio_duration_ms": 1000}

    monkeypatch.setattr(tts_service, "generate_audio_for_text", tts_during_edit)
    await audio_repo.create_task("admin", [{"poi_id": catalog["_id"], "input_version": 1, "lang": "vi"}])
    assert await process_one()
    assert not await db_manager.db["poi_localizations"].find_one({"poi_id": catalog["_id"]})


@pytest.mark.asyncio
async def test_edge_403_localization_task_completes_with_google(catalog, monkeypatch):
    import edge_tts
    from aiohttp import WSServerHandshakeError
    from app.repositories.audio_repo import audio_repo
    from app.services.localization_worker import process_one

    class RefusedEdge:
        def __init__(self, text, voice):
            pass

        async def save(self, path):
            raise WSServerHandshakeError(None, (), status=403)

    audio_key = "audio/google-narration.mp3"
    google = AsyncMock(return_value={"success": True, "audio_url": f"/storage/{audio_key}",
        "audio_storage_key": audio_key, "audio_duration_ms": 1500, "provider": "google_tts"})
    monkeypatch.setattr(edge_tts, "Communicate", RefusedEdge)
    monkeypatch.setattr(tts_service, "_generate_google_mp3", google)
    task = await audio_repo.create_task("admin", [{"poi_id": catalog["_id"], "input_version": 1,
        "lang": "vi", "provider": "edge"}])

    assert await process_one()
    google.assert_awaited_once_with("Saved source. Latest editor text", "vi", None)
    assert (await audio_repo.get_by_id(task["_id"]))["status"] == "succeeded"
    localization = await db_manager.db["poi_localizations"].find_one({"poi_id": catalog["_id"], "lang": "vi"})
    assert localization["audio_status"] == "ready" and localization["audio_storage_key"] == audio_key


@pytest.mark.asyncio
async def test_user_order_list_does_not_raise_typeerror(client):
    response = await client.post("/api/v1/auth/login", json={"email": "tourist@test.vn", "password": "User@123456"})
    orders = await client.get("/api/v1/orders?status=paid", headers={"Authorization": "Bearer " + response.json()["access_token"]})
    assert orders.status_code == 200

def test_password_suffix_is_not_truncated():
    from app.core.security import get_password_hash, verify_password
    password = "ắ" * 40 + "correct-tail"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("ắ" * 40 + "wrong-tail", hashed)
