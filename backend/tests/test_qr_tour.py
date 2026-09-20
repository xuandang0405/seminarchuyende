import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tour_qr_lifecycle(client: AsyncClient):
    """Ensure Tour QR code can be generated and resolved with tour details."""
    # 1. Login as admin
    login_resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "superadmin@tourvoice.vn",
        "password": "Admin@123456"
    })
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get or create a Tour
    tours_resp = await client.get("/api/v1/tours")
    assert tours_resp.status_code == 200
    tours = tours_resp.json()
    if tours:
        tour_id = tours[0].get("id") or tours[0].get("_id")
    else:
        create_tour_resp = await client.post("/api/v1/tours", json={
            "name": "Tour Lịch Sử Quận 4",
            "description": "Tham quan di tích bến Nhà Rồng",
            "poi_ids": []
        }, headers=headers)
        assert create_tour_resp.status_code == 201
        tour_id = create_tour_resp.json().get("id") or create_tour_resp.json().get("_id")

    # 3. Create a QR code for this Tour
    qr_payload = {
        "target_type": "tour",
        "tour_id": tour_id,
        "code": "QR_TEST_TOUR_01",
        "location_description": "Cổng vào Bến Nhà Rồng"
    }
    create_resp = await client.post("/api/v1/qr", json=qr_payload, headers=headers)
    assert create_resp.status_code == 201, f"Failed: {create_resp.text}"
    created_data = create_resp.json()
    assert created_data["target_type"] == "tour"
    assert created_data["tour_id"] == tour_id
    qr_code = created_data["code"]

    # 4. Resolve the QR code (simulating scanning by tourist)
    resolve_resp = await client.get(f"/api/v1/qr/{qr_code}")
    assert resolve_resp.status_code == 200
    resolved_data = resolve_resp.json()
    assert resolved_data["target_type"] == "tour"
    assert resolved_data["tour_id"] == tour_id
    assert "tour" in resolved_data or "smart_link" in resolved_data
