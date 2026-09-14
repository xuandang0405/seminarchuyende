from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_admin
from app.schemas.language import LanguageCreate, LanguageResponse

router = APIRouter(prefix="/languages", tags=["Languages"])


@router.get("", response_model=List[LanguageResponse])
async def list_languages():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    cursor = db["languages"].find({"is_enabled": True})
    languages = await cursor.to_list(length=100)
    # Map _id to code
    for lang in languages:
        lang["code"] = lang["_id"]
    return languages


@router.post("", response_model=LanguageResponse, status_code=status.HTTP_201_CREATED)
async def create_language(
    lang_in: LanguageCreate,
    current_user: dict = Depends(get_current_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    existing = await db["languages"].find_one({"_id": lang_in.code.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{lang_in.code}' already exists"
        )

    now = datetime.now(timezone.utc)
    new_lang = {
        "_id": lang_in.code.lower(),
        "name": lang_in.name,
        "native_name": lang_in.native_name,
        "is_enabled": lang_in.is_enabled,
        "created_at": now,
        "updated_at": now
    }

    await db["languages"].insert_one(new_lang)
    new_lang["code"] = new_lang["_id"]
    return new_lang
