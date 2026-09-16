"""Password Recovery Service.

Implements Section 8 of UPDATE_PROMPT_LOGIN_GOOGLE_SECURITY.md:
- Forgot password: always returns a generic response (no account enumeration).
- Reset password: one-time action token (atomic consumption), expires in 15 minutes.
- Google-only accounts cannot be reset via password recovery (must login with Google).
- Successfully resetting password invalidates all existing sessions and increments auth_version.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging

from app.core.config import settings
from app.core.security import (
    generate_random_token,
    hash_token,
    get_password_hash,
)
from app.repositories.auth_repo import auth_repo

logger = logging.getLogger("uvicorn")


class PasswordRecoveryService:
    GENERIC_FORGOT_MESSAGE = (
        "Nếu email này tồn tại trong hệ thống và có mật khẩu, hướng dẫn đặt lại mật khẩu đã được xử lý."
    )

    async def request_password_reset(self, email: str) -> Dict[str, Any]:
        """Requests password reset. Always returns a generic response."""
        normalized_email = email.strip().lower()
        user = await auth_repo.get_user_by_email(normalized_email)

        # Non-enumerating logic:
        # If user doesn't exist, is inactive, or has no password (Google-only), return generic message
        if not user or not user.get("is_active", True) or not user.get("password_hash"):
            return {
                "success": True,
                "message": self.GENERIC_FORGOT_MESSAGE
            }

        # Generate single-use reset token
        raw_token = generate_random_token(32)
        token_hash_val = hash_token(raw_token)
        token_id = f"act_{uuid.uuid4().hex[:12]}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        await auth_repo.create_action_token(
            token_id=token_id,
            user_id=user["_id"],
            purpose="password_reset",
            token_hash=token_hash_val,
            expires_at=expires_at,
        )

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        # In a real SMTP production deployment, this sends an email.
        # For development / seminar demo, log without exposing credentials.
        logger.info(f"Password reset requested for user {user['_id']}. Reset URL configured: {settings.FRONTEND_URL}/reset-password")

        return {
            "success": True,
            "message": self.GENERIC_FORGOT_MESSAGE,
            # In debug/local test environments, expose token if configured for automated tests
            "debug_token": raw_token if settings.DEBUG else None
        }

    async def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """Atomically validates and consumes token, updating password and revoking sessions."""
        if not token or not token.strip():
            return {
                "success": False,
                "error": "Mã xác thực đặt lại mật khẩu không hợp lệ."
            }

        if len(new_password) < 6:
            return {
                "success": False,
                "error": "Mật khẩu mới phải có ít nhất 6 ký tự."
            }

        token_hash_val = hash_token(token.strip())

        # Atomic find_one_and_update ensures only ONE request can consume this token
        consumed_record = await auth_repo.consume_action_token(
            token_hash=token_hash_val,
            purpose="password_reset"
        )

        if not consumed_record:
            return {
                "success": False,
                "error": "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn. Vui lòng gửi yêu cầu mới."
            }

        user_id = consumed_record["user_id"]
        user = await auth_repo.get_user_by_id(user_id)
        if not user or not user.get("is_active", True):
            return {
                "success": False,
                "error": "Tài khoản không tồn tại hoặc đã bị vô hiệu hóa."
            }

        new_hash = get_password_hash(new_password)
        await auth_repo.update_user(user_id, {"password_hash": new_hash})
        await auth_repo.increment_auth_version(user_id)
        await auth_repo.revoke_all_user_sessions(user_id)

        return {
            "success": True,
            "message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại bằng mật khẩu mới."
        }


password_recovery_service = PasswordRecoveryService()
