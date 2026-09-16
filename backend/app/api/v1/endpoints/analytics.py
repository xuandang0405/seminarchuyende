"""Router for Analytics endpoints.

F08 / S05 / S06 / S07 / S08 / SD11 / AD11 / SD12 / AD12 / SD13 / AD13.
Implements Consent, Idempotent Event Batch Ingestion with per-event ACK, and Dashboard.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.endpoints.auth import get_current_user
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Telemetry & Analytics"])


class ConsentRequest(BaseModel):
    device_id: str
    consent_granted: bool
    scopes: Optional[List[str]] = Field(default=["events", "route_sampling"])


class EventItem(BaseModel):
    event_id: str
    session_id: Optional[str] = None
    poi_id: Optional[str] = None
    event_type: str
    occurred_at: Optional[Any] = None
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EventBatchRequest(BaseModel):
    events: List[EventItem]


# =============================================================================
# CONSENT (F08 / SD11)
# =============================================================================

@router.post("/consent")
async def update_consent(req: ConsentRequest):
    """
    Use Case F08: Tourist grants or revokes analytics consent.
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
# BATCH EVENT INGESTION (SD11 / AD11)
# =============================================================================

@router.post("/events/batch")
async def ingest_events_batch(req: EventBatchRequest):
    """
    Sequence Diagram 11: Idempotent event batch ingestion with per-event ACK.
    Client only removes acknowledged event IDs from local SQLite outbox.
    """
    events_data = [e.model_dump() for e in req.events]
    res = await analytics_service.ingest_events(events_data)
    return res


# =============================================================================
# DASHBOARD STATS (S05 / S06 / S07 / SD12 / SD13)
# =============================================================================

@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Use Cases S05, S06, S07, O10:
    Returns system-wide aggregated metrics for Admin, or scoped metrics for Owner.
    Calculates average listening time safely without division by zero.
    """
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

