"""Shared fixed-window limiter, atomic across API workers."""
import hashlib
import time
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.core.database import get_database


async def enforce_rate_limit(key: str, maximum: int, window_seconds: int):
    bucket = int(time.time()) // window_seconds
    identifier = hashlib.sha256(f"{key}:{bucket}".encode()).hexdigest()
    now = datetime.now(timezone.utc)
    col = get_database()["request_rate_limits"]
    record = await col.find_one_and_update({"_id": identifier},
        {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now + timedelta(seconds=window_seconds * 2)}},
        upsert=True, return_document=True)
    if record["count"] > maximum:
        raise HTTPException(429, "Quá nhiều yêu cầu. Vui lòng thử lại sau.", headers={"Retry-After": str(window_seconds)})
