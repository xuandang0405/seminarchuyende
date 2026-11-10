import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import db_manager
from app.db.collections import COLLECTION_TOURS
from app.repositories.order_repo import order_repo


@pytest.mark.asyncio
async def test_quick_simulation_uses_server_price_and_grants_ticket_once(client: AsyncClient, monkeypatch):
    path = "/api/v1/payments/simulate-checkout"
    tour_id = "tour_quick_simulation"
    payload = {"item_id": tour_id, "unit_price": 1}
    headers = {"Idempotency-Key": "quick-test"}
    assert (await client.get("/api/v1/payments/config")).json() == {"simulation_enabled": True}
    assert (await client.post(path, json=payload, headers=headers)).status_code == 401
    login = await client.post("/api/v1/auth/login", json={"email": "tourist@test.vn", "password": "User@123456"})
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    await db_manager.db[COLLECTION_TOURS].insert_one({
        "_id": tour_id, "name": "Tour mô phỏng", "price_amount": 129000,
        "is_active": True, "is_purchasable": True, "poi_ids": [],
    })
    response = await client.post(path, json=payload, headers=headers)
    assert response.status_code == 200, response.text
    paid = response.json()["data"]
    assert paid["amount_vnd"] == 129000 and paid["status"] == "paid" and paid["simulated"]
    assert paid["customer_phone"] is None
    repeated = await client.post(path, json=payload, headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["data"]["ticket_code"] == paid["ticket_code"]
    assert repeated.json()["data"]["order_id"] == paid["order_id"]
    assert (await client.get(f"/api/v1/tours/{tour_id}/access")).json()["has_entitlement"] is True
    monkeypatch.setattr(settings, "PAYMENT_MODE", "live")
    assert (await client.get("/api/v1/payments/config")).json() == {"simulation_enabled": False}
    assert (await client.post(path, json=payload, headers=headers)).status_code == 403

@pytest.mark.asyncio
async def test_payment_flow_order_and_simulate_success(client: AsyncClient):
    login = await client.post("/api/v1/auth/login", json={"email": "admin@tourvoice.vn", "password": "Admin@123456"})
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    await db_manager.db[COLLECTION_TOURS].insert_one({"_id": "tour_di_tich_lich_su_quan_4", "name": "Tour Test", "price_amount": 150000, "is_active": True, "is_purchasable": True, "poi_ids": []})
    # 1. Create order
    payload = {
        "order_type": "tour_ticket",
        "item_id": "tour_di_tich_lich_su_quan_4",
        "item_title": "Tour Di Tích Bến Nhà Rồng",
        "customer_name": "Trần Du Khách",
        "customer_phone": "0911222333",
        "customer_email": "khach.test@gmail.com",
        "quantity": 1,
        "unit_price": 150000,
        "payment_method": "vietqr"
    }
    resp = await client.post("/api/v1/payments/orders", json=payload)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["status"] == "success"
    order = res_data["data"]
    order_id = order["order_id"]
    assert order["total_amount"] == 150000
    assert order["status"] == "pending_payment"
    assert order["mock_mode"] is True
    assert order["vietqr_url"] is None and order["bank_info"] is None

    # 2. Get order details
    resp_get = await client.get(f"/api/v1/payments/orders/{order_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["order_id"] == order_id

    # 3. Simulate payment success (Webhook/IPN)
    resp_sim = await client.post(f"/api/v1/payments/orders/{order_id}/simulate-success")
    assert resp_sim.status_code == 200
    paid_order = resp_sim.json()["data"]
    assert paid_order["status"] == "paid"
    assert paid_order["ticket_code"].startswith("TICKET-Q4-")

    # 4. Check revenue summary
    resp_rev = await client.get("/api/v1/payments/revenue-summary")
    assert resp_rev.status_code == 200
    rev_data = resp_rev.json()
    assert rev_data["total_revenue_vnd"] >= 300000


@pytest.mark.asyncio
async def test_expired_mock_order_cannot_be_settled(client: AsyncClient):
    login = await client.post("/api/v1/auth/login", json={"email": "tourist@test.vn", "password": "User@123456"})
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    tour_id = "tour_expired_mock"
    await db_manager.db[COLLECTION_TOURS].insert_one({
        "_id": tour_id, "name": "Tour đơn hết hạn", "price_amount": 59000,
        "is_active": True, "is_purchasable": True, "poi_ids": [],
    })
    created = await client.post("/api/v1/payments/orders", json={
        "item_id": tour_id, "customer_name": "Test", "customer_phone": "0900000000",
    })
    assert created.status_code == 201
    order_id = created.json()["data"]["order_id"]
    await order_repo.collection.update_one({"_id": order_id}, {
        "$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)},
    })
    expired = await client.post(f"/api/v1/payments/orders/{order_id}/simulate-success")
    assert expired.status_code == 409
    assert expired.json()["detail"]["error_code"] == "CHECKOUT_EXPIRED"
    assert (await client.get(f"/api/v1/tours/{tour_id}/access")).json()["has_entitlement"] is False
