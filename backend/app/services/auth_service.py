"""Authentication & Access Control Service.

U01 / U02 / U03 / O01 / SD02 / AD02 / SD08 / AD08.
Implements JWT access tokens + server-side refresh sessions in auth_sessions.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import jwt

from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.core.permissions import ROLES_DEFINITION
from app.repositories.auth_repo import auth_repo
from app.repositories.owner_repo import owner_repo


class AuthService:
    def create_access_token(self, user_id: str, role: str, auth_version: int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "role": role,
            "auth_version": auth_version,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    async def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        user = await auth_repo.get_user_by_email(email)
        if not user:
            return {"success": False, "error": "Email hoặc mật khẩu không chính xác."}

        if not user.get("is_active", True):
            return {"success": False, "error": "Tài khoản đã bị khóa hoặc tạm ngưng."}

        # Check for Google-only (passwordless) account
        if not user.get("password_hash"):
            return {
                "success": False,
                "error": "Tài khoản này được đăng ký qua Google. Vui lòng đăng nhập bằng nút Google."
            }

        if not verify_password(password, user["password_hash"]):
            return {"success": False, "error": "Email hoặc mật khẩu không chính xác."}

        role_name = user.get("role", "user")
        role_doc = await auth_repo.get_role_by_name(role_name)
        permissions = role_doc.get("permissions", []) if role_doc else []

        # Create refresh session
        session_id = f"sess_{uuid.uuid4().hex}"
        refresh_token = f"ref_{uuid.uuid4().hex}_{uuid.uuid4().hex}"
        token_family_id = f"fam_{uuid.uuid4().hex[:12]}"
        auth_version = user.get("auth_version", 1)
        refresh_expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await auth_repo.create_session(
            session_id=session_id,
            user_id=user["_id"],
            refresh_token=refresh_token,
            token_family_id=token_family_id,
            auth_version=auth_version,
            expires_at=refresh_expire,
            ip_address=ip_address,
            user_agent=user_agent,
            authenticated_at=datetime.now(timezone.utc),
        )

        access_token = self.create_access_token(user["_id"], role_name, auth_version)

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "session_id": session_id,
            "refresh_token": refresh_token,
            "user": {
                "id": user["_id"],
                "email": user["email"],
                "full_name": user.get("full_name"),
                "role": role_name,
                "is_verified": user.get("is_verified", False),
                "is_poi_owner_verified": user.get("is_poi_owner_verified", False),
                "avatar_url": user.get("avatar_url"),
                "permissions": permissions,
            }
        }

    async def refresh_session(
        self,
        session_id: str,
        incoming_refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rotates refresh token and returns new access + refresh token."""
        new_refresh_token = f"ref_{uuid.uuid4().hex}_{uuid.uuid4().hex}"
        new_expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        updated_session = await auth_repo.verify_and_rotate_session(
            session_id=session_id,
            incoming_refresh_token=incoming_refresh_token,
            new_refresh_token=new_refresh_token,
            new_expires_at=new_expire,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not updated_session:
            return {"success": False, "error": "Phiên làm việc không hợp lệ hoặc đã hết hạn."}

        user = await auth_repo.get_user_by_id(updated_session["user_id"])
        if not user or not user.get("is_active", True):
            return {"success": False, "error": "Tài khoản không tồn tại hoặc đã bị khóa."}

        # Check auth_version
        if user.get("auth_version", 1) != updated_session.get("auth_version", 1):
            return {"success": False, "error": "Phiên đăng nhập đã bị vô hiệu hóa."}

        role_name = user.get("role", "user")
        access_token = self.create_access_token(user["_id"], role_name, user.get("auth_version", 1))

        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "session_id": session_id
        }

    async def logout(self, session_id: str) -> bool:
        return await auth_repo.revoke_session(session_id)

    async def logout_all(self, user_id: str) -> bool:
        """Revokes all active sessions for user and increments auth_version."""
        await auth_repo.revoke_all_user_sessions(user_id)
        await auth_repo.increment_auth_version(user_id)
        return True

    async def revoke_user_session(self, user_id: str, session_id: str) -> bool:
        """Revokes a specific session belonging strictly to the user."""
        return await auth_repo.revoke_user_session(user_id, session_id)

    async def reauthenticate(self, user_id: str, password: str) -> Dict[str, Any]:
        """Re-authenticates user for sensitive operations."""
        user = await auth_repo.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "Người dùng không tồn tại."}

        if not user.get("password_hash"):
            return {"success": False, "error": "Tài khoản chưa thiết lập mật khẩu (đăng nhập bằng Google)."}

        if not verify_password(password, user["password_hash"]):
            return {"success": False, "error": "Mật khẩu xác nhận không chính xác."}

        return {"success": True, "message": "Xác thực thành công."}

    async def register_owner(
        self,
        email: str,
        password: str,
        full_name: str,
        business_name: str
    ) -> Dict[str, Any]:
        """Registers a new POI owner account in pending state."""
        normalized_email = email.strip().lower()
        existing = await auth_repo.get_user_by_email(normalized_email)
        if existing:
            return {"success": False, "error": "Email này đã được đăng ký trong hệ thống."}

        user_id = f"user_{uuid.uuid4().hex[:12]}"
        pwd_hash = get_password_hash(password)

        user_doc = {
            "_id": user_id,
            "email": normalized_email,
            "full_name": full_name,
            "password_hash": pwd_hash,
            "role": "poi_owner",
            "is_active": True,
            "is_verified": True,
            "is_poi_owner_verified": False,  # Pending Admin review
            "auth_version": 1,
            "pii_encrypted": None,
        }
        await auth_repo.create_user(user_doc)

        # Create pending registration
        reg = await owner_repo.create_registration(user_id=user_id, business_name=business_name)

        return {
            "success": True,
            "user_id": user_id,
            "registration_id": reg["_id"],
            "status": "pending",
            "message": "Đăng ký thành công! Hồ sơ của bạn đang chờ Admin xét duyệt."
        }

    async def register_tourist(
        self,
        email: str,
        password: str,
        full_name: str,
        confirm_password: Optional[str] = None,
        guest_credential: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registers a tourist user with role 'user' (Section 4 & BR-ACCESS-04)."""
        clean_email = email.strip().lower()
        if confirm_password and password != confirm_password:
            return {"success": False, "error": "Mật khẩu xác nhận không khớp."}

        if len(password) < 6:
            return {"success": False, "error": "Mật khẩu phải có ít nhất 6 ký tự."}

        existing = await auth_repo.get_user_by_email(clean_email)
        if existing:
            return {"success": False, "error": "Email này đã được đăng ký trong hệ thống."}

        user_id = f"user_{uuid.uuid4().hex[:10]}"
        pwd_hash = get_password_hash(password)

        user_doc = {
            "_id": user_id,
            "email": clean_email,
            "password_hash": pwd_hash,
            "full_name": full_name.strip(),
            "role": "user",  # Strict default role 'user'
            "is_active": True,
            "is_verified": True,
            "is_poi_owner_verified": False,
            "auth_version": 1,
            "pii_encrypted": None,
        }
        await auth_repo.create_user(user_doc)

        # Claim guest session if provided
        merged_quota = False
        if guest_credential:
            from app.services.guest_service import guest_service
            claim_res = await guest_service.claim_guest_session(user_id, guest_credential)
            merged_quota = claim_res.get("claimed", False)

        # Generate login session and access token
        login_res = await self.login(
            email=clean_email,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent
        )

        if login_res.get("success"):
            login_res["merged_guest_quota"] = merged_quota
            login_res["message"] = "Đăng ký tài khoản du khách thành công."
            return login_res

        return {
            "success": True,
            "user_id": user_id,
            "email": clean_email,
            "role": "user",
            "message": "Đăng ký tài khoản thành công."
        }


    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        user = await auth_repo.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "Người dùng không tồn tại."}

        if not user.get("password_hash"):
            return {
                "success": False,
                "error": "Tài khoản này đăng nhập qua Google và chưa thiết lập mật khẩu."
            }

        if not verify_password(old_password, user["password_hash"]):
            return {"success": False, "error": "Mật khẩu hiện tại không chính xác."}

        if len(new_password) < 6:
            return {"success": False, "error": "Mật khẩu mới phải có ít nhất 6 ký tự."}

        new_hash = get_password_hash(new_password)
        await auth_repo.update_user(user_id, {"password_hash": new_hash})
        await auth_repo.increment_auth_version(user_id)
        await auth_repo.revoke_all_user_sessions(user_id)

        return {"success": True, "message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."}


auth_service = AuthService()

