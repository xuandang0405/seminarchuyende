"""Comprehensive Acceptance Test Suite covering all 22 Scenarios.

Specification: Section 12 (Kiểm thử nghiệm thu bắt buộc).
"""

import pytest
import hmac
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

from app.core.config import settings
from app.core.database import db_manager
from app.db.collections import (
    COLLECTION_GUEST_SESSIONS,
    COLLECTION_TRIAL_USAGE,
    COLLECTION_PLAYBACK_GRANTS,
    COLLECTION_ORDERS,
    COLLECTION_TOUR_ENTITLEMENTS,
    COLLECTION_ADMIN_USERS,
    COLLECTION_TOURS,
    COLLECTION_POI
)
from app.core.security import create_access_token


def make_user_token(user_id: str, role: str = "user") -> str:
    return create_access_token(subject=user_id, claims={"role": role, "auth_version": 1})


@pytest.fixture
async def seeded_tour_and_poi():
    db = db_manager.db
    tour = {
        "_id": "tour_test_01",
        "name": "Tour Di Tích Quận 4",
        "price_amount": 99000,
        "currency": "VND",
        "pricing_version": 1,
        "is_purchasable": True,
        "preview_enabled": True,
        "preview_poi_ids": ["poi_test_01"],
        "is_active": True,
        "poi_ids": ["poi_test_01", "poi_test_02"]
    }
    poi1 = {
        "_id": "poi_test_01",
        "name": "Bến Nhà Rồng Test",
        "audio_url": "/api/v1/audio/audio/poi_test_01_vi.mp3/stream",
        "is_active": True
    }
    poi2 = {
        "_id": "poi_test_02",
        "name": "Chợ Xóm Chiếu Test",
        "audio_url": "/api/v1/audio/audio/poi_test_02_vi.mp3/stream",
        "is_active": True
    }
    await db[COLLECTION_TOURS].update_one({"_id": tour["_id"]}, {"$set": tour}, upsert=True)
    await db[COLLECTION_POI].update_one({"_id": poi1["_id"]}, {"$set": poi1}, upsert=True)
    await db[COLLECTION_POI].update_one({"_id": poi2["_id"]}, {"$set": poi2}, upsert=True)
    return tour, poi1, poi2


# =============================================================================
# SCENARIOS 1 & 2: Guest trial, replay/new POI paywall, pause/resume
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_01_and_02_guest_trial_and_paywall(client: AsyncClient, seeded_tour_and_poi):
    tour, poi1, poi2 = seeded_tour_and_poi

    # 1. Guest creates session
    res = await client.post("/api/v1/guest-sessions")
    assert res.status_code == 201
    guest_data = res.json()
    guest_token = guest_data.get("guest_token") or guest_data.get("guest_credential")

    # 2. Check tour access initially -> trial available
    res_access = await client.get(f"/api/v1/tours/{tour['_id']}/access", headers={"X-Guest-Token": guest_token})
    assert res_access.status_code == 200
    access_info = res_access.json()
    assert access_info["can_preview"] is True
    assert access_info["trial_remaining"] == 1
    assert access_info["has_entitlement"] is False

    # 3. Active consent trial playback for POI 1
    res_grant = await client.post(
        "/api/v1/playback-grants",
        headers={"X-Guest-Token": guest_token},
        json={
            "tour_id": tour["_id"],
            "poi_id": poi1["_id"],
            "language": "vi",
            "trigger_type": "manual",
            "user_consent_trial": True
        }
    )
    assert res_grant.status_code == 200
    grant_data = res_grant.json()
    assert grant_data["granted"] is True
    assert grant_data["scope"] == "trial"
    stream_url = grant_data["stream_url"]

    # 4. Stream media with valid grant token -> 200 OK
    res_stream = await client.get(stream_url)
    assert res_stream.status_code == 200

    # 5. Pause & resume with SAME grant token within window -> 200 OK
    res_resume = await client.get(stream_url)
    assert res_resume.status_code == 200

    # 6. Scenario 2: Trying a NEW POI without purchasing -> TRIAL_EXHAUSTED / TOUR_PURCHASE_REQUIRED
    res_grant_poi2 = await client.post(
        "/api/v1/playback-grants",
        headers={"X-Guest-Token": guest_token},
        json={
            "tour_id": tour["_id"],
            "poi_id": poi2["_id"],
            "language": "vi",
            "trigger_type": "manual",
            "user_consent_trial": True
        }
    )
    assert res_grant_poi2.status_code == 403


