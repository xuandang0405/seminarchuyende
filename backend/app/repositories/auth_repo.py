"""Repository for Auth: admin_users, roles, and auth_sessions.

Implements token family rotation and session revocation.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import hashlib

from app.repositories.base import BaseRepository
from app.db.collections import (
    COLLECTION_ADMIN_USERS,
    COLLECTION_ROLES,
    COLLECTION_AUTH_SESSIONS,
    COLLECTION_AUTH_IDENTITIES,
    COLLECTION_AUTH_ACTION_TOKENS,
    COLLECTION_OAUTH_TRANSACTIONS,
)


class AuthRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_ADMIN_USERS)

    @property
    def roles_col(self):
        return self.db[COLLECTION_ROLES]

    @property
    def sessions_col(self):
        return self.db[COLLECTION_AUTH_SESSIONS]

    @property
    def identities_col(self):
        return self.db[COLLECTION_AUTH_IDENTITIES]

    @property
    def action_tokens_col(self):
        return self.db[COLLECTION_AUTH_ACTION_TOKENS]

    @property
    def oauth_transactions_col(self):
        return self.db[COLLECTION_OAUTH_TRANSACTIONS]

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        normalized = email.strip().lower()
        return await self.collection.find_one({"email": normalized})

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"_id": user_id})

    async def create_user(self, user_doc: Dict[str, Any]) -> Dict[str, Any]:
        user_doc["email"] = user_doc["email"].strip().lower()
        now = datetime.now(timezone.utc)
        user_doc.setdefault("created_at", now)
        user_doc.setdefault("updated_at", now)
        user_doc.setdefault("auth_version", 1)
        await self.collection.insert_one(user_doc)
        return user_doc

    async def update_user(self, user_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields["updated_at"] = datetime.now(timezone.utc)
        return await self.collection.find_one_and_update(
            {"_id": user_id},
            {"$set": fields},
            return_document=True
        )

    async def increment_auth_version(self, user_id: str) -> int:
        """Invalidates all existing sessions/tokens for the user."""
        res = await self.collection.find_one_and_update(
            {"_id": user_id},
            {"$inc": {"auth_version": 1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        return res.get("auth_version", 1) if res else 1

    # =========================================================================
    # ROLES OPERATIONS
    # =========================================================================

    async def get_role_by_name(self, role_name: str) -> Optional[Dict[str, Any]]:
        return await self.roles_col.find_one({"name": role_name})

    async def get_all_roles(self) -> List[Dict[str, Any]]:
        cursor = self.roles_col.find().sort("priority", 1)
        return await cursor.to_list(length=20)

    # =========================================================================
    # SESSION OPERATIONS (auth_sessions)
    # =========================================================================

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        refresh_token: str,
        token_family_id: str,
        auth_version: int,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        authenticated_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": session_id,
            "user_id": user_id,
            "refresh_token_hash": self.hash_token(refresh_token),
            "token_family_id": token_family_id,
            "auth_version": auth_version,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "authenticated_at": authenticated_at or now,
            "created_at": now,
            "last_used_at": now,
            "expires_at": expires_at,
            "revoked_at": None,
        }
        await self.sessions_col.insert_one(doc)
        return doc

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self.sessions_col.find_one({"_id": session_id})

    async def verify_and_rotate_session(
        self,
        session_id: str,
        incoming_refresh_token: str,
        new_refresh_token: str,
        new_expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Rotates refresh token in the session. Detects reuse."""
        session = await self.get_session(session_id)
        if not session:
            return None

        # Check if already revoked
        if session.get("revoked_at") is not None:
            # Token reuse detected! Revoke the entire family
            await self.revoke_token_family(session.get("token_family_id"))
            return None

        incoming_hash = self.hash_token(incoming_refresh_token)
        if session.get("refresh_token_hash") != incoming_hash:
            # Token mismatch: possible breach, revoke family
            await self.revoke_token_family(session.get("token_family_id"))
            return None

        now = datetime.now(timezone.utc)
        new_hash = self.hash_token(new_refresh_token)
        update_fields: Dict[str, Any] = {
            "refresh_token_hash": new_hash,
            "last_used_at": now,
            "expires_at": new_expires_at,
        }
        if ip_address:
            update_fields["ip_address"] = ip_address
        if user_agent:
            update_fields["user_agent"] = user_agent

        updated = await self.sessions_col.find_one_and_update(
            {"_id": session_id},
            {"$set": update_fields},
            return_document=True
        )
        return updated

    async def revoke_session(self, session_id: str) -> bool:
        now = datetime.now(timezone.utc)
        res = await self.sessions_col.update_one(
            {"_id": session_id},
            {"$set": {"revoked_at": now}}
        )
        return res.modified_count > 0

    async def revoke_user_session(self, user_id: str, session_id: str) -> bool:
        """Revokes a session belonging strictly to the specified user."""
        now = datetime.now(timezone.utc)
        res = await self.sessions_col.update_one(
            {"_id": session_id, "user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": now}}
        )
        return res.modified_count > 0

    async def list_user_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Lists active (non-revoked, unexpired) sessions for user without leaking token hashes."""
        now = datetime.now(timezone.utc)
        cursor = self.sessions_col.find(
            {
                "user_id": user_id,
                "revoked_at": None,
                "expires_at": {"$gt": now}
            },
            projection={"refresh_token_hash": 0}
        ).sort("last_used_at", -1)
        return await cursor.to_list(length=50)

    async def revoke_token_family(self, token_family_id: str) -> int:
        now = datetime.now(timezone.utc)
        res = await self.sessions_col.update_many(
            {"token_family_id": token_family_id, "revoked_at": None},
            {"$set": {"revoked_at": now}}
        )
        return res.modified_count

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        res = await self.sessions_col.update_many(
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": now}}
        )
        return res.modified_count

    # =========================================================================
    # AUTH IDENTITIES (Google / OIDC)
    # =========================================================================

    async def get_identity_by_provider_sub(
        self,
        provider: str,
        issuer: str,
        subject: str
    ) -> Optional[Dict[str, Any]]:
        return await self.identities_col.find_one({
            "provider": provider,
            "issuer": issuer,
            "subject": subject
        })

    async def get_identities_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.identities_col.find({"user_id": user_id})
        return await cursor.to_list(length=10)

    async def get_identity_by_user_and_provider(
        self,
        user_id: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        return await self.identities_col.find_one({
            "user_id": user_id,
            "provider": provider
        })

    async def create_identity(self, identity_doc: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        identity_doc.setdefault("created_at", now)
        identity_doc.setdefault("last_login_at", now)
        await self.identities_col.insert_one(identity_doc)
        return identity_doc

    async def update_identity_login(self, identity_id: str) -> None:
        now = datetime.now(timezone.utc)
        await self.identities_col.update_one(
            {"_id": identity_id},
            {"$set": {"last_login_at": now}}
        )

    # =========================================================================
    # ACTION TOKENS (Password Reset)
    # =========================================================================

    async def create_action_token(
        self,
        token_id: str,
        user_id: str,
        purpose: str,
        token_hash: str,
        expires_at: datetime
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": token_id,
            "user_id": user_id,
            "purpose": purpose,
            "token_hash": token_hash,
            "created_at": now,
            "expires_at": expires_at,
            "consumed_at": None,
        }
        await self.action_tokens_col.insert_one(doc)
        return doc

    async def consume_action_token(
        self,
        token_hash: str,
        purpose: str
    ) -> Optional[Dict[str, Any]]:
        """Atomically checks and consumes a one-time action token."""
        now = datetime.now(timezone.utc)
        return await self.action_tokens_col.find_one_and_update(
            {
                "token_hash": token_hash,
                "purpose": purpose,
                "consumed_at": None,
                "expires_at": {"$gt": now}
            },
            {"$set": {"consumed_at": now}},
            return_document=False  # Return the state before consuming to read user_id
        )

    # =========================================================================
    # OAUTH TRANSACTIONS (State, Nonce, PKCE, ReturnTo)
    # =========================================================================

    async def save_oauth_transaction(self, doc: Dict[str, Any]) -> None:
        """Stores short-lived OAuth state transaction."""
        await self.oauth_transactions_col.update_one(
            {"state": doc["state"]},
            {"$set": doc},
            upsert=True
        )

    async def get_and_consume_oauth_transaction(self, state: str) -> Optional[Dict[str, Any]]:
        """Atomically retrieves and deletes OAuth transaction, validating expiry."""
        now = datetime.now(timezone.utc)
        return await self.oauth_transactions_col.find_one_and_delete(
            {
                "state": state,
                "expires_at": {"$gt": now}
            }
        )


auth_repo = AuthRepository()
