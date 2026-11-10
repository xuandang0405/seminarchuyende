"""Import the bundled, public sample catalog into the disposable demo database."""
import asyncio
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo, get_database
from app.db.collections import COLLECTION_POI, COLLECTION_POI_LOCALIZATIONS
from app.services.audio_metadata import mp3_duration_ms


async def main():
    if not settings.is_development or settings.DATABASE_NAME != "tourvoice_release_demo":
        raise SystemExit("Sample content is only available in the release demo database.")
    await connect_to_mongo()
    try:
        db = get_database()
        folder = Path(__file__).resolve().parent
        places = json.loads((folder / "places.json").read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc)
        for place in places:
            localizations = place.pop("localizations")
            poi_id = place["_id"]
            if await db[COLLECTION_POI].find_one({"_id": poi_id}):
                continue
            for lang, content in localizations.items():
                audio_name = f"{poi_id}_{lang}.mp3"
                source = folder / "audio" / audio_name
                localization = {
                    **content, "poi_id": poi_id, "lang": lang, "version": 1,
                    "source_version": 1, "translation_status": "ready",
                    "audio_status": "missing", "updated_at": now,
                }
                if source.is_file():
                    key = f"audio/{audio_name}"
                    destination = Path(settings.MEDIA_STORAGE_DIR) / key
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
                    localization.update(audio_status="ready", audio_storage_key=key,
                                        audio_url=f"/storage/{key}", audio_duration_ms=mp3_duration_ms(source.read_bytes()))
                await db[COLLECTION_POI_LOCALIZATIONS].update_one(
                    {"poi_id": poi_id, "lang": lang}, {"$setOnInsert": localization}, upsert=True,
                )
            await db[COLLECTION_POI].update_one({"_id": poi_id}, {"$setOnInsert": {
                **place, "is_active": True, "activation_requested": True,
                "version": 1, "content_version": 1, "source_lang": "vi",
                "images": [], "created_at": now, "updated_at": now, "deleted_at": None,
            }}, upsert=True)
        tour = {
            "name": "Dạo quanh Quận 4", "description": "Tuyến tham quan dùng để trình diễn chức năng mua vé và nghe ngoại tuyến.",
            "poi_ids": [place["_id"] for place in places], "is_active": True,
            "is_purchasable": True, "price_amount": 99000, "version": 1,
            "preview_enabled": True, "preview_poi_ids": [places[0]["_id"]],
            "created_at": now, "updated_at": now,
        }
        await db["tours"].update_one({"_id": "release-demo-tour"}, {"$setOnInsert": tour}, upsert=True)
        print(f"Demo ready: {len(places)} places and 1 tour")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
