"""Repository for managing anonymous device identities in analytics_devices.

Implements BR-DEVICE-01 / BR-DEVICE-02 / Section 9:
- Server issues 256-bit cryptographically random token.
- Server ONLY stores HMAC-SHA256 hash of token, never raw token.
- Never uses raw IP as device identifier.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings
from app.db.collections import COLLECTION_ANALYTICS_DEVICES
from app.repositories.base import BaseRepository


class DeviceRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_ANALYTICS_DEVICES)

    def hash_token(self, token: str) -> str:
        """Computes HMAC-SHA256 hash of device token using server SECRET_KEY."""
        key = settings.SECRET_KEY.encode("utf-8")
        msg = token.encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    async def find_by_token_hash(self, token_hash: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"token_hash": token_hash})

    async def get_or_create_device(
        self,
        token: Optional[str] = None,
        platform: str = "web",
        app_version: Optional[str] = "1.0.0"
    ) -> Tuple[Dict[str, Any], str, bool]:
        """Bootstrap or recover a device identity.
        
        Returns: (device_doc, raw_device_token, is_new)
        """
        now = datetime.now(timezone.utc)

        if token and token.strip():
            token_hash = self.hash_token(token.strip())
            existing = await self.find_by_token_hash(token_hash)
            if existing:
                await self.collection.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": {
                            "last_seen_at": now,
                            "platform": platform,
                            "app_version": app_version or existing.get("app_version"),
                            "updated_at": now,
                        }
                    }
                )
                existing["last_seen_at"] = now
                return existing, token.strip(), False

        # Generate new high-entropy token (32 bytes = 256-bit)
        new_token = secrets.token_urlsafe(32)
        token_hash = self.hash_token(new_token)
        device_id = f"dev_{uuid.uuid4().hex[:12]}"

        doc = {
            "_id": device_id,
            "token_hash": token_hash,
            "platform": platform,
            "app_version": app_version,
            "consent_granted": True,
            "consent_version": 1,
            "consent_scopes": ["events", "route_sampling"],
            "consent_updated_at": now,
            "first_seen_at": now,
            "last_seen_at": now,
            "created_at": now,
            "updated_at": now,
        }

        await self.collection.insert_one(doc)
        return doc, new_token, True

    async def record_consent(
        self,
        device_id: str,
        consent_granted: bool,
        scopes: Optional[list] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        scopes = scopes or (["events", "route_sampling"] if consent_granted else [])
        update_doc = {
            "consent_granted": consent_granted,
            "consent_scopes": scopes,
            "consent_updated_at": now,
            "last_seen_at": now,
            "updated_at": now,
        }
        if not consent_granted:
            update_doc["consent_revoked_at"] = now

        res = await self.collection.find_one_and_update(
            {"_id": device_id},
            {"$set": update_doc},
            return_document=True
        )
        return res


device_repo = DeviceRepository()
