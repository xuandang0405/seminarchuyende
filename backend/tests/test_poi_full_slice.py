import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_public_pois(client: AsyncClient):
    """Test public listing of POIs with resolved localization."""
    resp = await client.get("/api/v1/pois?lang=vi")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 10
    # Check sample POI structure
    first = data["items"][0]
    assert "id" in first
    assert "name" in first
    assert "location" in first
    assert "trigger_radius" in first


@pytest.mark.asyncio
async def test_get_poi_detail(client: AsyncClient):
    """Test public POI detail with language fallback."""
    resp = await client.get("/api/v1/pois/poi_ben_nha_rong?lang=en")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "poi_ben_nha_rong"
    assert "Dragon Wharf" in data["name"]
    assert data["resolved_lang"] == "en"


@pytest.mark.asyncio
async def test_poi_creation_and_concurrency_control(client: AsyncClient):
    """Test POI creation, update with correct version, and conflict on wrong version."""
    # 1. Login as admin
    login_resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create POI
    create_resp = await client.post("/api/v1/pois", json={
        "name": "Bến Vân Đồn Điểm Hẹn",
        "description": "Tuyến đường ven kênh Bến Nghé thoáng mát.",
        "category": "sightseeing",
        "address": "Bến Vân Đồn, Quận 4",
        "location": {"type": "Point", "coordinates": [106.701, 10.765]},
        "trigger_radius": 30.0,
        "audio_priority": 3
    }, headers=headers)
    assert create_resp.status_code == 201
    created_poi = create_resp.json()
    poi_id = created_poi["_id"]
    assert created_poi["version"] == 1

    # 3. Update with correct expected_version (1) -> should succeed
    update_resp = await client.patch(f"/api/v1/pois/{poi_id}", json={
        "name": "Bến Vân Đồn Điểm Hẹn (Đã cập nhật)",
        "expected_version": 1
    }, headers=headers)
    assert update_resp.status_code == 200
    updated_poi = update_resp.json()
    assert updated_poi["version"] == 2

    # 4. Update with stale version (1 instead of 2) -> must return 409 Conflict
    conflict_resp = await client.patch(f"/api/v1/pois/{poi_id}", json={
        "name": "Bến Vân Đồn Xung Đột",
        "expected_version": 1
    }, headers=headers)
    assert conflict_resp.status_code == 409


@pytest.mark.asyncio
async def test_publication_readiness_gate(client: AsyncClient):
    """Test that activating a POI without English translation and audio fails the readiness gate."""
    login_resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create draft POI without English translation
    create_resp = await client.post("/api/v1/pois", json={
        "name": "Quán Trà Sữa Tôn Đản",
        "description": "Trà sữa nhà làm ngon bổ rẻ.",
        "location": {"type": "Point", "coordinates": [106.702, 10.761]},
    }, headers=headers)
    poi_id = create_resp.json()["_id"]

    # Try activating POI
    toggle_resp = await client.post(f"/api/v1/pois/{poi_id}/toggle-active?active=true", headers=headers)
    assert toggle_resp.status_code == 200
    gate_data = toggle_resp.json()
    assert gate_data["is_active"] is False
    assert gate_data["activation_requested"] is True
    assert gate_data["gate_passed"] is False
    assert len(gate_data["reasons"]) > 0


@pytest.mark.asyncio
async def test_poi_deletion_cascades_qr(client: AsyncClient):
    """Test that deleting a POI cascade deletes all associated QR codes."""
    # 1. Login as admin
    login_resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create test POI
    create_resp = await client.post("/api/v1/pois", json={
        "name": "Địa Điểm Test Cascade Xóa",
        "description": "Địa điểm kiểm thử xóa QR theo POI.",
        "location": {"type": "Point", "coordinates": [106.702, 10.761]},
    }, headers=headers)
    assert create_resp.status_code == 201
    poi_id = create_resp.json()["_id"]

    # 3. Create QR code for this POI
    qr_code = f"QR-CASCADE-{poi_id[-6:]}"
    qr_create_resp = await client.post("/api/v1/qr", json={
        "poi_id": poi_id,
        "code": qr_code,
        "location_description": "Cổng kiểm thử"
    }, headers=headers)
    assert qr_create_resp.status_code == 201

    # 4. Verify QR is resolvable
    resolve_resp = await client.get(f"/api/v1/qr/{qr_code}")
    assert resolve_resp.status_code == 200

    # 5. Delete the POI
    delete_resp = await client.delete(f"/api/v1/pois/{poi_id}", headers=headers)
    assert delete_resp.status_code == 204

    # 6. Verify QR is no longer resolvable (404)
    resolve_after = await client.get(f"/api/v1/qr/{qr_code}")
    assert resolve_after.status_code == 404

    # 7. Verify QR does not appear in admin list
    qr_list_resp = await client.get("/api/v1/qr", headers=headers)
    assert qr_list_resp.status_code == 200
    all_codes = [q["code"] for q in qr_list_resp.json()]
    assert qr_code not in all_codes
