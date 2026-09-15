import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.repositories.poi_repo import poi_repo
from app.repositories.content_repo import content_repo
from app.repositories.audio_repo import audio_repo
from app.schemas.poi_content import (
    POIContentCreate,
    POIContentUpdate,
    POIContentResponse
)

router = APIRouter(prefix="/pois/{poi_id}/contents", tags=["POI Multilingual Contents"])


@router.get("", response_model=List[POIContentResponse])
async def list_poi_contents(
    poi_id: str,
    language_code: Optional[str] = None
):
    query = {"poi_id": poi_id}
    if language_code:
        query["language_code"] = language_code
    contents = await content_repo.list(query=query, limit=50, sort=[("version", -1)])
    return contents


@router.get("/{language_code}/active", response_model=Optional[POIContentResponse])
async def get_active_poi_content(
    poi_id: str,
    language_code: str
):
    """Returns the currently approved/published content for the specified language."""
    contents = await content_repo.find_by_poi_and_lang(poi_id, language_code, status="approved")
    if not contents:
        # Fallback to Vietnamese if not found
        fallback = await content_repo.find_by_poi_and_lang(poi_id, "vi", status="approved")
        if fallback:
            return fallback[0]
        return None
    return contents[0]


@router.post("", response_model=POIContentResponse, status_code=status.HTTP_201_CREATED)
async def create_poi_content(
    poi_id: str,
    content_in: POIContentCreate,
    current_user: dict = Depends(get_current_user)
):
    poi = await poi_repo.get_by_id(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")

    role = current_user.get("role")
    if role not in ("admin", "super_admin") and poi.get("owner_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to add content to this POI")

    latest_version = await content_repo.get_latest_version_number(poi_id, content_in.language_code)
    now = datetime.now(timezone.utc)

    # Admins can create already approved content; owners create draft
    status_val = "approved" if role in ("admin", "super_admin") else "draft"
    reviewed_at = now if status_val == "approved" else None

    content_doc = {
        "_id": str(uuid.uuid4()),
        "poi_id": poi_id,
        "language_code": content_in.language_code,
        "version": latest_version + 1,
        "title": content_in.title,
        "description": content_in.description or "",
        "narration_text": content_in.narration_text,
        "review_status": status_val,
        "source_content_id": content_in.source_content_id,
        "reviewed_at": reviewed_at,
        "created_by": current_user["_id"],
        "created_at": now,
        "updated_at": now
    }

    await content_repo.insert_one(content_doc)
    return content_doc


@router.put("/{content_id}", response_model=POIContentResponse)
async def update_poi_content(
    poi_id: str,
    content_id: str,
    content_in: POIContentUpdate,
    current_user: dict = Depends(get_current_user)
):
    existing = await content_repo.get_by_id(content_id)
    if not existing or existing.get("poi_id") != poi_id:
        raise HTTPException(status_code=404, detail="Content not found")

    update_data = {k: v for k, v in content_in.model_dump(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)

    updated = await content_repo.update_by_id(content_id, update_data)
    return updated


@router.post("/{content_id}/approve", response_model=POIContentResponse)
async def approve_content(
    poi_id: str,
    content_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Admin approves a content draft."""
    content = await content_repo.get_by_id(content_id)
    if not content or content.get("poi_id") != poi_id:
        raise HTTPException(status_code=404, detail="Content not found")

    updated = await content_repo.approve_content(content_id)
    return updated


@router.post("/{content_id}/publish", response_model=dict)
async def publish_content(
    poi_id: str,
    content_id: str,
    audio_asset_id: Optional[str] = None,
    current_user: dict = Depends(get_current_admin)
):
    """Publishes approved content and audio to POI's published_contents map."""
    content = await content_repo.get_by_id(content_id)
    if not content or content.get("poi_id") != poi_id:
        raise HTTPException(status_code=404, detail="Content not found")

    if content.get("review_status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved content can be published")

    # If audio_asset_id not provided, find latest audio for this content
    final_audio_id = audio_asset_id
    if not final_audio_id:
        audios = await audio_repo.find_by_content_id(content_id)
        if audios:
            final_audio_id = audios[0]["_id"]
        else:
            final_audio_id = str(uuid.uuid4())  # Placeholder until audio is generated

    updated_poi = await poi_repo.update_published_content(
        poi_id=poi_id,
        language_code=content["language_code"],
        content_id=content_id,
        audio_asset_id=final_audio_id,
        published_by=current_user["_id"]
    )
    return {"message": "Content published successfully", "poi": updated_poi}
