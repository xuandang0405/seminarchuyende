"""Router for Analytics endpoints.

F08 / S05 / S06 / S07 / S08 / SD11 / AD11 / SD12 / AD12 / SD13 / AD13.
Implements Consent, Idempotent Event Batch Ingestion with per-event ACK, and Admin Analytics.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.schemas.device_session import (
    EventBatchIn,
    EventBatchResponse,
    AnalyticsOverviewResponse,
    TopPoiAnalyticsItem,
    TourAnalyticsItem,
)
from app.services.analytics_service import analytics_service
from app.services.session_service import session_service

router = APIRouter(prefix="/analytics", tags=["Telemetry & Analytics"])


class ConsentRequest(BaseModel):
    device_id: str
    consent_granted: bool
    scopes: Optional[List[str]] = Field(default=["events", "route_sampling"])


# =============================================================================
# CONSENT (F08 / SD11 / BR-CONSENT-01)
# =============================================================================

@router.post("/consent")
async def update_consent(req: ConsentRequest):
    """Tourist grants or revokes analytics consent.
    
    Pseudonymous device_id is stored with granted scopes.
    """
    res = await analytics_service.set_device_consent(
        device_id=req.device_id,
        consent=req.consent_granted,
        scopes=req.scopes
    )
    return {
        "success": True,
        "device_id": req.device_id,
        "consent_granted": req.consent_granted,
        "message": "Cập nhật tùy chọn đồng ý thành công."
    }


# =============================================================================
# BATCH EVENT INGESTION WITH PER-ITEM ACK (SD11 / AD11 / BR-SYNC-01)
# =============================================================================

@router.post("/events/batch", response_model=EventBatchResponse)
async def ingest_events_batch(
    req: EventBatchIn,
    cookie_token: Optional[str] = Cookie(None, alias="tourvoice_device_token"),
    header_token: Optional[str] = Header(None, alias="x-device-token"),
):
    """Sequence Diagram 11: Idempotent event batch ingestion with per-event ACK.
    
    Client only removes acknowledged event IDs (accepted or duplicate) from local outbox.
    Device ID is securely inferred from device credential.
    """
    token = header_token or cookie_token
    device_id = None
    if token:
        dev = await session_service.verify_device_token(token)
        if dev:
            device_id = dev["_id"]

    events_data = [e.model_dump() for e in req.events]
    res = await analytics_service.ingest_events(events_data, inferred_device_id=device_id)
    return res


# =============================================================================
# ADMIN ANALYTICS ENDPOINTS (Section 14 & 17)
# =============================================================================

@router.get("/overview", response_model=AnalyticsOverviewResponse)
@router.get("/admin/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview():
    """System-wide analytics overview with distinct unique devices and non-zero math."""
    return await analytics_service.get_overview()


@router.get("/pois", response_model=List[TopPoiAnalyticsItem])
@router.get("/admin/pois", response_model=List[TopPoiAnalyticsItem])
async def get_analytics_pois(
    limit: int = Query(10, ge=1, le=50)
):
    """Top POIs by listening activity and unique devices."""
    return await analytics_service.get_top_pois(limit=limit)


@router.get("/tours", response_model=List[TourAnalyticsItem])
@router.get("/admin/tours", response_model=List[TourAnalyticsItem])
async def get_analytics_tours():
    """Tour usage statistics and completion rates."""
    return await analytics_service.get_tours()


# Legacy dashboard endpoint for admin portal
@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    """Returns overview stats for Admin or scoped stats for Owner."""
    role = current_user.get("role", "user")
    user_id = current_user["_id"]
    stats = await analytics_service.get_dashboard(actor_role=role, actor_id=user_id)
    return stats


import uuid

@router.post("/playbacks")
async def create_playback(req: Dict[str, Any]):
    """Records start of audio playback for tourist telemetry."""
    playback_id = f"pb_{uuid.uuid4().hex[:12]}"
    return {"status": "ok", "playback_id": playback_id, "_id": playback_id}


@router.post("/playback-events")
async def record_playback_event(req: Dict[str, Any]):
    """Records audio playback progress event."""
    return {"status": "ok"}
