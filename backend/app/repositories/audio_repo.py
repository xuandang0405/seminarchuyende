from typing import Any, Dict, List, Optional
from app.repositories.base import BaseRepository


class AudioRepository(BaseRepository):
    def __init__(self):
        super().__init__("audio_assets")

    async def find_by_content_id(self, poi_content_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"poi_content_id": poi_content_id}).sort([("created_at", -1)])
        return await cursor.to_list(length=10)

    async def find_by_storage_key(self, storage_key: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"storage_key": storage_key})

    async def find_by_sha256(self, sha256: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"sha256": sha256})


audio_repo = AudioRepository()
