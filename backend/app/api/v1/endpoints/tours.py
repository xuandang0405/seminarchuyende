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
    code: Optional[str] = None
    name: str = Field(..., min_length=2)
    description: Optional[str] = ""
    localizations: Optional[Dict[str, Any]] = Field(default_factory=dict)
    poi_ids: List[str] = Field(..., min_length=1, description="Ordered list of POI IDs")
    price_amount: int = Field(default=0, ge=0)
    price_vnd: Optional[int] = Field(default=None, ge=0)
    currency: str = Field(default="VND")
    is_paid: Optional[bool] = None
    is_purchasable: bool = Field(default=True)
    is_active: bool = Field(default=True)


class TourUpdateRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    localizations: Optional[Dict[str, Any]] = None
    poi_ids: Optional[List[str]] = None
    price_amount: Optional[int] = Field(None, ge=0)
    price_vnd: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = None
    is_paid: Optional[bool] = None
    is_purchasable: Optional[bool] = None
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
@router.put("/{tour_id}")
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


from app.schemas.tour import TourPricingUpdateRequest
from app.repositories.tour_repo import tour_repo


@router.put("/{tour_id}/pricing")
async def update_tour_pricing_endpoint(
    tour_id: str,
    req: TourPricingUpdateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """C15 / Section 10: Admin configures tour pricing, purchasable status, and preview settings."""
    updated = await tour_repo.update_tour_pricing(
        tour_id=tour_id,
        price_amount=req.price_amount,
        currency=req.currency,
        is_purchasable=req.is_purchasable,
        preview_enabled=req.preview_enabled,
        preview_poi_ids=req.preview_poi_ids
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour không tồn tại.")
    return {
        "success": True,
        "message": "Cập nhật giá và trạng thái mở bán thành công.",
        "tour": updated
    }


from app.services.offline_package_service import offline_package_service
from app.api.v1.endpoints.auth import get_current_user


@router.post("/{tour_id}/offline-pack")
async def download_tour_offline_pack_endpoint(
    tour_id: str,
    language_code: str = Query("vi"),
    current_user: dict = Depends(get_current_user)
):
    """Section 8 & 10 (F02 / BR-PAY-08): Downloads verified offline pack with 7-day signed offline license.
    Strictly requires user to hold an active entitlement for this tour.
    """
    return await offline_package_service.generate_tour_offline_pack_with_license(
        user_id=current_user["_id"],
        tour_id=tour_id,
        language_code=language_code
    )


