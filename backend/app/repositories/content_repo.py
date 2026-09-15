from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository


class ContentRepository(BaseRepository):
    def __init__(self):
        super().__init__("poi_contents")

    async def find_by_poi_and_lang(
        self,
        poi_id: str,
        language_code: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"poi_id": poi_id, "language_code": language_code}
        if status:
            query["review_status"] = status
        cursor = self.collection.find(query).sort([("version", -1)])
        return await cursor.to_list(length=50)

    async def get_latest_version_number(self, poi_id: str, language_code: str) -> int:
        cursor = self.collection.find(
            {"poi_id": poi_id, "language_code": language_code}
        ).sort([("version", -1)]).limit(1)
        docs = await cursor.to_list(length=1)
        if docs:
            return docs[0].get("version", 1)
        return 0

    async def approve_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": content_id},
            {
                "$set": {
                    "review_status": "approved",
                    "reviewed_at": now,
                    "updated_at": now
                }
            }
        )
        return await self.get_by_id(content_id)


content_repo = ContentRepository()
