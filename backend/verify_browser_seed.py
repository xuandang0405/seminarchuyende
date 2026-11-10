"""Seed a disposable browser-check DB; never accepts production database names."""
import asyncio
import os
from pathlib import Path
from pymongo import AsyncMongoClient
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.bootstrap import bootstrap
from app.services.audio_metadata import mp3_duration_ms
from app.db.collections import COLLECTION_POI

async def seed_browser_fixtures(db):
    assert settings.APP_ENV == "test" and settings.DATABASE_NAME.startswith("tourvoice_review_")
    for uid, role in [("review-admin", "admin"), ("review-user", "user")]:
        await db["admin_users"].update_one({"_id": uid}, {"$set": {"email": uid + "@example.org",
            "full_name": uid, "role": role, "is_active": True, "is_verified": True, "auth_version": 1,
            "password_hash": get_password_hash("ReviewPass@2026")}}, upsert=True)
    source = None
    configured = os.environ.get("BROWSER_MP3_FIXTURE")
    candidates = [Path(configured)] if configured else Path("storage/audio").glob("*.mp3")
    for candidate in candidates:
        try:
            mp3_duration_ms(candidate.read_bytes())
            source = candidate.read_bytes()
            break
        except Exception:
            continue
    if source is None:
        raise RuntimeError("Provide one real MP3 in storage/audio for the browser audio fixture")
    target = Path(settings.MEDIA_STORAGE_DIR) / "audio/review-fixture.mp3"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)
    poi = {"_id": "review-poi", "name": "Điểm kiểm tra TourVoice", "description": "Nội dung mẫu chỉ dùng kiểm tra phần mềm.",
        "location": {"type": "Point", "coordinates": [106.7042, 10.7635]}, "is_active": True,
        "category": "historical", "images": [], "address": "Quận 4", "version": 1, "content_version": 1,
        "trigger_radius": 30, "audio_priority": 50, "deleted_at": None}
    await db[COLLECTION_POI].update_one({"_id": poi["_id"]}, {"$set": poi}, upsert=True)
    await db[COLLECTION_POI].update_one({"_id": "review-markup"}, {"$set": {
        **poi, "_id": "review-markup", "name": '<img src=x onerror="window.__reviewPopupExecuted=1">',
        "location": {"type": "Point", "coordinates": [106.708, 10.759]},
    }}, upsert=True)
    for lang in ["vi", "en"]:
        await db["poi_localizations"].update_one({"poi_id": poi["_id"], "lang": lang}, {"$set": {
            "poi_id": poi["_id"], "lang": lang, "name": poi["name"], "description": poi["description"],
            "audio_storage_key": "audio/review-fixture.mp3", "audio_url": "/storage/audio/review-fixture.mp3",
            "audio_status": "ready", "translation_status": "ready", "source_version": 1,
            "audio_duration_ms": mp3_duration_ms(source)}}, upsert=True)
    await db["tours"].update_one({"_id": "review-tour"}, {"$set": {
        "_id": "review-tour", "name": "Tour kiểm tra", "description": "Dữ liệu kiểm thử", "poi_ids": ["review-poi"],
        "is_active": True, "is_purchasable": True, "price_amount": 99000, "version": 1,
        "preview_enabled": True, "preview_poi_ids": ["review-poi"]}}, upsert=True)
    for lang in ["vi", "en"]:
        await db["poi_localizations"].update_one({"poi_id": "review-markup", "lang": lang}, {"$set": {
            "poi_id": "review-markup", "lang": lang, "name": '<img src=x onerror="window.__reviewPopupExecuted=1">',
            "description": "Dữ liệu kiểm tra bảo mật.", "audio_storage_key": "audio/review-fixture.mp3",
            "audio_url": "/storage/audio/review-fixture.mp3", "audio_status": "ready",
            "translation_status": "ready", "source_version": 1, "audio_duration_ms": mp3_duration_ms(source),
        }}, upsert=True)
    await db["tours"].update_one({"_id": "review-free-tour"}, {"$set": {
        "name": "Tour miễn phí mẫu", "poi_ids": ["review-markup"], "is_active": True, "price_amount": 0,
    }}, upsert=True)
    print("PASS: disposable browser fixtures created (MP3 fixture is not a language-quality evaluation)")

async def main():
    assert settings.APP_ENV == "test" and settings.DATABASE_NAME.startswith("tourvoice_review_")
    client = AsyncMongoClient(settings.mongodb_connection_string, tz_aware=True)
    try:
        db = client[settings.DATABASE_NAME]
        await bootstrap(db)
        await seed_browser_fixtures(db)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
