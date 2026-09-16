"""Router for Admin Moderation & Management endpoints:
- C06: Duyệt đăng ký chủ quán
- C07: Duyệt đề xuất nội dung POI
- S01: Quản lý người dùng
- S04: Xem nhật ký audit logs
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_admin
from app.services.moderation_service import moderation_service
from app.repositories.auth_repo import auth_repo
from app.repositories.base import BaseRepository
from app.db.collections import COLLECTION_AUDIT_LOGS

router = APIRouter(prefix="/admin", tags=["Admin Moderation & Management"])
audit_repo = BaseRepository(COLLECTION_AUDIT_LOGS)


class ReviewAction(BaseModel):
    decision: str = Field(..., description="'approved' or 'rejected'")
    admin_note: Optional[str] = None
    expected_version: Optional[int] = None


# =============================================================================
# MODERATION: OWNER REGISTRATIONS (C06 / SD10 / AD10)
# =============================================================================

@router.get("/moderation/registrations")
@router.get("/owners/pending")
async def list_pending_registrations(current_admin: dict = Depends(get_current_admin)):
    """Use Case C06: List pending owner registrations."""
    return await moderation_service.list_pending_registrations()


@router.post("/moderation/registrations/{registration_id}")
@router.post("/owners/{registration_id}/review")
async def review_owner_registration(
    registration_id: str,
    action: ReviewAction,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C06: Admin approves or rejects owner registration."""
    res = await moderation_service.review_registration(
        registration_id=registration_id,
        decision=action.decision,
        admin_id=current_admin["_id"],
        admin_note=action.admin_note,
        expected_version=action.expected_version
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res


# =============================================================================
# MODERATION: POI SUBMISSIONS (C07 / SD10 / AD10)
# =============================================================================

@router.get("/moderation/submissions")
@router.get("/submissions")
async def list_pending_submissions(current_admin: dict = Depends(get_current_admin)):
    """Use Case C07: List pending POI content submissions."""
    return await moderation_service.list_pending_submissions()


@router.post("/moderation/submissions/{submission_id}")
@router.post("/submissions/{submission_id}/review")
async def review_poi_submission(
    submission_id: str,
    action: ReviewAction,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C07: Admin approves or rejects owner's submitted content."""
    res = await moderation_service.review_submission(
        submission_id=submission_id,
        decision=action.decision,
        admin_id=current_admin["_id"],
        admin_note=action.admin_note,
        expected_version=action.expected_version
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res


# =============================================================================
# USER MANAGEMENT (S01)
# =============================================================================

@router.get("/users")
async def list_users(
    role: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case S01: List users."""
    query = {}
    if role:
        query["role"] = role
    users = await auth_repo.list(query=query, skip=skip, limit=limit)
    return [
        {
            "id": u["_id"],
            "email": u["email"],
            "full_name": u.get("full_name"),
            "role": u.get("role"),
            "is_active": u.get("is_active", True),
            "is_verified": u.get("is_verified", False),
            "is_poi_owner_verified": u.get("is_poi_owner_verified", False),
            "created_at": u.get("created_at"),
        }
        for u in users
    ]


# =============================================================================
# AUDIT LOGS (S04)
# =============================================================================

@router.get("/audit-logs")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case S04: View audit logs from audit_logs collection."""
    logs = await audit_repo.list(skip=skip, limit=limit, sort=[("timestamp", -1)])
    return logs
