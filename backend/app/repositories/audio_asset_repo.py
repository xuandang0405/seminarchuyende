from app.repositories.base import BaseRepository


class AudioAssetRepository(BaseRepository):
    def __init__(self):
        super().__init__("audio_assets")

    async def find_by_content_id(self, content_id):
        return await self.list({"poi_content_id": content_id}, sort=[("created_at", -1)])


audio_asset_repo = AudioAssetRepository()
