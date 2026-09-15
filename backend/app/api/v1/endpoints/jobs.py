import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.repositories.job_repo import job_repo
from app.repositories.content_repo import content_repo
from app.schemas.content_job import ContentJobCreate, ContentJobResponse, JobStatus
from app.services.job_worker import job_worker

router = APIRouter(prefix="/jobs", tags=["Async Content Jobs (TTS & Translate)"])


@router.post("", response_model=ContentJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: ContentJobCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Enqueue an asynchronous TTS or Translation job.
    Uses idempotency_key to prevent duplicate submissions.
    """
    content = await content_repo.get_by_id(job_in.input_content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Input content not found")

    idempotency_key = job_in.idempotency_key or f"{job_in.job_type}:{job_in.input_content_id}:{job_in.target_language_code or 'tts'}"
    
    # Check if job already exists with same idempotency_key
    existing = await job_repo.find_one({"idempotency_key": idempotency_key})
    if existing:
        return existing

    now = datetime.now(timezone.utc)
    job_doc = {
        "_id": str(uuid.uuid4()),
        "job_type": job_in.job_type,
        "input_content_id": job_in.input_content_id,
        "provider": job_in.provider or "edge-tts",
        "parameters": job_in.parameters,
        "target_language_code": job_in.target_language_code,
        "status": "queued",
        "attempts": 0,
        "max_attempts": 3,
        "idempotency_key": idempotency_key,
        "requested_by": current_user["_id"],
        "output_content_id": None,
        "output_audio_id": None,
        "error_message": None,
        "started_at": None,
        "finished_at": None,
        "next_retry_at": None,
        "created_at": now,
        "updated_at": now
    }
    await job_repo.insert_one(job_doc)
    return job_doc


@router.get("", response_model=List[ContentJobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    query = {}
    if status_filter:
        query["status"] = status_filter
    jobs = await job_repo.list(query=query, skip=skip, limit=limit, sort=[("created_at", -1)])
    return jobs


@router.get("/{job_id}", response_model=ContentJobResponse)
async def get_job(job_id: str):
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/worker/process-one", response_model=Optional[ContentJobResponse])
async def trigger_worker_step(
    current_user: dict = Depends(get_current_admin)
):
    """Manually triggers the worker to process the next queued job immediately."""
    result = await job_worker.process_single_job()
    return result
