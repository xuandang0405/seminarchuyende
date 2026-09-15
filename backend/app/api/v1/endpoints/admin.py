from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.v1.endpoints.auth import get_current_admin
from app.repositories.base import BaseRepository
from app.repositories.owner_repo import owner_repo
from app.schemas.user import AdminUserResponse
from app.schemas.owner import OwnerSubmissionResponse, OwnerReviewAction

router = APIRouter(prefix="/admin", tags=["Admin Approval & Management"])
user_repo = BaseRepository("admin_users")


@router.get("/owners/pending", response_model=List[AdminUserResponse])
async def list_pending_owners(current_admin: dict = Depends(get_current_admin)):
    """Sequence Diagram 10: List all owners waiting for verification."""
    owners = await owner_repo.list_pending_owners()
    return owners


@router.post("/owners/{owner_id}/review", response_model=AdminUserResponse)
async def review_owner_registration(
    owner_id: str,
    review: OwnerReviewAction,
    current_admin: dict = Depends(get_current_admin)
):
    """Admin approves or rejects owner registration."""
    status_str = "approved" if review.action == "approve" else "rejected"
    updated = await owner_repo.update_owner_status(
        owner_id=owner_id,
        status=status_str,
        admin_notes=review.admin_notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Owner not found")
    return updated


@router.get("/submissions", response_model=List[OwnerSubmissionResponse])
async def list_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_admin: dict = Depends(get_current_admin)
):
    """List submissions from store owners waiting for content approval."""
    subs = await owner_repo.list_submissions(status=status_filter)
    return subs


@router.post("/submissions/{submission_id}/review", response_model=OwnerSubmissionResponse)
async def review_submission(
    submission_id: str,
    review: OwnerReviewAction,
    current_admin: dict = Depends(get_current_admin)
):
    """Sequence Diagram 10: Admin approves or rejects owner's submitted content."""
    status_str = "approved" if review.action == "approve" else "rejected"
    reviewed = await owner_repo.review_submission(
        submission_id=submission_id,
        status=status_str,
        admin_id=current_admin["_id"],
        admin_notes=review.admin_notes
    )
    if not reviewed:
        raise HTTPException(status_code=404, detail="Submission not found")
    return reviewed


@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(
    role: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    query = {}
    if role:
        query["role"] = role
    users = await user_repo.list(query=query, limit=100)
    return users