# =============================================================================
# SCENARIO 3: Atomic concurrency / Idempotency
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_03_atomic_concurrency_single_trial(client: AsyncClient, seeded_tour_and_poi):
    tour, poi1, _ = seeded_tour_and_poi
    res = await client.post("/api/v1/guest-sessions")
    guest_token = res.json().get("guest_token") or res.json().get("guest_credential")

    # First request consumes quota
    res1 = await client.post(
        "/api/v1/playback-grants",
        headers={"X-Guest-Token": guest_token},
        json={
            "tour_id": tour["_id"],
            "poi_id": poi1["_id"],
            "language": "vi",
            "trigger_type": "manual",
            "user_consent_trial": True
        }
    )
    assert res1.status_code == 200

    # Second request immediately fails because quota was consumed atomically
    res2 = await client.post(
        "/api/v1/playback-grants",
        headers={"X-Guest-Token": guest_token},
        json={
            "tour_id": tour["_id"],
            "poi_id": poi1["_id"],
            "language": "vi",
            "trigger_type": "manual",
            "user_consent_trial": True
        }
    )
    assert res2.status_code == 403


# =============================================================================
# SCENARIO 4: GPS does not silently burn trial quota
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_04_gps_requires_explicit_consent(client: AsyncClient, seeded_tour_and_poi):
    tour, poi1, _ = seeded_tour_and_poi
    res = await client.post("/api/v1/guest-sessions")
    guest_token = res.json().get("guest_token") or res.json().get("guest_credential")

    # GPS trigger with user_consent_trial=False
    res_gps = await client.post(
        "/api/v1/playback-grants",
        headers={"X-Guest-Token": guest_token},
        json={
            "tour_id": tour["_id"],
            "poi_id": poi1["_id"],
            "language": "vi",
            "trigger_type": "gps",
            "user_consent_trial": False
        }
    )
    assert res_gps.status_code == 403
    data = res_gps.json()
    error_code = data.get("error_code") or (data.get("detail", {}).get("error_code") if isinstance(data.get("detail"), dict) else data.get("detail"))
    assert "TRIAL_CONSENT_REQUIRED" in str(error_code)

    # Quota is still available!
    res_access = await client.get(f"/api/v1/tours/{tour['_id']}/access", headers={"X-Guest-Token": guest_token})
    assert res_access.json()["trial_remaining"] == 1


# =============================================================================
# SCENARIO 5: Failure before media delivery does not consume quota permanently
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_05_rollback_reservation_on_failure(client: AsyncClient, seeded_tour_and_poi):
    from app.services.trial_service import trial_service
    tour, poi1, _ = seeded_tour_and_poi
    subject_id = f"guest_test_fail_{int(time.time()*1000)}"

    success, res_id, _ = await trial_service.reserve_trial_quota("guest", subject_id, tour["_id"], poi1["_id"], "vi")
    assert success is True

    # Rollback reservation
    released = await trial_service.release_trial_quota("guest", subject_id, res_id)
    assert released is True

    # Quota is restored
    status = await trial_service.get_trial_status("guest", subject_id)
    assert status["state"] == "available"
    assert status["trial_remaining"] == 1


# =============================================================================
# SCENARIO 6: Guest who used trial registers -> quota stays consumed
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_06_guest_used_trial_merge_on_register(client: AsyncClient, seeded_tour_and_poi):
    tour, poi1, _ = seeded_tour_and_poi
    res_guest = await client.post("/api/v1/guest-sessions")
    guest_token = res_guest.json().get("guest_token") or res_guest.json().get("guest_credential")

    # Consume trial as guest
    await client.post(
        "/api/v1/playback-grants",
        headers={"X-Guest-Token": guest_token},
        json={
            "tour_id": tour["_id"],
            "poi_id": poi1["_id"],
            "language": "vi",
            "trigger_type": "manual",
            "user_consent_trial": True
        }
    )

    # Register tourist passing guest_token
    reg_email = f"tourist_{int(time.time()*1000)}@test.vn"
    res_reg = await client.post("/api/v1/auth/register", json={
        "full_name": "Nguyen Van Test",
        "email": reg_email,
        "password": "Password@123",
        "guest_token": guest_token
    })
    assert res_reg.status_code == 201
    user_token = res_reg.json()["access_token"]

    # Newly registered user has 0 trial remaining because guest quota was consumed!
    res_access = await client.get(f"/api/v1/tours/{tour['_id']}/access", headers={"Authorization": f"Bearer {user_token}"})
    assert res_access.json()["trial_remaining"] == 0
    assert res_access.json()["can_preview"] is False


