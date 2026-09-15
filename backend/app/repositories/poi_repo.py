from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository


class POIRepository(BaseRepository):
    def __init__(self):
        super().__init__("pois")

    async def find_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"code": code})

    async def find_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"owner_id": owner_id})
        return await cursor.to_list(length=100)

    async def find_nearby(
        self,
        longitude: float,
        latitude: float,
        max_distance_meters: float = 1000.0,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "status": status,
            "location": {
                "$nearSphere": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "$maxDistance": max_distance_meters
                }
            }
        }
        if category:
            query["category"] = category

        cursor = self.collection.find(query).limit(limit)
        return await cursor.to_list(length=limit)

    async def update_published_content(
        self,
        poi_id: str,
        language_code: str,
        content_id: str,
        audio_asset_id: str,
        published_by: str
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        pub_dict = {
            "content_id": content_id,
            "audio_asset_id": audio_asset_id,
            "published_at": now,
            "published_by": published_by
        }
        await self.collection.update_one(
            {"_id": poi_id},
            {
                "$set": {
                    f"published_contents.{language_code}": pub_dict,
                    "updated_at": now
                },
                "$inc": {"revision": 1}
            }
        )
        return await self.get_by_id(poi_id)


poi_repo = POIRepository()
