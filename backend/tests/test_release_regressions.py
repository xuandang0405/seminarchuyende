import pytest
from unittest.mock import AsyncMock, patch
from app.core.config import settings, Settings
from app.core.database import db_manager
from app.db.collections import COLLECTION_TOURS, COLLECTION_POI, COLLECTION_ADMIN_USERS
from httpx import ASGITransport, AsyncClient
from app.main import app


async def user(client, email="tourist@test.vn", password="User@123456"):
    response = await client.post('/api/v1/auth/login', json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()['access_token']}


@pytest.mark.asyncio
async def test_no_unauthenticated_checkout_or_customer_lookup(client):
    payload = {"item_id": "x", "customer_name": "test", "customer_phone": "0900000000", "unit_price": 0}
    assert (await client.post('/api/v1/payments/orders', json=payload)).status_code == 401
    assert (await client.get('/api/v1/payments/my-orders?email=tourist@test.vn')).status_code == 401
    assert (await client.get('/api/v1/payments/orders/unknown')).status_code == 401


@pytest.mark.asyncio
async def test_server_price_and_owner_scoped_order(client, monkeypatch):
    await db_manager.db[COLLECTION_TOURS].insert_one({"_id": "paid-review", "name": "Review tour", "price_amount": 99000,
        "is_active": True, "is_purchasable": True, "poi_ids": []})
    headers = await user(client)
    created = await client.post('/api/v1/payments/orders', headers=headers,
        json={"item_id": "paid-review", "customer_name": "test", "customer_phone": "0900000000", "unit_price": 0})
    assert created.status_code == 201, created.text
    order = created.json()['data']
    assert order['amount_vnd'] == 99000
    assert order['mock_mode'] is True
    other = await user(client, "owner.verified@quan4.vn", "Owner@123456")
    assert (await client.get('/api/v1/payments/orders/' + order['_id'], headers=other)).status_code == 403
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    monkeypatch.setattr(settings, 'PAYMENT_MODE', 'live')
    assert (await client.post('/api/v1/payments/orders/' + order['_id'] + '/simulate-success', headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_admin_orders_and_revenue_in_live_mode(client, monkeypatch):
    headers = await user(client, 'admin@tourvoice.vn', 'Admin@123456')
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    monkeypatch.setattr(settings, 'PAYMENT_MODE', 'live')
    assert (await client.get('/api/v1/payments/orders', headers=headers)).status_code == 200
    assert (await client.get('/api/v1/payments/revenue-summary', headers=headers)).status_code == 200


@pytest.mark.asyncio
async def test_production_reset_never_exposes_token_even_in_debug(client, monkeypatch):
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    monkeypatch.setattr(settings, 'DEBUG', True)
    with patch('app.services.password_recovery_service.send_password_reset', new_callable=AsyncMock):
        response = await client.post('/api/v1/auth/forgot-password', json={"email": "admin@tourvoice.vn"})
    assert response.status_code == 200
    assert not response.json().get('debug_token')


@pytest.mark.asyncio
async def test_private_audio_has_no_static_bypass(client):
    assert (await client.get('/storage/audio/poi_test_01_vi.mp3')).status_code == 403
    assert (await client.get('/api/v1/audio/poi_test_01_vi.mp3/stream')).status_code == 403


@pytest.mark.asyncio
async def test_logout_requires_session_proof_and_revokes_existing_bearer(client):
    response = await client.post('/api/v1/auth/login', json={"email": "tourist@test.vn", "password": "User@123456"})
    login = response.json()
    headers = {"Authorization": "Bearer " + login["access_token"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        assert (await other.post('/api/v1/auth/logout', json={"session_id": login["session_id"]})).status_code == 200
    assert (await client.get('/api/v1/auth/me', headers=headers)).status_code == 200
    assert (await client.post('/api/v1/auth/logout', headers=headers)).status_code == 200
    assert (await client.get('/api/v1/auth/me', headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_reversed_bounds_and_private_package_index(client):
    response = await client.get('/api/v1/pois/in-bounds', params={
        "min_lon": 106.72, "max_lon": 106.70, "min_lat": 10.74, "max_lat": 10.77,
    })
    assert response.status_code == 422
    assert (await client.get('/api/v1/packages')).status_code == 401
    assert (await client.get('/api/v1/packages', headers=await user(client))).status_code == 403


@pytest.mark.asyncio
async def test_device_identity_and_consent_enforced(client):
    event = {"events": [{"event_id": "review-1", "event_type": "poi_viewed", "poi_id": "poi_ben_nha_rong"}]}
    assert (await client.post('/api/v1/analytics/events/batch', json=event)).json()['accepted_count'] == 0
    boot = (await client.post('/api/v1/device/bootstrap', json={"platform": "web"})).json()
    assert (await client.post('/api/v1/analytics/consent', json={"device_id": "someone-else", "consent_granted": True})).status_code == 403
    assert (await client.post('/api/v1/analytics/consent', json={"device_id": boot['device_id'], "consent_granted": True})).status_code == 200
    assert (await client.post('/api/v1/analytics/events/batch', json=event)).json()['accepted_count'] == 1
    forged = {"events": [{"event_id": "forged-1", "event_type": "narration_started",
                         "poi_id": "poi_ben_nha_rong", "playback_id": "fake-grant"}]}
    proof = (await client.post('/api/v1/analytics/events/batch', json=forged)).json()
    assert proof["acks"][0]["reason"] == "PLAYBACK_NOT_VERIFIED"
    await client.post('/api/v1/analytics/consent', json={"device_id": boot['device_id'], "consent_granted": False})
    event['events'][0]['event_id'] = 'review-2'
    assert (await client.post('/api/v1/analytics/events/batch', json=event)).json()['accepted_count'] == 0
    assert (await client.get('/api/v1/analytics/admin/overview')).status_code == 401


@pytest.mark.asyncio
async def test_cookie_auth_rejects_cross_origin_mutation(client):
    await user(client)
    response = await client.post('/api/v1/auth/logout', headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_config_aliases_and_production_fail_fast():
    config = Settings(_env_file=None, JWT_SECRET='x' * 48, MONGODB_DB_NAME='review_db')
    # Explicit canonical env from the test runner takes precedence; aliases are declared and accepted.
    assert 'JWT_SECRET' in str(Settings.model_fields['SECRET_KEY'].validation_alias)
    config.APP_ENV = 'production'
    config.SECRET_KEY = 'x' * 48
    config.PAYMENT_MODE = 'mock'
    with pytest.raises(RuntimeError): config.validate_runtime()


@pytest.mark.asyncio
async def test_draft_not_public_and_source_change_invalidates_audio(client):
    headers = await user(client, 'admin@tourvoice.vn', 'Admin@123456')
    created = await client.post('/api/v1/pois', headers=headers, json={"name": "Review draft", "description": "Review description", "location": {"coordinates": [106.7, 10.76]}})
    assert created.status_code == 201
    poi = created.json()
    assert poi['is_active'] is False
    assert (await client.get('/api/v1/pois/' + poi['_id'])).status_code == 404
    assert (await client.get('/api/v1/pois/' + poi['_id'] + '/contents/vi/active')).status_code == 404
    updated = await client.patch('/api/v1/pois/' + poi['_id'], headers=headers, json={"description": "Updated source text", "expected_version": poi['version']})
    assert updated.status_code == 200
    assert updated.json()['audio_url'] is None
    assert updated.json()['content_version'] == 2