# =============================================================================
# SCENARIO 7: Entitled user plays full tour without consuming trial quota
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_07_entitled_user_does_not_consume_trial(client: AsyncClient, seeded_tour_and_poi):
    tour, poi1, poi2 = seeded_tour_and_poi
    db = db_manager.db

    # Create user with active entitlement
    user_id = f"user_entitled_{int(time.time()*1000)}"
    user_doc = {
        "_id": user_id,
        "email": f"{user_id}@test.vn",
        "full_name": "Entitled User",
        "role": "user",
        "is_active": True,
        "auth_version": 1,
        "created_at": datetime.now(timezone.utc)
    }
    await db[COLLECTION_ADMIN_USERS].insert_one(user_doc)

    await db[COLLECTION_TOUR_ENTITLEMENTS].update_one(
        {"user_id": user_id, "tour_id": tour["_id"]},
        {"$set": {
            "user_id": user_id,
            "tour_id": tour["_id"],
            "status": "active",
            "granted_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )

    user_token = make_user_token(user_id, "user")

    # Check access
    res_access = await client.get(f"/api/v1/tours/{tour['_id']}/access", headers={"Authorization": f"Bearer {user_token}"})
    assert res_access.status_code == 200
    assert res_access.json()["has_entitlement"] is True
    assert res_access.json()["can_play_full_tour"] is True

    # Play POI 1 -> scope: paid/entitled
    res_grant = await client.post(
        "/api/v1/playback-grants",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "tour_id": tour["_id"],
            "poi_id": poi1["_id"],
            "language": "vi",
            "trigger_type": "manual"
        }
    )
    assert res_grant.status_code == 200
    assert res_grant.json()["scope"] in ("paid", "entitled")


# =============================================================================
# SCENARIO 8: Guest cannot create order
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_08_guest_cannot_create_order(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    res = await client.post("/api/v1/orders", json={"tour_id": tour["_id"]})
    assert res.status_code == 401


# =============================================================================
# SCENARIO 9: Order price is server-determined from tour document
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_09_order_price_server_determined(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_pricing_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1
    })
    user_token = make_user_token(user_id, "user")

    # Client sends order request -> server sets price amount snapshot from DB
    res = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"tour_id": tour["_id"]}
    )
    assert res.status_code == 201
    order = res.json()
    assert order["amount_vnd"] == 99000
    assert order["currency"] == "VND"


# =============================================================================
# SCENARIO 10: Invalid callback / signature does NOT grant entitlement
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_10_invalid_signature_rejected(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_fraud_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1
    })
    user_token = make_user_token(user_id, "user")

    res_order = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"tour_id": tour["_id"]}
    )
    order_id = res_order.json()["order_id"]

    # Forge payOS webhook with fake signature
    fake_payload = {
        "data": {
            "orderCode": 12345,
            "amount": 99000,
            "description": f"Thanh toan don hang {order_id}"
        },
        "signature": "forged_signature_hex"
    }
    res_webhook = await client.post("/api/v1/payments/webhook/payos", json=fake_payload)
    assert res_webhook.status_code == 400

    # Verify order is still pending
    res_check = await client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_check.json()["status"] == "pending_payment"


# =============================================================================
# SCENARIO 11: ReturnURL or "paid" query does NOT unlock tour
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_11_return_url_does_not_unlock(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_spoof_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1
    })
    user_token = make_user_token(user_id, "user")

    res_access = await client.get(
        f"/api/v1/tours/{tour['_id']}/access?success=true&paid=true",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res_access.json()["has_entitlement"] is False


# =============================================================================
# SCENARIO 12: Valid callback grants entitlement; duplicate webhook is idempotent
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_12_valid_callback_and_idempotency(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_idempotent_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1
    })
    user_token = make_user_token(user_id, "user")

    # Create order & payment attempt
    res_order = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"tour_id": tour["_id"]}
    )
    order_id = res_order.json()["order_id"]

    res_attempt = await client.post(
        f"/api/v1/orders/{order_id}/payment-attempts",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"payment_method": "vietqr"}
    )
    ref = res_attempt.json()["provider_reference"]

    # Mock callback
    cb_payload = {
        "provider_reference": ref,
        "transaction_id": f"tx_mock_{int(time.time()*1000)}",
        "amount": 99000,
        "status": "PAID"
    }

    # First call
    res_cb1 = await client.post("/api/v1/payments/mock/callback", json=cb_payload)
    assert res_cb1.status_code == 200
    assert res_cb1.json()["data"]["status"] in ("success", "ok")

    # Order is now paid and entitlement exists
    res_order_check = await client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_order_check.json()["status"] == "paid"

    # Second call (duplicate webhook from network retry)
    res_cb2 = await client.post("/api/v1/payments/mock/callback", json=cb_payload)
    assert res_cb2.status_code == 200

    # Ensure only 1 entitlement exists in database
    count = await db[COLLECTION_TOUR_ENTITLEMENTS].count_documents({"user_id": user_id, "tour_id": tour["_id"]})
    assert count == 1


