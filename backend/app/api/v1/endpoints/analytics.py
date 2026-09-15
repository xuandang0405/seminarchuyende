import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.endpoints.auth import get_current_admin
from app.repositories.analytics_repo import analytics_repo
from app.schemas.playback import (
    PlaybackCreate,
    PlaybackResponse,
    PlaybackBatchEventsRequest,
    PlaybackBatchEventsResult
)
from app.schemas.location_sample import LocationBatchIn
from app.schemas.analytics import AnalyticsDashboardResponse

router = APIRouter(prefix="/analytics", tags=["Telemetry & Analytics"])


@router.post("/playbacks", response_model=PlaybackResponse, status_code=status.HTTP_201_CREATED)
async def create_playback(playback_in: PlaybackCreate):
    """
    Register a new playback instance (triggered by GPS, QR, or manual tap).
    """
    now = datetime.now(timezone.utc)
    playback_id = str(uuid.uuid4())
    doc = {
        "_id": playback_id,
        "session_id": playback_in.session_id,
        "audio_asset_id": playback_in.audio_asset_id,
        "trigger_type": playback_in.trigger_type,
        "status": "pending",
        "listened_ms": 0,
        "last_event_seq": 0,
        "qr_code_id": playback_in.qr_code_id,
        "started_at": None,
        "ended_at": None,
        "created_at": now,
        "updated_at": now
    }
    await analytics_repo.insert_one(doc)
    return doc


@router.post("/playback-events", response_model=PlaybackBatchEventsResult)
async def ingest_playback_events(batch: PlaybackBatchEventsRequest):
    """
    Sequence Diagram 11: Batch telemetry synchronization with deduplication.
    Client transmits cached playback events. Server idempotently upserts using (playback_id, seq_no).
    """
    saved = 0
    duplicates = 0
    for ev in batch.events:
        is_new = await analytics_repo.upsert_playback_event(ev.model_dump())
        if is_new:
            saved += 1
        else:
            duplicates += 1

    return {
        "received_count": len(batch.events),
        "saved_count": saved,
        "duplicates_count": duplicates
    }


@router.post("/location-samples", status_code=status.HTTP_201_CREATED)
async def ingest_location_samples(batch: LocationBatchIn):
    """
    Ingest opt-in location points for tourist route tracing and heatmaps.
    """
    count = await analytics_repo.insert_location_samples([s.model_dump() for s in batch.samples])
    return {"received_count": len(batch.samples), "saved_count": count}


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def get_dashboard_metrics(current_admin: dict = Depends(get_current_admin)):
    """
    Sequence Diagram 13 / UseCases S05-S07:
    Admin dashboard metrics: total playbacks, total listening hours, top POIs.
    """
    stats = await analytics_repo.get_dashboard_stats()
    return stats
