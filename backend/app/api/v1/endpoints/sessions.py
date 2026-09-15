import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from app.repositories.base import BaseRepository
from app.schemas.visit_session import VisitSessionCreate, VisitSessionResponse

router = APIRouter(prefix="/sessions", tags=["Visit Sessions"])
session_repo = BaseRepository("visit_sessions")


@router.post("", response_model=VisitSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_visit_session(session_in: VisitSessionCreate):
    """
    Start a visit session (either free exploration or following a curated tour).
    """
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())
    doc = {
        "_id": session_id,
        "initial_language_code": session_in.initial_language_code,
        "tour_id": session_in.tour_id,
        "started_at": now,
        "ended_at": None,
        "created_at": now,
        "updated_at": now
    }
    await session_repo.insert_one(doc)
    return doc


@router.post("/{session_id}/end", response_model=VisitSessionResponse)
async def end_visit_session(session_id: str):
    """
    End a visit session.
    """
    now = datetime.now(timezone.utc)
    updated = await session_repo.update_by_id(session_id, {"ended_at": now, "updated_at": now})
    if not updated:
        raise HTTPException(status_code=404, detail="Visit session not found")
    return updated


@router.get("/{session_id}", response_model=VisitSessionResponse)
async def get_visit_session(session_id: str):
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Visit session not found")
    return session
