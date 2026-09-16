"""Router for Owner Portal endpoints.

O02 / O03 / O04 / O05 / O06 / O07 / O08 / O10 / SD09 / AD09.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_owner
from app.services.owner_service import owner_service
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/owner", tags=["Store Owner Portal (Chủ quán)"])


class SubmissionCreateRequest(BaseModel):
    action: str = Field("create", description="'create' or 'update'")
    poi_id: Optional[str] = None
    payload: Dict[str, Any]
    request_key: Optional[str] = None


@router.get("/registration")
async def get_registration_status(current_owner: dict = Depends(get_current_owner)):
    """Use Case O02: Check owner verification status."""
    reg = await owner_service.get_registration_status(current_owner["_id"])
    return {
        "user_id": current_owner["_id"],
        "is_poi_owner_verified": current_owner.get("is_poi_owner_verified", False),
        "registration": reg
    }


@router.get("/pois")
async def get_my_pois(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_owner: dict = Depends(get_current_owner)
):
    """Use Case O03: View list of POIs owned by current owner."""
    pois = await owner_service.get_my_pois(owner_id=current_owner["_id"], skip=skip, limit=limit)
    return pois


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def create_submission(
    req: SubmissionCreateRequest,
    current_owner: dict = Depends(get_current_owner)
):
    """Use Case O04, O05: Submit draft POI or modification for Admin review."""
    res = await owner_service.submit_content(
        owner_id=current_owner["_id"],
        action=req.action,
        payload=req.payload,
        poi_id=req.poi_id,
        request_key=req.request_key
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res


@router.get("/submissions")
async def list_my_submissions(current_owner: dict = Depends(get_current_owner)):
    """Use Case O06: View owner's submissions and admin feedback."""
    subs = await owner_service.list_my_submissions(owner_id=current_owner["_id"])
    return subs


@router.get("/notifications")
async def list_my_notifications(current_owner: dict = Depends(get_current_owner)):
    """Use Case O07: View in-app notifications."""
    notifs = await owner_service.list_my_notifications(owner_id=current_owner["_id"])
    return notifs


@router.patch("/notifications/{notif_id}/read")
async def mark_notification_as_read(
    notif_id: str,
    current_owner: dict = Depends(get_current_owner)
):
    """Use Case O08: Mark notification as read."""
    success = await owner_service.mark_notification_read(notif_id=notif_id, owner_id=current_owner["_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thông báo không tồn tại.")
    return {"success": True, "message": "Đã đánh dấu đã đọc."}


@router.get("/analytics")
async def get_owner_analytics(current_owner: dict = Depends(get_current_owner)):
    """Use Case O10: View listening statistics for owned POIs."""
    stats = await analytics_service.get_dashboard(
        actor_role=current_owner.get("role", "poi_owner"),
        actor_id=current_owner["_id"]
    )
    return stats
