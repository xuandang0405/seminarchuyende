"""Google OAuth 2.0 / OpenID Connect Authentication Service.

Implements Section 7 of UPDATE_PROMPT_LOGIN_GOOGLE_SECURITY.md:
- Authorization Code + OpenID Connect flow with PKCE S256 and browser-binding state.
- Strict token claims verification (RS256 JWKS/certs, issuer, audience, nonce).
- Strict account policies:
    * No auto-merge with existing local accounts without explicit linking.
    * No automatic admin promotion or POI owner verification.
    * Google-only accounts with nullable password_hash.
    * Safe return URL validation to prevent open redirects.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import urllib.parse
import httpx
import jwt

from app.core.config import settings
from app.core.security import (
    generate_random_token,
    generate_pkce_pair,
    is_safe_return_url,
)
from app.repositories.auth_repo import auth_repo
from app.services.auth_service import auth_service


GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ["https://accounts.google.com", "accounts.google.com"]


class GoogleAuthService:
    def __init__(self):
        self._jwks_client: Optional[jwt.PyJWKClient] = None

    @property
    def jwks_client(self) -> jwt.PyJWKClient:
        if self._jwks_client is None:
            self._jwks_client = jwt.PyJWKClient(GOOGLE_JWKS_URL)
        return self._jwks_client

    def is_configured(self) -> bool:
        """Returns True if Google client ID and secret are configured."""
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)

    async def start_google_login(
        self,
        return_to: Optional[str],
        browser_binding: str
    ) -> Dict[str, Any]:
        """Initiates Google login OAuth transaction."""
        if not settings.GOOGLE_CLIENT_ID:
            return {
                "success": False,
                "error": "Google OAuth chưa được cấu hình trên hệ thống (thiếu GOOGLE_CLIENT_ID)."
            }

        safe_return_to = return_to if is_safe_return_url(return_to, settings.ALLOWED_RETURN_PATHS) else "/"
        state = generate_random_token(32)
        nonce = generate_random_token(16)
        code_verifier, code_challenge = generate_pkce_pair()

        # Store short-lived OAuth transaction (10 minutes)
        tx_doc = {
            "state": state,
            "browser_binding": browser_binding,
            "nonce": nonce,
            "code_verifier": code_verifier,
            "purpose": "login",
            "return_to": safe_return_to,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
        }
        await auth_repo.save_oauth_transaction(tx_doc)

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
        return {"success": True, "auth_url": auth_url, "state": state}

    async def start_google_link(
        self,
        user_id: str,
        current_session_id: str,
        return_to: Optional[str],
        browser_binding: str
    ) -> Dict[str, Any]:
        """Initiates Google account linking OAuth transaction for an authenticated user."""
        if not settings.GOOGLE_CLIENT_ID:
            return {
                "success": False,
                "error": "Google OAuth chưa được cấu hình trên hệ thống (thiếu GOOGLE_CLIENT_ID)."
            }

        # Check if user already linked Google
        existing_link = await auth_repo.get_identity_by_user_and_provider(user_id, "google")
        if existing_link:
            return {
                "success": False,
                "error": "Tài khoản của bạn đã được liên kết với Google rồi."
            }

        safe_return_to = return_to if is_safe_return_url(return_to, settings.ALLOWED_RETURN_PATHS) else "/account/security"
        state = generate_random_token(32)
        nonce = generate_random_token(16)
        code_verifier, code_challenge = generate_pkce_pair()

        tx_doc = {
            "state": state,
            "browser_binding": browser_binding,
            "nonce": nonce,
            "code_verifier": code_verifier,
            "purpose": "link",
            "user_id": user_id,
            "session_id": current_session_id,
            "return_to": safe_return_to,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
        }
        await auth_repo.save_oauth_transaction(tx_doc)

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
        return {"success": True, "auth_url": auth_url, "state": state}

    async def verify_google_id_token(
        self,
        id_token_str: str,
        expected_nonce: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cryptographically verifies Google ID token using JWKS public keys."""
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(id_token_str)
            claims = jwt.decode(
                id_token_str,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.GOOGLE_CLIENT_ID,
                issuer=GOOGLE_ISSUERS,
                options={"verify_exp": True}
            )
        except Exception as e:
            raise ValueError(f"Xác minh Google ID Token thất bại: {str(e)}")

        if expected_nonce and claims.get("nonce") != expected_nonce:
            raise ValueError("Google ID Token nonce không khớp với giao dịch khởi tạo.")

        return claims

    async def handle_google_callback(
        self,
        code: str,
        state: str,
        browser_binding: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        mock_id_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handles Google OAuth callback, verifies identity, applies account policy, and returns session."""
        # 1. Retrieve and consume OAuth transaction atomically
        tx = await auth_repo.get_and_consume_oauth_transaction(state)
        if not tx:
            return {
                "success": False,
                "error": "Phiên xác thực Google không hợp lệ hoặc đã hết hạn. Vui lòng thử lại."
            }

        # 2. Verify browser binding
        if tx.get("browser_binding") != browser_binding:
            return {
                "success": False,
                "error": "Phát hiện sai lệch trình duyệt (browser binding mismatch). Vui lòng thử lại từ cùng trình duyệt."
            }

        # 3. Obtain and verify ID token
        if mock_id_payload is not None:
            id_payload = mock_id_payload
        else:
            if not self.is_configured():
                return {
                    "success": False,
                    "error": "Google OAuth chưa được cấu hình đầy đủ trên server (thiếu client ID hoặc secret)."
                }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    token_res = await client.post(
                        GOOGLE_TOKEN_ENDPOINT,
                        data={
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "code": code,
                            "grant_type": "authorization_code",
                            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                            "code_verifier": tx.get("code_verifier"),
                        }
                    )
                if token_res.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Không thể đổi mã code với Google (status {token_res.status_code})."
                    }
                tokens_data = token_res.json()
                raw_id_token = tokens_data.get("id_token")
                if not raw_id_token:
                    return {"success": False, "error": "Google không trả về id_token."}

                id_payload = await self.verify_google_id_token(raw_id_token, tx.get("nonce"))
            except Exception as e:
                return {"success": False, "error": f"Lỗi xác thực với Google: {str(e)}"}

        # 4. Validate core OpenID claims
        sub = id_payload.get("sub")
        email = id_payload.get("email")
        email_verified = id_payload.get("email_verified", False)

        if not sub or not email:
            return {
                "success": False,
                "error": "Thông tin Google ID Token không đầy đủ (thiếu sub hoặc email)."
            }

        if not email_verified:
            return {
                "success": False,
                "error": "Tài khoản Google này chưa được xác minh email bởi Google."
            }

        normalized_email = email.strip().lower()
        purpose = tx.get("purpose", "login")

        # 5. Handle account linking flow
        if purpose == "link":
            target_user_id = tx.get("user_id")
            if not target_user_id:
                return {"success": False, "error": "Giao dịch liên kết không chứa user_id hợp lệ."}

            # Check if this Google identity is already linked to anyone
            existing_identity = await auth_repo.get_identity_by_provider_sub("google", "accounts.google.com", str(sub))
            if existing_identity:
                if existing_identity["user_id"] != target_user_id:
                    return {
                        "success": False,
                        "error": "Tài khoản Google này đã được liên kết với một tài khoản TourVoice khác."
                    }
                return {
                    "success": True,
                    "linked": True,
                    "message": "Tài khoản của bạn đã được liên kết với Google này từ trước.",
                    "return_to": tx.get("return_to", "/account/security"),
                }

            # Check if target user already linked to ANY Google identity
            current_user_link = await auth_repo.get_identity_by_user_and_provider(target_user_id, "google")
            if current_user_link:
                return {
                    "success": False,
                    "error": "Tài khoản của bạn hiện đã liên kết với một tài khoản Google khác."
                }

            # Create auth_identities document
            ident_doc = {
                "_id": f"ident_{uuid.uuid4().hex[:12]}",
                "user_id": target_user_id,
                "provider": "google",
                "issuer": "accounts.google.com",
                "subject": str(sub),
                "email_at_link": normalized_email,
            }
            await auth_repo.create_identity(ident_doc)
            return {
                "success": True,
                "linked": True,
                "message": "Liên kết tài khoản Google thành công!",
                "return_to": tx.get("return_to", "/account/security"),
            }

        # 6. Handle login flow
        # Check if identity already exists
        identity = await auth_repo.get_identity_by_provider_sub("google", "accounts.google.com", str(sub))

        if identity:
            # Identity exists -> find user
            user = await auth_repo.get_user_by_id(identity["user_id"])
            if not user:
                return {"success": False, "error": "Tài khoản liên kết không tồn tại trong hệ thống."}

            if not user.get("is_active", True):
                return {"success": False, "error": "Tài khoản đã bị khóa hoặc tạm ngưng."}

            await auth_repo.update_identity_login(identity["_id"])
            target_user = user
        else:
            # Identity does not exist: check if email is already in admin_users
            existing_user = await auth_repo.get_user_by_email(normalized_email)
            if existing_user:
                # STRICT SPEC REQUIREMENT: Refuse auto-merge!
                return {
                    "success": False,
                    "error": "Tài khoản đã tồn tại với email này. Vui lòng đăng nhập bằng mật khẩu rồi liên kết Google trong mục Cài đặt Bảo mật."
                }

            # Create new minimal user with role "user" (no admin promotion, no owner verification)
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            new_user = {
                "_id": user_id,
                "email": normalized_email,
                "full_name": id_payload.get("name") or normalized_email.split("@")[0],
                "password_hash": None,  # Google-only account
                "role": "user",         # Strictly 'user' role
                "is_active": True,
                "is_verified": True,
                "is_poi_owner_verified": False,
                "avatar_url": id_payload.get("picture"),
                "auth_version": 1,
                "email_verified_at": now,
                "created_at": now,
                "updated_at": now,
            }
            await auth_repo.create_user(new_user)
            target_user = new_user

            # Create identity link
            ident_doc = {
                "_id": f"ident_{uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "provider": "google",
                "issuer": "accounts.google.com",
                "subject": str(sub),
                "email_at_link": normalized_email,
            }
            await auth_repo.create_identity(ident_doc)

        # 7. Create application session and tokens
        session_id = f"sess_{uuid.uuid4().hex}"
        refresh_token = f"ref_{uuid.uuid4().hex}_{uuid.uuid4().hex}"
        token_family_id = f"fam_{uuid.uuid4().hex[:12]}"
        auth_version = target_user.get("auth_version", 1)
        refresh_expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await auth_repo.create_session(
            session_id=session_id,
            user_id=target_user["_id"],
            refresh_token=refresh_token,
            token_family_id=token_family_id,
            auth_version=auth_version,
            expires_at=refresh_expire,
            ip_address=ip_address,
            user_agent=user_agent,
            authenticated_at=datetime.now(timezone.utc),
        )

        role_name = target_user.get("role", "user")
        role_doc = await auth_repo.get_role_by_name(role_name)
        permissions = role_doc.get("permissions", []) if role_doc else []

        access_token = auth_service.create_access_token(
            target_user["_id"],
            role_name,
            auth_version
        )

        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id,
            "return_to": tx.get("return_to", "/"),
            "user": {
                "id": target_user["_id"],
                "email": target_user["email"],
                "full_name": target_user.get("full_name"),
                "role": role_name,
                "is_verified": target_user.get("is_verified", False),
                "is_poi_owner_verified": target_user.get("is_poi_owner_verified", False),
                "avatar_url": target_user.get("avatar_url"),
                "permissions": permissions,
            }
        }


google_auth_service = GoogleAuthService()
