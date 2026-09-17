import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_payment_flow_order_and_simulate_success(client: AsyncClient):
    # 1. Create order
    payload = {
        "order_type": "tour_ticket",
        "item_id": "tour_di_tich_lich_su_quan_4",
        "item_title": "Tour Di Tích Bến Nhà Rồng",
        "customer_name": "Trần Du Khách",
        "customer_phone": "0911222333",
        "customer_email": "khach.test@gmail.com",
        "quantity": 2,
        "unit_price": 150000,
        "payment_method": "vietqr"
    }
    resp = await client.post("/api/v1/payments/orders", json=payload)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["status"] == "success"
    order = res_data["data"]
    order_id = order["order_id"]
    assert order["total_amount"] == 300000
    assert order["status"] == "pending"
    assert "vietqr.io" in order["vietqr_url"]

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
