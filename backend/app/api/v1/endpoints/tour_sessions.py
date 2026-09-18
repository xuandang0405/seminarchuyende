"""Router for Tour Sessions (tour_sessions).

Implements Section 10.3 / BR-TOUR-SESSION-01:
- Idempotent tour start with double-click / retry protection.
- Progress updates and state transitions.
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Header, HTTPException, status

from app.schemas.device_session import (
    TourSessionStartRequest,
    TourSessionPatchRequest,
    TourSessionResponse,
)
from app.services.session_service import session_service

router = APIRouter(prefix="/tour-sessions", tags=["Tour Sessions"])


@router.post("", response_model=TourSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_tour_session_endpoint(
    req: TourSessionStartRequest,
    cookie_token: Optional[str] = Cookie(None, alias="tourvoice_device_token"),
    header_token: Optional[str] = Header(None, alias="x-device-token"),
):
    """Starts a new tour session with idempotency_key deduplication."""
    token = header_token or cookie_token
    device_doc, _, _ = await session_service.bootstrap_device(device_token=token)
    device_id = device_doc["_id"]

    tour_session = await session_service.start_tour_session(
        idempotency_key=req.idempotency_key,
        tour_id=req.tour_id,
        visitor_session_id=req.visitor_session_id,
        device_id=device_id,
        start_poi_id=req.start_poi_id
    )

    return tour_session


@router.patch("/{tour_session_id}", response_model=TourSessionResponse)
async def patch_tour_session_endpoint(
    tour_session_id: str,
    req: TourSessionPatchRequest,
    cookie_token: Optional[str] = Cookie(None, alias="tourvoice_device_token"),
    header_token: Optional[str] = Header(None, alias="x-device-token"),
):
    """Updates progress, visited POIs or state transitions with device ownership check."""
    token = header_token or cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu device token để cập nhật phiên tour."
        )

    device_doc = await session_service.verify_device_token(token)
    if not device_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device token không hợp lệ."
        )

    status_val = req.status.value if req.status and hasattr(req.status, "value") else (str(req.status) if req.status else None)

    updated = await session_service.update_tour_progress(
        tour_session_id=tour_session_id,
        device_id=device_doc["_id"],
        last_poi_id=req.last_poi_id,
        completed_poi_ids=req.completed_poi_ids,
        progress_percentage=req.progress_percentage,
        status=status_val
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên tour không tồn tại hoặc không thuộc quyền sở hữu của thiết bị."
        )

    return updated
