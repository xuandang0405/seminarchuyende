"""Repository for Playback Grants.

G02 / BR-ACCESS-01 / BR-TRIAL-05.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db.collections import COLLECTION_PLAYBACK_GRANTS
from app.repositories.base import BaseRepository


class PlaybackGrantRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_PLAYBACK_GRANTS)

    async def create_grant(
        self,
        playback_id: str,
        grant_token: str,
        subject_type: str,
        subject_id: str,
        tour_id: str,
        poi_id: str,
        lang: str,
        scope: str,  # "trial" | "entitled"
        asset_storage_key: str,
        expires_at: datetime
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": playback_id,
            "grant_token": grant_token,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "tour_id": tour_id,
            "poi_id": poi_id,
            "lang": lang,
            "scope": scope,
            "asset_storage_key": asset_storage_key,
            "delivery_state": "granted",  # "granted" | "streaming" | "completed"
            "first_delivered_at": None,
            "expires_at": expires_at,
            "created_at": now
        }
        await self.insert_one(doc)
        return doc

    async def get_by_token(self, grant_token: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return await self.find_one({
            "grant_token": grant_token,
            "expires_at": {"$gt": now}
        })

    async def mark_delivery(self, playback_id: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return await self.collection.find_one_and_update(
            {"_id": playback_id},
            {
                "$set": {
                    "delivery_state": "streaming",
                    "first_delivered_at": now
                }
            },
            return_document=True
        )


playback_grant_repo = PlaybackGrantRepository()
