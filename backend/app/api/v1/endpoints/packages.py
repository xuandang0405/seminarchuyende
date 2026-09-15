from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.v1.endpoints.auth import get_current_user
from app.repositories.base import BaseRepository
from app.schemas.tour_package import TourPackageResponse
from app.services.offline_package_service import offline_package_service

router = APIRouter(prefix="/packages", tags=["Offline Tour Packages"])
package_repo = BaseRepository("tour_packages")


@router.post("/tours/{tour_id}/generate", response_model=TourPackageResponse)
async def generate_package(
    tour_id: str,
    language_code: str = Query("vi", description="Target language, e.g., 'vi' or 'en'"),
    current_user: dict = Depends(get_current_user)
):
    """Generate or refresh an offline snapshot manifest for a tour."""
    package = await offline_package_service.generate_tour_package(tour_id, language_code)
    return package


@router.get("/tours/{tour_id}", response_model=TourPackageResponse)
async def get_tour_package(
    tour_id: str,
    language_code: str = Query("vi")
):
    """Retrieve the offline manifest for downloading."""
    package = await package_repo.find_one({
        "tour_id": tour_id,
        "language_code": language_code
    })
    if not package:
        # Generate on-demand if not existing
        package = await offline_package_service.generate_tour_package(tour_id, language_code)
    return package


@router.get("/{package_id}", response_model=TourPackageResponse)
async def get_package_by_id(package_id: str):
    package = await package_repo.get_by_id(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return package
