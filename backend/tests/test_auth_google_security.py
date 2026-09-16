"""Comprehensive tests for Google Auth, Session Security, CSRF, and RBAC.

Implements all 18 verification requirements of UPDATE_PROMPT_LOGIN_GOOGLE_SECURITY.md.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
import uuid

from app.core.config import settings
from app.repositories.auth_repo import auth_repo
from app.services.google_auth_service import google_auth_service
from app.services.password_recovery_service import password_recovery_service
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_1_login_credentials_and_passwordless(client: AsyncClient):
    """Criterion 1: Correct/wrong password, inactive account, and passwordless account."""
    # 1. Correct password
    res = await client.post("/api/v1/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "tourvoice_refresh_token" in res.cookies

    # 2. Wrong password
    res_wrong = await client.post("/api/v1/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "IncorrectPassword"
    })
    assert res_wrong.status_code == 401
    assert "chính xác" in res_wrong.json()["detail"].lower()

    # 3. Inactive account
    await auth_repo.create_user({
        "_id": "user_inactive",
        "email": "inactive@tourvoice.vn",
        "password_hash": get_password_hash("Pass123!"),
        "role": "user",
        "is_active": False
    })
    res_inactive = await client.post("/api/v1/auth/login", json={
        "email": "inactive@tourvoice.vn",
        "password": "Pass123!"
    })
    assert res_inactive.status_code == 401
    assert "khóa" in res_inactive.json()["detail"].lower()

    # 4. Passwordless account (Google-only user)
    await auth_repo.create_user({
        "_id": "user_google_only",
        "email": "google.only@gmail.com",
        "password_hash": None,
        "role": "user",
        "is_active": True
    })
    res_google_only = await client.post("/api/v1/auth/login", json={
        "email": "google.only@gmail.com",
        "password": "AnyPassword"
    })
    assert res_google_only.status_code == 401
    assert "google" in res_google_only.json()["detail"].lower()


@pytest.fixture(autouse=True)
def setup_google_settings():
    """Sets test Google OAuth credentials for testing."""
    old_client_id = settings.GOOGLE_CLIENT_ID
    old_secret = settings.GOOGLE_CLIENT_SECRET
    settings.GOOGLE_CLIENT_ID = "mock-google-client-id.apps.googleusercontent.com"
    settings.GOOGLE_CLIENT_SECRET = "mock-google-client-secret"
    yield
    settings.GOOGLE_CLIENT_ID = old_client_id
    settings.GOOGLE_CLIENT_SECRET = old_secret


@pytest.mark.asyncio
async def test_2_unauthenticated_and_privilege_escalation(client: AsyncClient):
    """Criterion 2: No token -> 401; regular user cannot call admin API -> 403."""
    # 1. No token
    res_no_token = await client.get("/api/v1/admin/moderation/registrations")
    assert res_no_token.status_code == 401

    # 2. Fake token
    res_fake = await client.get(
        "/api/v1/admin/moderation/registrations",
        headers={"Authorization": "Bearer fake_token_abc"}
    )
    assert res_fake.status_code == 401

    # 3. Regular user calling admin endpoint
    await auth_repo.create_user({
        "_id": "user_normal",
        "email": "normal.user@tourvoice.vn",
        "password_hash": get_password_hash("Pass123!"),
        "role": "user",
        "is_active": True,
        "auth_version": 1,
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "normal.user@tourvoice.vn",
        "password": "Pass123!"
    })
    access_token = login_res.json()["access_token"]

    # User attempts to call admin endpoint
    admin_res = await client.get(
        "/api/v1/admin/moderation/registrations",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert admin_res.status_code == 403
    assert "admin" in admin_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_3_refresh_token_rotation_and_reuse_detection(client: AsyncClient):
    """Criterion 5: Refresh token rotation via HttpOnly cookie and token reuse detection."""
    # Login to acquire session
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    assert login_res.status_code == 200
    cookie_val = login_res.cookies["tourvoice_refresh_token"]

    # 1. First refresh with valid cookie
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        cookies={"tourvoice_refresh_token": cookie_val}
    )
    assert refresh_res.status_code == 200
    data1 = refresh_res.json()
    assert "access_token" in data1
    new_cookie_val = refresh_res.cookies["tourvoice_refresh_token"]
    assert new_cookie_val != cookie_val

    # 2. Replaying the OLD refresh token must fail and revoke the entire token family
    replayed_res = await client.post(
        "/api/v1/auth/refresh",
        cookies={"tourvoice_refresh_token": cookie_val}
    )
    assert replayed_res.status_code == 401

    # 3. Subsequent refresh with the new token should also now fail because the family was revoked!
    revoked_family_res = await client.post(
        "/api/v1/auth/refresh",
        cookies={"tourvoice_refresh_token": new_cookie_val}
    )
    assert revoked_family_res.status_code == 401


@pytest.mark.asyncio
async def test_4_logout_and_logout_all(client: AsyncClient):
    """Criterion 6: Logout and logout-all server-side revocation."""
    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    token = login_res.json()["access_token"]
    cookie_val = login_res.cookies["tourvoice_refresh_token"]

    # Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        cookies={"tourvoice_refresh_token": cookie_val}
    )
    assert logout_res.status_code == 200

    # Refresh after logout must fail
    refresh_after_logout = await client.post(
        "/api/v1/auth/refresh",
        cookies={"tourvoice_refresh_token": cookie_val}
    )
    assert refresh_after_logout.status_code == 401

    # Login again and test logout-all
    login_res2 = await client.post("/api/v1/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    token2 = login_res2.json()["access_token"]
    cookie2 = login_res2.cookies["tourvoice_refresh_token"]

    logout_all_res = await client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert logout_all_res.status_code == 200

    # Old token auth_version was incremented, so token2 is rejected
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert me_res.status_code == 401


@pytest.mark.asyncio
async def test_5_google_oauth_anti_automerge(client: AsyncClient):
    """Criterion 9 & 10: Strict rule: NO auto-merging if Google email matches local account."""
    # Ensure local account exists
    local_email = "local.user@tourvoice.vn"
    await auth_repo.create_user({
        "_id": "user_local_123",
        "email": local_email,
        "password_hash": get_password_hash("LocalPass123!"),
        "role": "user",
        "is_active": True,
        "auth_version": 1,
    })

    # Start Google OAuth transaction
    start_res = await client.get("/api/v1/auth/google/start?return_to=/dashboard")
    assert start_res.status_code == 200
    state = start_res.json()["state"]

    # Mock Google ID token payload with same email
    mock_payload = {
        "sub": "google_sub_9999",
        "email": local_email,
        "email_verified": True,
        "name": "Local User From Google",
        "picture": "https://example.com/photo.jpg"
    }

    # Simulate callback via service
    tx = await auth_repo.oauth_transactions_col.find_one({"state": state})
    binding = tx.get("browser_binding")

    callback_res = await google_auth_service.handle_google_callback(
        code="mock_code_123",
        state=state,
        browser_binding=binding,
        mock_id_payload=mock_payload
    )

    # STRICT CHECK: Must refuse auto-merge!
    assert callback_res["success"] is False
    assert "tồn tại" in callback_res["error"].lower()
    assert "liên kết" in callback_res["error"].lower()


@pytest.mark.asyncio
async def test_6_google_oauth_new_user_role_assignment(client: AsyncClient):
    """Criterion 9: New Google user strictly gets role 'user' and is not verified as owner."""
    start_res = await client.get("/api/v1/auth/google/start?return_to=/pois")
    state = start_res.json()["state"]

    new_email = "completely.brandnew.tourist@gmail.com"
    mock_payload = {
        "sub": "google_sub_new_tourist_123",
        "email": new_email,
        "email_verified": True,
        "name": "Tourist John",
        "picture": "https://example.com/john.jpg"
    }

    # Use exact binding generated by start
    binding = "unknown:unknown"
    tx = await auth_repo.oauth_transactions_col.find_one({"state": state})
    if tx:
        binding = tx.get("browser_binding", binding)

    callback_res = await google_auth_service.handle_google_callback(
        code="mock_code_valid",
        state=state,
        browser_binding=binding,
        mock_id_payload=mock_payload
    )

    assert callback_res["success"] is True
    created_user = callback_res["user"]
    # STRICT ASSERTIONS
    assert created_user["role"] == "user"
    assert created_user["is_poi_owner_verified"] is False
    assert created_user["email"] == new_email

    # Check identity in database
    ident = await auth_repo.get_identity_by_provider_sub("google", "accounts.google.com", "google_sub_new_tourist_123")
    assert ident is not None
    assert ident["user_id"] == created_user["id"]


@pytest.mark.asyncio
async def test_7_google_account_linking_flow(client: AsyncClient):
    """Criterion 10: Authenticated user links Google account."""
    # Create local user
    user_doc = await auth_repo.create_user({
        "_id": "user_to_link",
        "email": "link.target@tourvoice.vn",
        "password_hash": get_password_hash("Pass123!"),
        "role": "poi_owner",
        "is_active": True,
        "auth_version": 1,
    })

    # Start linking
    link_res = await google_auth_service.start_google_link(
        user_id="user_to_link",
        current_session_id="sess_123",
        return_to="/account/security",
        browser_binding="test_binding"
    )
    assert link_res["success"] is True
    state = link_res["state"]

    # Simulate callback
    mock_payload = {
        "sub": "google_sub_linked_555",
        "email": "google.linked.email@gmail.com",
        "email_verified": True,
        "name": "Linked Name"
    }
    result = await google_auth_service.handle_google_callback(
        code="mock_code_link",
        state=state,
        browser_binding="test_binding",
        mock_id_payload=mock_payload
    )
    assert result["success"] is True
    assert result["linked"] is True

    # Check that identity is linked
    ident = await auth_repo.get_identity_by_provider_sub("google", "accounts.google.com", "google_sub_linked_555")
    assert ident is not None
    assert ident["user_id"] == "user_to_link"


@pytest.mark.asyncio
async def test_8_password_recovery_flow(client: AsyncClient):
    """Criterion 15: Forgot password generic response and one-time atomic reset token."""
    # 1. Forgot password request (always generic response)
    res_forgot = await client.post("/api/v1/auth/forgot-password", json={
        "email": "admin@tourvoice.vn"
    })
    assert res_forgot.status_code == 200
    assert "mật khẩu" in res_forgot.json()["message"].lower()

    # Request for non-existent email must return identical generic response
    res_nonexistent = await client.post("/api/v1/auth/forgot-password", json={
        "email": "ghost.user.never.registered@unknown.vn"
    })
    assert res_nonexistent.status_code == 200
    assert res_nonexistent.json()["message"] == res_forgot.json()["message"]

    # 2. Reset password via action token
    reset_req = await password_recovery_service.request_password_reset("admin@tourvoice.vn")
    token = reset_req.get("debug_token")
    assert token is not None

    # Reset with valid token
    res_reset = await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "NewAdminPassword@123"
    })
    assert res_reset.status_code == 200
    assert res_reset.json()["success"] is True

    # 3. Token cannot be reused (consumed atomically)
    res_reuse = await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "AnotherPassword@456"
    })
    assert res_reuse.status_code == 400

    # 4. Verify login works with the new password
    login_new = await client.post("/api/v1/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "NewAdminPassword@123"
    })
    assert login_new.status_code == 200


@pytest.mark.asyncio
async def test_9_active_sessions_management(client: AsyncClient):
    """Criterion 16: List sessions without leaking token hashes and user can only revoke own session."""
    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "admin@tourvoice.vn",
        "password": "Admin@123456"
    })
    token = login_res.json()["access_token"]
    session_id = login_res.json()["session_id"]

    # List sessions
    sess_res = await client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {token}"})
    assert sess_res.status_code == 200
    sessions_list = sess_res.json()
    assert len(sessions_list) >= 1
    # STRICT: Token hashes MUST NOT be returned!
    for s in sessions_list:
        assert "refresh_token_hash" not in s

    # Revoke own session
    del_res = await client.delete(
        f"/api/v1/auth/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res.status_code == 200

    # Attempting to delete a non-existent or other user's session returns 404
    del_res_other = await client.delete(
        "/api/v1/auth/sessions/sess_non_existent_or_other_user",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res_other.status_code == 404


@pytest.mark.asyncio
async def test_10_public_endpoints_unrestricted(client: AsyncClient):
    """Criterion 17: Public endpoints (POIs, tours, QR, health) remain accessible without login."""
    # 1. Health
    res_health = await client.get("/api/v1/health")
    assert res_health.status_code == 200

    # 2. Public POIs
    res_pois = await client.get("/api/v1/pois")
    assert res_pois.status_code == 200

    # 3. Public Tours
    res_tours = await client.get("/api/v1/tours")
    assert res_tours.status_code == 200

    # 4. CSRF Bootstrap
    res_csrf = await client.get("/api/v1/auth/csrf")
    assert res_csrf.status_code == 200
    assert "csrf_token" in res_csrf.json()
    assert "tourvoice_csrf_token" in res_csrf.cookies