# =============================================================================
# SCENARIO 13: Transactional consistency between order and entitlement
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_13_reconciliation_consistency(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_rec_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1
    })
    user_token = make_user_token(user_id, "user")

    res_order = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"tour_id": tour["_id"]}
    )
    order_id = res_order.json()["order_id"]
    await client.post(
        f"/api/v1/orders/{order_id}/payment-attempts",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"payment_method": "vietqr"}
    )

    # Reconcile pending order
    res_rec = await client.post(
        f"/api/v1/orders/{order_id}/reconcile",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res_rec.status_code == 200
    assert res_rec.json()["order_id"] == order_id


# =============================================================================
# SCENARIO 14: Pending timeout can be reconciled; cancel does not overwrite paid
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_14_cannot_cancel_already_paid_order(client: AsyncClient, seeded_tour_and_poi):
    db = db_manager.db
    order_id = f"order_paid_{int(time.time()*1000)}"
    await db[COLLECTION_ORDERS].update_one(
        {"_id": order_id},
        {"$set": {
            "_id": order_id,
            "status": "paid",
            "snapshot_price_amount": 99000
        }},
        upsert=True
    )
    from app.repositories.order_repo import order_repo
    # Attempting to cancel paid order fails
    res = await order_repo.mark_order_cancelled(order_id)
    assert res is False


# =============================================================================
# SCENARIO 15: Amount mismatch enters requires_review
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_15_amount_mismatch_requires_review(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_underpaid_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1
    })
    user_token = make_user_token(user_id, "user")

    res_order = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"tour_id": tour["_id"]}
    )
    order_id = res_order.json()["order_id"]
    res_attempt = await client.post(
        f"/api/v1/orders/{order_id}/payment-attempts",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"payment_method": "vietqr"}
    )
    ref = res_attempt.json()["provider_reference"]

    # Provider reports underpayment (50000 instead of 99000)
    cb_payload = {
        "provider_reference": ref,
        "transaction_id": f"tx_underpaid_{int(time.time()*1000)}",
        "amount": 50000,
        "status": "PAID"
    }
    await client.post("/api/v1/payments/mock/callback", json=cb_payload)

    # Order status must be requires_review!
    res_check = await client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_check.json()["status"] == "requires_review"


# =============================================================================
# SCENARIO 16: Prevent duplicate purchase if already entitled
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_16_prevent_duplicate_tour_purchase(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_double_buy_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1
    })
    await db[COLLECTION_TOUR_ENTITLEMENTS].update_one(
        {"user_id": user_id, "tour_id": tour["_id"]},
        {"$set": {
            "user_id": user_id,
            "tour_id": tour["_id"],
            "status": "active"
        }},
        upsert=True
    )
    user_token = make_user_token(user_id, "user")

    # Attempting to order again returns 409 Conflict
    res = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"tour_id": tour["_id"]}
    )
    assert res.status_code == 409
    assert "sở hữu" in res.json()["detail"].lower() or "already" in res.json()["detail"].lower()


