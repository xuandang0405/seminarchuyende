import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.v1.endpoints.auth import get_current_admin
from app.repositories.base import BaseRepository
from app.repositories.poi_repo import poi_repo
from app.repositories.content_repo import content_repo
from app.repositories.audio_repo import audio_repo
from app.schemas.qr_code import QRCodeCreate, QRCodeResponse, QRResolveResponse

router = APIRouter(prefix="/qr", tags=["QR Codes"])
qr_repo = BaseRepository("qr_codes")


@router.post("", response_model=QRCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_qr_code(
    qr_in: QRCodeCreate,
    current_user: dict = Depends(get_current_admin)
):
    poi = await poi_repo.get_by_id(qr_in.poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")

    qr_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "_id": qr_id,
        "poi_id": qr_in.poi_id,
        "label": qr_in.label,
        "is_active": qr_in.is_active,
        "created_at": now,
        "updated_at": now
    }
    await qr_repo.insert_one(doc)
    return {**doc, "qr_uri": f"tourguide://qr/{qr_id}"}


@router.get("/poi/{poi_id}", response_model=List[QRCodeResponse])
async def list_qr_for_poi(poi_id: str):
    docs = await qr_repo.list(query={"poi_id": poi_id, "is_active": True})
    return [{**d, "qr_uri": f"tourguide://qr/{d['_id']}"} for d in docs]


@router.get("/resolve/{qr_id}", response_model=QRResolveResponse)
async def resolve_qr_code(
    qr_id: str,
    language_code: str = Query("vi")
):
    """
    Sequence Diagram 05: Tourist scans QR code.
    Resolves QR ID to POI, active localized content, and matching audio stream.
    """
    qr_doc = await qr_repo.get_by_id(qr_id)
    if not qr_doc or not qr_doc.get("is_active", True):
        raise HTTPException(status_code=404, detail="QR Code is inactive or invalid")

    poi = await poi_repo.get_by_id(qr_doc["poi_id"])
    if not poi:
        raise HTTPException(status_code=404, detail="Associated POI not found")

    contents = await content_repo.find_by_poi_and_lang(poi["_id"], language_code, status="approved")
    content_doc = contents[0] if contents else None
    if not content_doc:
        # Fallback to Vietnamese
        fb = await content_repo.find_by_poi_and_lang(poi["_id"], "vi", status="approved")
        content_doc = fb[0] if fb else None

    audio_doc = None
    if content_doc:
        audios = await audio_repo.find_by_content_id(content_doc["_id"])
        if audios:
            audio_doc = audios[0]
            audio_doc["stream_url"] = f"/api/v1/audio/{audio_doc['storage_key']}/stream"

    return {
        "qr_id": qr_id,
        "poi_id": poi["_id"],
        "poi": poi,
        "content": content_doc,
        "audio": audio_doc
    }
