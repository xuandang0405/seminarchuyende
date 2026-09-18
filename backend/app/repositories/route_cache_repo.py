"""Repository for route cache collection with TTL and fingerprint lookup."""

from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone
from app.repositories.base import BaseRepository
from app.db.collections import COLLECTION_ROUTE_CACHE


class RouteCacheRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_ROUTE_CACHE)

    async def get_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Finds cached route if not expired."""
        now = datetime.now(timezone.utc)
        doc = await self.collection.find_one({
            "fingerprint": fingerprint,
            "expires_at": {"$gt": now}
        })
        return doc

    async def save_route(
        self,
        fingerprint: str,
        mode: str,
        route_data: Dict[str, Any],
        ttl_hours: int = 24
    ) -> None:
        """Upserts a calculated route into cache with expiration date."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)

        cache_doc = {
            "fingerprint": fingerprint,
            "mode": mode,
            "route": route_data,
            "created_at": now,
            "expires_at": expires_at
        }
        await self.collection.update_one(
            {"fingerprint": fingerprint},
            {"$set": cache_doc},
            upsert=True
        )

    async def invalidate_all(self) -> int:
        """Invalidates all cached routes (called when POI coordinates or tours are updated)."""
        res = await self.collection.delete_many({})
        return res.deleted_count


route_cache_repo = RouteCacheRepository()