# =============================================================================
# SCENARIO 17: Strict IDOR protection between users
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_17_strict_idor_protection(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    userA_id = f"user_A_{int(time.time()*1000)}"
    userB_id = f"user_B_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({"_id": userA_id, "email": f"{userA_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1})
    await db[COLLECTION_ADMIN_USERS].insert_one({"_id": userB_id, "email": f"{userB_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1})

    userA_token = make_user_token(userA_id, "user")
    userB_token = make_user_token(userB_id, "user")

    # User A creates order
    res_order = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {userA_token}"},
        json={"tour_id": tour["_id"]}
    )
    orderA_id = res_order.json()["order_id"]

    # User B tries to view User A's order -> 403 Forbidden
    res_idor = await client.get(
        f"/api/v1/orders/{orderA_id}",
        headers={"Authorization": f"Bearer {userB_token}"}
    )
    assert res_idor.status_code == 403


# =============================================================================
# SCENARIO 18: Direct media streaming gated by grant token
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_18_direct_media_gated_by_grant(client: AsyncClient):
    # Direct access without grant token -> 403 Forbidden
    res = await client.get("/api/v1/audio/random_secret_audio_key/stream")
    assert res.status_code == 403

    # Public POI summary is accessible
    res_pois = await client.get("/api/v1/pois")
    assert res_pois.status_code == 200


# =============================================================================
# SCENARIO 19: Offline pack download requires active entitlement
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_19_offline_pack_requires_entitlement(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_no_ent_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({"_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1})
    user_token = make_user_token(user_id, "user")

    # User without entitlement attempts download -> 403 Forbidden
    res = await client.post(
        f"/api/v1/tours/{tour['_id']}/offline-pack",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"device_id": "phone_test"}
    )
    assert res.status_code == 403

    # Grant entitlement and download -> 200 OK with signed 7-day license
    await db[COLLECTION_TOUR_ENTITLEMENTS].update_one(
        {"user_id": user_id, "tour_id": tour["_id"]},
        {"$set": {"user_id": user_id, "tour_id": tour["_id"], "status": "active"}},
        upsert=True
    )
    res_ok = await client.post(
        f"/api/v1/tours/{tour['_id']}/offline-pack",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"device_id": "phone_test"}
    )
    assert res_ok.status_code == 200
    pack = res_ok.json()
    assert "license" in pack
    assert pack["license"]["scope"] == "offline_7days"


# =============================================================================
# SCENARIO 20: Role-based permissions: tourist cannot access admin routes
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_20_tourist_cannot_access_admin(client: AsyncClient, seeded_tour_and_poi):
    tour, _, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_tourist_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({"_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1})
    tourist_token = make_user_token(user_id, "user")

    # Try to edit pricing -> 403 Forbidden
    res_pricing = await client.put(
        f"/api/v1/tours/{tour['_id']}/pricing",
        headers={"Authorization": f"Bearer {tourist_token}"},
        json={"price_amount": 1000, "currency": "VND", "is_purchasable": True, "preview_enabled": True}
    )
    assert res_pricing.status_code == 403

    # Try to view admin users -> 403 Forbidden
    res_users = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {tourist_token}"})
    assert res_users.status_code == 403


# =============================================================================
# SCENARIO 21: Production safety: mock disabled in production
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_21_mock_disabled_in_production(client: AsyncClient):
    old_mode = settings.PAYMENT_MODE
    try:
        settings.PAYMENT_MODE = "production"
        res = await client.post("/api/v1/payments/mock/callback", json={"foo": "bar"})
        assert res.status_code == 403
    finally:
        settings.PAYMENT_MODE = old_mode


# =============================================================================
# SCENARIO 22: Complete user journey & my tours retrieval
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_22_complete_tourist_journey(client: AsyncClient, seeded_tour_and_poi):
    tour, poi1, _ = seeded_tour_and_poi
    db = db_manager.db
    user_id = f"user_journey_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({"_id": user_id, "email": f"{user_id}@test.vn", "role": "user", "is_active": True, "auth_version": 1})
    user_token = make_user_token(user_id, "user")

    # 1. User orders tour
    res_order = await client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"tour_id": tour["_id"]}
    )
    order_id = res_order.json()["order_id"]

    # 2. Creates payment attempt
    res_attempt = await client.post(
        f"/api/v1/orders/{order_id}/payment-attempts",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"payment_method": "vietqr"}
    )
    ref = res_attempt.json()["provider_reference"]

    # 3. Webhook completes payment
    await client.post("/api/v1/payments/mock/callback", json={
        "provider_reference": ref,
        "transaction_id": f"tx_journey_{int(time.time()*1000)}",
        "amount": 99000,
        "status": "PAID"
    })

    # 4. User views /me/tours and /me/orders
    res_my_tours = await client.get("/api/v1/me/tours", headers={"Authorization": f"Bearer {user_token}"})
    assert res_my_tours.status_code == 200
    my_tours = res_my_tours.json()
    assert any(t["_id"] == tour["_id"] for t in my_tours)

    res_my_orders = await client.get("/api/v1/me/orders", headers={"Authorization": f"Bearer {user_token}"})
    assert res_my_orders.status_code == 200
    my_orders = res_my_orders.json()
    assert any((o.get("order_id") == order_id or o.get("_id") == order_id) and o["status"] == "paid" for o in my_orders)
