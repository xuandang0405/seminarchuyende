"""Router for QR Code endpoints (Public Resolution & Admin Management).

T11 / C16 / SD05 / AD05.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.endpoints.auth import get_current_admin
from app.services.qr_service import qr_service

router = APIRouter(prefix="/qr", tags=["QR Codes"])


class QRCreateRequest(BaseModel):
    poi_id: Optional[str] = None
    tour_id: Optional[str] = None
    target_type: Optional[str] = "poi"
    code: str = Field(..., min_length=3, max_length=50)
    location_description: Optional[str] = None


# =============================================================================
# PUBLIC RESOLUTION (T11 / SD05 / AD05)
# =============================================================================

@router.get("/poi/{poi_id}")
async def list_qr_for_poi(poi_id: str):
    """Lists all QR codes generated for a POI."""
    from app.repositories.qr_repo import qr_repo
    return await qr_repo.find_by_poi(poi_id)


@router.get("/{code}")
async def resolve_qr_code(code: str):
    """
    Use Case T11: Scan QR code to listen to POI or Tour narration directly without GPS.
    Resolves opaque QR code to public Tour or POI info.
    """
    res = await qr_service.resolve_qr_code(code)
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=res.get("error"))
    return res


# =============================================================================
# ADMIN MANAGEMENT (C16)
# =============================================================================

@router.get("", response_model=List[Dict[str, Any]])
async def list_qr_codes(
    limit: int = 100,
    skip: int = 0,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C16: Admin lists all QR codes with associated POI / Tour details."""
    return await qr_service.list_qrs(limit=limit, skip=skip)


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def create_qr_code(
    req: QRCreateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C16: Admin generates a new QR code for a POI or Tour."""
    res = await qr_service.create_qr_code(
        poi_id=req.poi_id,
        tour_id=req.tour_id,
        target_type=req.target_type,
        code=req.code,
        created_by=current_admin["_id"],
        location_description=req.location_description
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res["qr"]


@router.post("/{qr_id}/activate")
async def activate_qr_code(
    qr_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C16: Admin activates / re-enables a deactivated QR code."""
    success = await qr_service.activate_qr_code(qr_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mã QR không tồn tại.")
    return {"success": True, "message": "Mã QR đã được kích hoạt lại."}


@router.post("/{qr_id}/deactivate")
async def deactivate_qr_code(
    qr_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C16: Admin deactivates a QR code."""
    success = await qr_service.deactivate_qr_code(qr_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mã QR không tồn tại.")
    return {"success": True, "message": "Mã QR đã được vô hiệu hóa."}


@router.delete("/{qr_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_qr_code(
    qr_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Use Case C16: Admin deletes a QR code permanently."""
    success = await qr_service.delete_qr_code(qr_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mã QR không tồn tại.")
    return None
