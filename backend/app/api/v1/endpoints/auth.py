"""Router for Authentication and Security endpoints.

Implements Sections 3, 4, 5, 6, 7, 8, 10 of UPDATE_PROMPT_LOGIN_GOOGLE_SECURITY.md:
- Email/Password login with rate-limiting and passwordless account protection.
- OpenID Connect / OAuth 2.0 Google login and linking.
- Refresh token rotation via HttpOnly cookie.
- CSRF bootstrap and token validation.
- Password recovery (forgot-password, reset-password, change-password, reauthenticate).
- Active user session management (list, revoke own session, logout-all).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
import jwt
import urllib.parse
import hashlib

from app.core.config import settings
from app.core.security import (
    generate_csrf_token,
    verify_csrf_token,
)
from app.services.auth_service import auth_service
from app.services.google_auth_service import google_auth_service
from app.services.password_recovery_service import password_recovery_service
from app.repositories.auth_repo import auth_repo

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# =============================================================================
# SCHEMAS
# =============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    session_id: Optional[str] = None
    refresh_token: Optional[str] = None


class RegisterOwnerRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    business_name: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ReauthenticateRequest(BaseModel):
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class GoogleStartRequest(BaseModel):
    return_to: Optional[str] = "/"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_browser_binding(request: Request) -> str:
    """Computes a browser binding fingerprint based on User-Agent and client IP."""
    ua = request.headers.get("User-Agent", "unknown")
    client_ip = request.client.host if request.client else "unknown"
    raw = f"{ua}:{client_ip}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def set_refresh_cookie(response: Response, session_id: str, refresh_token: str):
    """Sets secure HttpOnly cookie for refresh token rotation."""
    cookie_value = f"{session_id}:{refresh_token}"
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=cookie_value,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def clear_refresh_cookie(response: Response):
    """Clears refresh token cookie."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
    )


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    request: Request = None
) -> Dict[str, Any]:
    """Resolves authenticated user from Bearer access token."""
    if not token:
        # Check Authorization header directly if oauth2_scheme returned None
        auth_header = request.headers.get("Authorization") if request else None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu xác thực (thiếu Bearer token).",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token payload không hợp lệ.")

    user = await auth_repo.get_user_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không tồn tại hoặc đã bị khóa.")

    # Check auth_version
    token_auth_version = payload.get("auth_version", 1)
    if user.get("auth_version", 1) != token_auth_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã bị vô hiệu hóa.")

    # Attach permissions
    role_name = user.get("role", "user")
    role_doc = await auth_repo.get_role_by_name(role_name)
    user["permissions"] = role_doc.get("permissions", []) if role_doc else []

    return user


async def get_current_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yêu cầu quyền Quản trị viên (Admin).")
    return current_user


async def get_current_super_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yêu cầu quyền Quản trị tối cao (Super Admin).")
    return current_user


async def get_current_owner(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") not in ("poi_owner", "admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yêu cầu tài khoản Chủ quán (POI Owner).")
    return current_user


# =============================================================================
# CSRF & BOOTSTRAP ENDPOINT
# =============================================================================

@router.get("/csrf")
async def get_csrf(response: Response):
    """Bootstraps CSRF token for web application and sets non-HttpOnly cookie."""
    token = generate_csrf_token()
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Readable by frontend JS to attach X-CSRF-Token header
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return {"csrf_token": token}


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/login")
async def login(
    req: LoginRequest,
    request: Request,
    response: Response
):
    """Logs in with email/password and sets HttpOnly refresh cookie."""
    client_ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    res = await auth_service.login(
        email=req.email,
        password=req.password,
        ip_address=client_ip,
        user_agent=ua,
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.get("error"))

    set_refresh_cookie(response, res["session_id"], res["refresh_token"])
    return res


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    body: Optional[RefreshRequest] = None,
):
    """Refreshes access token with rotation. Reads from HttpOnly cookie or request body."""
    session_id = None
    incoming_refresh_token = None

    cookie_val = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_val and ":" in cookie_val:
        session_id, incoming_refresh_token = cookie_val.split(":", 1)
    elif body and body.session_id and body.refresh_token:
        session_id = body.session_id
        incoming_refresh_token = body.refresh_token

    if not session_id or not incoming_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy phiên làm việc để làm mới (thiếu refresh cookie)."
        )

    client_ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    res = await auth_service.refresh_session(
        session_id=session_id,
        incoming_refresh_token=incoming_refresh_token,
        ip_address=client_ip,
        user_agent=ua,
    )
    if not res.get("success"):
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.get("error"))

    set_refresh_cookie(response, res["session_id"], res["refresh_token"])
    return res


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    body: Optional[RefreshRequest] = None,
):
    """Revokes current session and clears HttpOnly refresh cookie."""
    session_id = None
    cookie_val = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_val and ":" in cookie_val:
        session_id = cookie_val.split(":", 1)[0]
    elif body and body.session_id:
        session_id = body.session_id

    if session_id:
        await auth_service.logout(session_id=session_id)

    clear_refresh_cookie(response)
    return {"success": True, "message": "Đăng xuất thành công."}


