import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.endpoints.auth import get_current_owner
from app.repositories.owner_repo import owner_repo
from app.repositories.poi_repo import poi_repo
from app.repositories.analytics_repo import analytics_repo
from app.schemas.poi import POIResponse, MenuItem
from app.schemas.owner import OwnerSubmissionCreate, OwnerSubmissionResponse

router = APIRouter(prefix="/owner", tags=["Store Owner Portal (Chủ quán)"])


@router.get("/my-pois", response_model=List[POIResponse])
async def get_my_pois(current_owner: dict = Depends(get_current_owner)):
    """List all POIs owned and managed by the current store owner."""
    pois = await poi_repo.find_by_owner(current_owner["_id"])
    return pois


@router.post("/submissions", response_model=OwnerSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_content_change(
    sub_in: OwnerSubmissionCreate,
    current_owner: dict = Depends(get_current_owner)
):
    """
    Sequence Diagram 09: Owner submits new POI or modification for Admin review.
    """
    if current_owner.get("owner_status") != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your owner account has not been approved by an administrator yet."
        )

    now = datetime.now(timezone.utc)
    sub_doc = {
        "_id": str(uuid.uuid4()),
        "owner_id": current_owner["_id"],
        "poi_id": sub_in.poi_id,
        "submission_type": sub_in.submission_type,
        "title": sub_in.title,
        "proposed_content": sub_in.proposed_content,
        "owner_notes": sub_in.owner_notes,
        "status": "pending",
        "admin_notes": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "created_at": now,
        "updated_at": now
    }
    await owner_repo.create_submission(sub_doc)
    return sub_doc


@router.get("/submissions", response_model=List[OwnerSubmissionResponse])
async def list_my_submissions(current_owner: dict = Depends(get_current_owner)):
    """View submission review status (pending, approved, rejected) and admin notes."""
    subs = await owner_repo.list_submissions(owner_id=current_owner["_id"])
    return subs


@router.post("/pois/{poi_id}/menu", response_model=POIResponse)
async def owner_update_menu(
    poi_id: str,
    item: MenuItem,
    current_owner: dict = Depends(get_current_owner)
):
    """Owner adds or updates a specialty dish on their store menu."""
    poi = await poi_repo.get_by_id(poi_id)
    if not poi or poi.get("owner_id") != current_owner["_id"]:
        raise HTTPException(status_code=403, detail="You do not own this POI")

    item_dict = item.model_dump()
    if not item_dict.get("id"):
        item_dict["id"] = str(uuid.uuid4())

    menu_list = poi.get("menu_items", [])
    menu_list.append(item_dict)

    updated = await poi_repo.update_by_id(poi_id, {
        "menu_items": menu_list,
        "updated_at": datetime.now(timezone.utc)
    })
    return updated


@router.get("/stats")
async def get_owner_stats(current_owner: dict = Depends(get_current_owner)):
    """Use Case O10: View playbacks and listening metrics for owner's POIs."""
    my_pois = await poi_repo.find_by_owner(current_owner["_id"])
    poi_ids = [p["_id"] for p in my_pois]

    # In production, aggregate specifically for these poi_ids
    return {
        "total_managed_pois": len(my_pois),
        "managed_pois": [{"id": p["_id"], "code": p["code"]} for p in my_pois],
        "message": "Owner analytics successfully fetched."
    }
