import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.security import create_access_token


def make_admin_token(user_id: str = "superadmin_id") -> str:
    return create_access_token(
        subject=user_id,
        claims={"role": "superadmin", "email": "admin@tourvoice.vn", "auth_version": 1}
    )


@pytest.mark.asyncio
async def test_audio_upload_extension_validation(client: AsyncClient):
    """Ensure upload_audio_file rejects unsafe or invalid file extensions."""
    # Login as seeded superadmin
    login_resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "superadmin@tourvoice.vn",
        "password": "Admin@123456"
    })
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Try uploading an HTML file (malicious XSS payload)
    files = {"file": ("exploit.html", b"<html><script>alert(1)</script></html>", "text/html")}
    resp = await client.post("/api/v1/audio/upload/poi_test_01?lang=vi", files=files, headers=headers)
    assert resp.status_code == 400
    assert "không được hỗ trợ" in resp.json()["detail"]

    # 2. Try uploading an empty file
    files_empty = {"file": ("empty.mp3", b"", "audio/mpeg")}
    resp_empty = await client.post("/api/v1/audio/upload/poi_test_01?lang=vi", files=files_empty, headers=headers)
    assert resp_empty.status_code == 400
    assert "rỗng" in resp_empty.json()["detail"]


@pytest.mark.asyncio
async def test_my_orders_phone_number_masked(client: AsyncClient):
    """Ensure get_my_orders masks customer phone numbers for privacy."""
    # Create order with known phone
    payload = {
        "order_type": "tour_ticket",
        "item_id": "tour_di_tich_lich_su_quan_4",
        "item_title": "Tour Test Masking",
        "customer_name": "Nguyen Van A",
        "customer_phone": "0909123456",
        "customer_email": "masking_test@gmail.com",
        "quantity": 1,
        "unit_price": 50000,
        "payment_method": "vietqr"
    }
    resp_create = await client.post("/api/v1/payments/orders", json=payload)
    assert resp_create.status_code == 201

    # Fetch via my-orders
    resp_my = await client.get("/api/v1/payments/my-orders?email=masking_test@gmail.com")
    assert resp_my.status_code == 200
    orders = resp_my.json()
    assert len(orders) >= 1
    target = [o for o in orders if o.get("customer_email") == "masking_test@gmail.com"][0]
    # Phone must be masked like 090****456, not raw 0909123456
    assert "****" in target["customer_phone"]
    assert target["customer_phone"] != "0909123456"
