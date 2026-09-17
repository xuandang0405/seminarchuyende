"""Service for Guest Sessions & Guest Claiming.

G01 / G03 / BR-ACCESS-02 / BR-ACCESS-04.
"""

from datetime import datetime, timezone
import hashlib
import secrets
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings
from app.repositories.guest_repo import guest_repo
from app.repositories.trial_repo import trial_repo


class GuestService:
    def _hash_credential(self, credential: str) -> str:
        return hashlib.sha256(credential.encode("utf-8")).hexdigest()

    async def create_guest_session(
        self,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new anonymous guest session with cryptographically secure token."""
        raw_credential = secrets.token_urlsafe(32)
        credential_hash = self._hash_credential(raw_credential)

        doc = await guest_repo.create_guest_session(
            credential_hash=credential_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            days_valid=30
        )

        return {
            "guest_session_id": doc["_id"],
            "guest_credential": raw_credential,
            "expires_at": doc["expires_at"],
            "message": "Phiên khách được khởi tạo thành công."
        }

    async def resolve_guest_session(self, credential: str) -> Optional[Dict[str, Any]]:
        """Validates guest credential and returns active session."""
        if not credential:
            return None
        credential_hash = self._hash_credential(credential)
        return await guest_repo.get_by_credential_hash(credential_hash)

    async def claim_guest_session(
        self,
        user_id: str,
        guest_credential: str
    ) -> Dict[str, Any]:
        """Claims guest session to logged-in user and merges trial quota idempotently."""
        session = await self.resolve_guest_session(guest_credential)
        if not session:
            # Check if already claimed
            credential_hash = self._hash_credential(guest_credential)
            claimed_doc = await guest_repo.find_one({"credential_hash": credential_hash})
            if claimed_doc and claimed_doc.get("claimed_user_id") == user_id:
                usage = await trial_repo.get_or_create_usage("user", user_id, settings.TRIAL_POLICY_VERSION)
                remaining = 1 if usage.get("state") == "available" else 0
                return {
                    "success": True,
                    "claimed": True,
                    "guest_session_id": claimed_doc["_id"],
                    "user_id": user_id,
                    "trial_quota_merged": True,
                    "trial_remaining": remaining,
                    "message": "Phiên khách đã được liên kết trước đó."
                }
            return {
                "success": False,
                "claimed": False,
                "error": "Phiên khách không hợp lệ hoặc đã hết hạn."
            }

        guest_session_id = session["_id"]

        # 1. Atomically merge quota
        success, final_state = await trial_repo.merge_quota_into_user(
            guest_session_id=guest_session_id,
            user_id=user_id,
            policy_version=settings.TRIAL_POLICY_VERSION
        )

        # 2. Mark guest session claimed and revoke old credential
        await guest_repo.claim_session(guest_session_id, user_id)

        remaining = 1 if final_state == "available" else 0
        return {
            "success": True,
            "claimed": True,
            "guest_session_id": guest_session_id,
            "user_id": user_id,
            "trial_quota_merged": success,
            "trial_remaining": remaining,
            "message": "Hợp nhất phiên khách vào tài khoản thành công."
        }


guest_service = GuestService()