@router.post("/logout-all")
async def logout_all(
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Revokes all active sessions for current user."""
    await auth_service.logout_all(current_user["_id"])
    clear_refresh_cookie(response)
    return {"success": True, "message": "Đã đăng xuất khỏi tất cả thiết bị."}


@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Fetches currently authenticated user and resolved permissions."""
    # Check if user has linked Google identity
    google_link = await auth_repo.get_identity_by_user_and_provider(current_user["_id"], "google")

    return {
        "id": current_user["_id"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name"),
        "role": current_user.get("role"),
        "is_verified": current_user.get("is_verified", False),
        "is_poi_owner_verified": current_user.get("is_poi_owner_verified", False),
        "avatar_url": current_user.get("avatar_url"),
        "has_password": bool(current_user.get("password_hash")),
        "is_google_linked": bool(google_link),
        "permissions": current_user.get("permissions", []),
    }


# =============================================================================
# GOOGLE OIDC / OAUTH ENDPOINTS
# =============================================================================

@router.get("/google/start")
async def google_login_start(
    request: Request,
    return_to: Optional[str] = Query(default="/")
):
    """Initiates Google OAuth login transaction."""
    binding = get_browser_binding(request)
    res = await google_auth_service.start_google_login(return_to=return_to, browser_binding=binding)
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=res.get("error"))
    return res


@router.post("/google/link/start")
async def google_link_start(
    request: Request,
    body: Optional[GoogleStartRequest] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Initiates Google account linking transaction for logged-in user."""
    binding = get_browser_binding(request)
    return_to = body.return_to if body else "/account/security"
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME, "").split(":")[0]

    res = await google_auth_service.start_google_link(
        user_id=current_user["_id"],
        current_session_id=session_id,
        return_to=return_to,
        browser_binding=binding,
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Backend OAuth callback handling from Google redirect."""
    callback_frontend = settings.FRONTEND_CALLBACK_URL

    if error:
        redirect_url = f"{callback_frontend}?error={urllib.parse.quote(error)}"
        return RedirectResponse(url=redirect_url)

    if not code or not state:
        redirect_url = f"{callback_frontend}?error={urllib.parse.quote('Thiếu thông số code hoặc state từ Google.')}"
        return RedirectResponse(url=redirect_url)

    binding = get_browser_binding(request)
    client_ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    res = await google_auth_service.handle_google_callback(
        code=code,
        state=state,
        browser_binding=binding,
        ip_address=client_ip,
        user_agent=ua,
    )

    if not res.get("success"):
        err_msg = res.get("error", "Đăng nhập Google thất bại.")
        redirect_url = f"{callback_frontend}?error={urllib.parse.quote(err_msg)}"
        return RedirectResponse(url=redirect_url)

    # If this was account linking
    if res.get("linked"):
        return_to = res.get("return_to", "/account/security")
        redirect_url = f"{callback_frontend}?linked=true&return_to={urllib.parse.quote(return_to)}"
        return RedirectResponse(url=redirect_url)

    # Login succeeded: Set HttpOnly refresh cookie
    return_to = res.get("return_to", "/")
    redirect_url = f"{callback_frontend}?return_to={urllib.parse.quote(return_to)}"
    redirect_response = RedirectResponse(url=redirect_url)
    set_refresh_cookie(redirect_response, res["session_id"], res["refresh_token"])
    return redirect_response


# =============================================================================
# PASSWORD RECOVERY & MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Requests a password reset link. Always returns a generic response."""
    return await password_recovery_service.request_password_reset(req.email)


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """Resets password using single-use action token."""
    res = await password_recovery_service.reset_password(req.token, req.new_password)
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Changes password for an authenticated user with a password."""
    res = await auth_service.change_password(
        user_id=current_user["_id"],
        old_password=req.current_password,
        new_password=req.new_password,
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res


@router.post("/reauthenticate")
async def reauthenticate(
    req: ReauthenticateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Confirms current password for sensitive actions."""
    res = await auth_service.reauthenticate(current_user["_id"], req.password)
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.get("error"))
    return res


# =============================================================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/sessions")
async def list_sessions(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Lists all active sessions for current user."""
    sessions = await auth_repo.list_user_active_sessions(current_user["_id"])
    # Format for client
    formatted = []
    for s in sessions:
        formatted.append({
            "id": s["_id"],
            "ip_address": s.get("ip_address"),
            "user_agent": s.get("user_agent"),
            "created_at": s.get("created_at"),
            "last_used_at": s.get("last_used_at"),
            "expires_at": s.get("expires_at"),
        })
    return formatted


@router.delete("/sessions/{session_id}")
async def revoke_session_endpoint(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Revokes a specific session belonging strictly to the current user."""
    success = await auth_service.revoke_user_session(current_user["_id"], session_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phiên làm việc không tồn tại hoặc không thuộc quyền sở hữu.")
    return {"success": True, "message": "Thu hồi phiên làm việc thành công."}


# =============================================================================
# OWNER REGISTRATION
# =============================================================================

@router.post("/register-owner", status_code=status.HTTP_201_CREATED)
async def register_owner(req: RegisterOwnerRequest):
    """Public registration for Restaurant / Store Owners (Chủ quán)."""
    res = await auth_service.register_owner(
        email=req.email,
        password=req.password,
        full_name=req.full_name,
        business_name=req.business_name,
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res
