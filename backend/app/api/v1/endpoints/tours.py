"""Router for Tour endpoints (Public & Admin).

T12 / T13 / C15 / SD14 / AD14.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_admin
from app.services.tour_service import tour_service

router = APIRouter(prefix="/tours", tags=["Tours"])


class TourCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    description: Optional[str] = ""
    localizations: Optional[Dict[str, Any]] = Field(default_factory=dict)
    poi_ids: List[str] = Field(..., min_length=1, description="Ordered list of POI IDs")
    is_active: bool = Field(default=True)


class TourUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    localizations: Optional[Dict[str, Any]] = None
    poi_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None
    expected_version: Optional[int] = None


@router.get("")
async def list_tours(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Use Case T12: List public tours."""
    return await tour_service.list_public_tours(skip=skip, limit=limit)


@router.get("/{tour_id}")
async def get_tour(
    tour_id: str,
    lang: str = Query("vi")
):
    """Use Case T12: View tour detail with ordered stops."""
    tour = await tour_service.get_tour_detail(tour_id=tour_id, lang=lang)
    if not tour:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour không tồn tại.")
    return tour


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tour(
    req: TourCreateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C15: Admin creates tour."""
    res = await tour_service.create_tour(req.model_dump(), created_by=current_admin["_id"])
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res["tour"]


@router.patch("/{tour_id}")
async def update_tour(
    tour_id: str,
    req: TourUpdateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C15: Admin updates tour and reorders POIs."""
    data = req.model_dump(exclude_unset=True)
    expected_version = data.pop("expected_version", None)
    res = await tour_service.update_tour(tour_id, data, expected_version)
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.get("error"))
    return res["tour"]


@router.delete("/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tour(
    tour_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C15: Admin soft deletes tour."""
    success = await tour_service.delete_tour(tour_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour không tồn tại.")
    return None
