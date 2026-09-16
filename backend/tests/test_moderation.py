import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_owner_submission_and_admin_review(client: AsyncClient):
    """Test full moderation cycle: owner submits -> admin approves -> notification sent."""
    # 1. Login as verified owner
    owner_login = await client.post("/api/v1/admin/auth/login", json={
        "email": "owner.verified@quan4.vn",
        "password": "Owner@123456"
    })
    owner_token = owner_login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Owner submits draft proposal
    sub_resp = await client.post("/api/v1/owner/submissions", json={
        "action": "create",
        "payload": {
            "name": "Quán Cơm Tấm Đêm Vĩnh Khánh",
            "description": "Cơm tấm sườn bì chả nướng than thơm phức.",
            "category": "food",
            "address": "123 Vĩnh Khánh, Quận 4",
            "location": {"type": "Point", "coordinates": [106.7005, 10.7602]},
        }
    }, headers=owner_headers)
    assert sub_resp.status_code == 201
    sub_data = sub_resp.json()
    assert sub_data["status"] == "pending"
    sub_id = sub_data["submission_id"]

    # 3. Login as admin
    admin_login = await client.post("/api/v1/admin/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Admin approves submission
    review_resp = await client.post(f"/api/v1/admin/moderation/submissions/{sub_id}", json={
        "decision": "approved",
        "admin_note": "Nội dung đạt chuẩn, duyệt đưa vào hệ thống."
    }, headers=admin_headers)
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"

    # 5. Owner checks in-app notifications
    notifs_resp = await client.get("/api/v1/owner/notifications", headers=owner_headers)
    assert notifs_resp.status_code == 200
    notifs = notifs_resp.json()
    assert len(notifs) >= 1
    assert any(n["type"] == "submission_result" for n in notifs)


@pytest.mark.asyncio
async def test_idor_protection_for_menu(client: AsyncClient):
    """Test that an owner cannot add menu items to someone else's POI."""
    # 1. Login as owner
    owner_login = await client.post("/api/v1/admin/auth/login", json={
        "email": "owner.verified@quan4.vn",
        "password": "Owner@123456"
    })
    owner_token = owner_login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Try adding menu to Ben Nha Rong (which has owner_id = None, not owned by this owner)
    resp = await client.post("/api/v1/pois/poi_ben_nha_rong/menu", json={
        "name": "Món ăn trái phép",
        "price": 50000
    }, headers=owner_headers)
    assert resp.status_code == 403
