import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test login with seeded superadmin credentials."""
    resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "superadmin@tourvoice.vn",
        "password": "Admin@123456"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data and len(data["access_token"]) > 20
    assert data["user"]["role"] == "super_admin"
    assert "session_id" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Test login rejection with wrong password."""
    resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "superadmin@tourvoice.vn",
        "password": "WrongPassword!999"
    })
    assert resp.status_code == 401
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_owner_registration_flow(client: AsyncClient):
    """Test new owner registration creates pending state."""
    resp = await client.post("/api/v1/admin/auth/register-owner", json={
        "email": "new.owner@quan4.vn",
        "password": "SecretOwner123!",
        "full_name": "Nguyễn Văn Chủ Mới",
        "business_name": "Quán Bún Bò Xóm Chiếu"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert data["status"] == "pending"
    assert "registration_id" in data


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    """Test refresh token rotation."""
    login_resp = await client.post("/api/v1/admin/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    session_id = login_data["session_id"]
    refresh_token = login_data["refresh_token"]

    # Refresh
    refresh_resp = await client.post("/api/v1/admin/auth/refresh", json={
        "session_id": session_id,
        "refresh_token": refresh_token
    })
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert refresh_data["success"] is True
    assert "access_token" in refresh_data
    # Should be a new rotated refresh token
    assert refresh_data["refresh_token"] != refresh_token
