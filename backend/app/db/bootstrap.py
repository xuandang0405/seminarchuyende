"""Production bootstrap seeds permissions, never demonstration accounts or POIs."""
import os
from datetime import datetime, timezone
from app.core.config import settings
from app.core.permissions import ROLES_DEFINITION
from app.core.security import get_password_hash
from app.db.collections import COLLECTION_ROLES, COLLECTION_ADMIN_USERS


async def bootstrap(db):
    from app.services.tts_service import VOICE_MAPPING
    names = {"vi": ("Vietnamese", "Tiếng Việt"), "en": ("English", "English"), "fr": ("French", "Français"),
             "ja": ("Japanese", "日本語"), "ko": ("Korean", "한국어"), "zh": ("Chinese", "中文")}
    for code, voice in VOICE_MAPPING.items():
        await db["languages"].update_one({"_id": code}, {"$setOnInsert": {"name": names[code][0],
            "native_name": names[code][1], "is_enabled": True, "voice_id": voice, "created_at": datetime.now(timezone.utc)}}, upsert=True)
    for name, role in ROLES_DEFINITION.items():
        await db[COLLECTION_ROLES].update_one({"name": name}, {"$setOnInsert": {"_id": "role_" + name, "name": name, **role}}, upsert=True)
    mode = settings.SUPERADMIN_BOOTSTRAP_MODE
    if mode not in ("disabled", "create"):
        raise RuntimeError("Invalid SUPERADMIN_BOOTSTRAP_MODE")
    if mode == "create" and not await db[COLLECTION_ADMIN_USERS].find_one({"role": "super_admin"}):
        if settings.SUPERADMIN_PASSWORD == "Admin@123456" or len(settings.SUPERADMIN_PASSWORD) < 12:
            raise RuntimeError("Bootstrap requires a new strong SUPERADMIN_PASSWORD")
        await db[COLLECTION_ADMIN_USERS].insert_one({"_id": "bootstrap_super_admin", "email": settings.SUPERADMIN_EMAIL.lower(),
            "role": "super_admin", "password_hash": get_password_hash(settings.SUPERADMIN_PASSWORD), "is_active": True,
            "is_verified": True, "auth_version": 1, "created_at": datetime.now(timezone.utc)})
