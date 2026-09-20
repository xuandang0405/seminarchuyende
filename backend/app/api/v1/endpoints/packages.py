"""Router for Offline Data Packages endpoints.

O05 / T12 / F01-F06.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_admin, get_current_user
from app.services.offline_package_service import offline_package_service
from app.repositories.tour_repo import tour_repo
from app.repositories.entitlement_repo import entitlement_repo

router = APIRouter(prefix="/packages", tags=["Offline Data Packages"])


class PackageBuildRequest(BaseModel):
    language_code: str = "vi"
    package_name: Optional[str] = "Goi-Offline-Di-Tich-Am-Thuc-Q4-Full"


@router.get("", response_model=List[Dict[str, Any]])
async def list_packages():
    """Lists all available offline packages."""
    return await offline_package_service.list_packages()


@router.get("/tours/{tour_id}")
async def get_tour_package(
    tour_id: str,
    language_code: str = Query("vi", description="Requested language code"),
    current_user: dict = Depends(get_current_user)
):
    """Fetches or builds an offline package for a specific tour. Requires active tour entitlement if tour is paid."""
    tour = await tour_repo.get_public_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tour.")

    is_paid = tour.get("is_purchasable") or tour.get("is_paid")
    if is_paid and current_user.get("role") not in ("admin", "super_admin"):
        ent = await entitlement_repo.get_entitlement(user_id=current_user["_id"], tour_id=tour_id)
        if not ent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Yêu cầu mua vé tour để tải gói dữ liệu ngoại tuyến."
            )

    pkg = await offline_package_service.generate_tour_package(tour_id=tour_id, language_code=language_code)
    if not pkg:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tour.")
    return pkg


@router.get("/{package_id}/manifest")
async def get_package_manifest(package_id: str):
    """Fetches raw JSON manifest of an offline package."""
    pkg = await offline_package_service.get_package_by_id(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Gói offline không tồn tại.")
    return pkg.get("manifest", pkg)


@router.post("/build")
async def build_offline_package(
    req: PackageBuildRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Admin builds a verified offline package with SHA-256 checksums."""
    pkg = await offline_package_service.build_full_package(
        language_code=req.language_code,
        package_name=req.package_name
    )
    return {
        "status": "success",
        "message": "Đã tạo gói đóng gói offline thành công với mã băm SHA-256 an toàn.",
        "package": pkg
    }


from app.api.v1.endpoints.auth import get_current_user


@router.post("/tours/{tour_id}/offline-pack")
async def download_tour_offline_pack_with_license(
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

