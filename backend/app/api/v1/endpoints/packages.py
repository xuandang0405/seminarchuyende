"""Router for Offline Data Packages endpoints.

O05 / T12 / F01-F06.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_admin, get_current_user
from app.services.offline_package_service import offline_package_service

router = APIRouter(prefix="/packages", tags=["Offline Data Packages"])


class PackageBuildRequest(BaseModel):
    language_code: str = "vi"
    package_name: Optional[str] = "Goi-Offline-Di-Tich-Am-Thuc-Q4-Full"


@router.get("", response_model=List[Dict[str, Any]])
async def list_packages(_admin=Depends(get_current_admin)):
    """Lists all available offline packages."""
    return await offline_package_service.list_packages()


@router.get("/tours/{tour_id}")
async def get_tour_package(
    tour_id: str,
    language_code: str = Query("vi", description="Requested language code"),
    current_user: dict = Depends(get_current_user)
):
    """Fetches or builds an offline package for a specific tour. Requires active tour entitlement if tour is paid."""
    if current_user.get("role") not in ("admin", "super_admin"):
        await offline_package_service.require_access(tour_id, current_user["_id"])

    pkg = await offline_package_service.generate_tour_package(tour_id=tour_id, language_code=language_code)
    if not pkg:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tour.")
    return pkg


@router.get("/{package_id}/manifest")
async def get_package_manifest(package_id: str, current_user: dict = Depends(get_current_user)):
    """Fetches raw JSON manifest of an offline package."""
    pkg = await offline_package_service.get_package_by_id(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Gói offline không tồn tại.")
    await offline_package_service.require_access(pkg["tour_id"], current_user["_id"])
    return pkg.get("manifest", pkg)


@router.get("/{package_id}/assets/{asset_id}")
async def download_package_asset(package_id: str, asset_id: str, current_user: dict = Depends(get_current_user)):
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.core.config import settings
    from app.services.audio_service import audio_service
    pkg = await offline_package_service.get_package_by_id(package_id)
    if not pkg:
        raise HTTPException(404, "Gói không tồn tại.")
    await offline_package_service.require_access(pkg["tour_id"], current_user["_id"])
    asset = next((a for a in pkg["manifest"]["files"] if a["asset_id"] == asset_id), None)
    if not asset:
        raise HTTPException(404, "File không thuộc gói.")
    base = Path(settings.MEDIA_STORAGE_DIR).resolve()
    path = Path(audio_service.get_audio_filepath(asset["storage_key"])) if asset["kind"] == "audio" else (base / asset["storage_key"]).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise HTTPException(404, "File không tồn tại.")
    return FileResponse(path, headers={"Cache-Control": "private, no-store", "ETag": asset["sha256"]})


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

