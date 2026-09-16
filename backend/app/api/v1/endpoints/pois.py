"""Router for POI endpoints (Public & Admin).

T01 / T04 / T05 / C01 / C02 / C03 / C04 / SD01 / SD03 / SD04.
Clean Router -> Service -> Repository.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.services.poi_service import poi_service
from app.services.poi_admin_service import poi_admin_service
from app.schemas.poi import POICreate, POIUpdate, POIPublicResponse, POIAdminResponse
from app.api.v1.endpoints.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/pois", tags=["POIs (Points of Interest)"])


# =============================================================================
# PUBLIC ENDPOINTS (Khách du lịch - T01, T04, T05)
# =============================================================================

@router.get("", response_model=Dict[str, Any])
async def list_public_pois(
    category: Optional[str] = None,
    search: Optional[str] = None,
    lang: str = Query("vi", description="Requested language code (vi, en, fr, zh, ja)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Lists public POIs with language fallback."""
    return await poi_service.get_public_pois(
        skip=skip,
        limit=limit,
        category=category,
        search=search,
        lang=lang
    )


@router.get("/nearby", response_model=List[Dict[str, Any]])
async def get_nearby_pois(
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of current location"),
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of current location"),
    max_distance_meters: float = Query(1000.0, ge=1, le=50000, description="Search radius in meters"),
    category: Optional[str] = None,
    lang: str = Query("vi"),
    limit: int = Query(20, ge=1, le=50)
):
    """Geospatial 2dsphere nearSphere query for POIs near user GPS location."""
    return await poi_service.get_nearby_pois(
        longitude=longitude,
        latitude=latitude,
        max_distance_meters=max_distance_meters,
        category=category,
        limit=limit,
        lang=lang
    )


@router.get("/{poi_id}", response_model=Dict[str, Any])
async def get_poi_detail(
    poi_id: str,
    lang: str = Query("vi", description="Requested language code")
):
    """Fetches public POI detail with audio and localization fallback."""
    detail = await poi_service.get_poi_detail(poi_id=poi_id, lang=lang)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI không tồn tại hoặc chưa được công bố.")
    return detail


@router.get("/{poi_id}/contents/{lang}/active")
async def get_active_poi_content(poi_id: str, lang: str):
    """Legacy compatibility endpoint: Fetch active content for a POI in a given language."""
    from app.repositories.poi_repo import poi_repo
    poi = await poi_repo.get_by_id(poi_id)
    if not poi:
        poi = await poi_repo.get_public_by_id(poi_id)
    if not poi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI không tồn tại.")

    loc = await poi_repo.get_localization_by_lang(poi_id, lang)
    if not loc:
        loc = await poi_repo.get_localization_by_lang(poi_id, "vi") or await poi_repo.get_localization_by_lang(poi_id, "en")

    title = loc.get("name") if loc else (poi.get("name") or poi.get("code", "Điểm tham quan"))
    desc = loc.get("description") if loc else poi.get("description", poi.get("address", ""))
    audio_url = loc.get("audio_url") if loc else None

    return {
        "_id": f"{poi_id}_{lang}",
        "poi_id": poi_id,
        "language_code": loc.get("lang", lang) if loc else lang,
        "title": title,
        "description": desc,
        "narration_text": desc,
        "audio_url": audio_url,
        "audio_asset_id": loc.get("audio_asset_id") if loc else f"audio_{poi_id}_{lang}",
        "status": "approved"
    }


# =============================================================================
# ADMIN / OWNER ENDPOINTS (C01, C02, C03, C04)
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_poi_admin(
    payload: POICreate,
    current_user: dict = Depends(get_current_admin)
):
    """Creates a new POI (Admin only)."""
    data = payload.model_dump()
    created = await poi_admin_service.create_poi(data, created_by=current_user["_id"])
    return created


@router.patch("/{poi_id}")
async def update_poi_admin(
    poi_id: str,
    payload: POIUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Updates POI with optimistic concurrency check."""
    update_data = payload.model_dump(exclude_unset=True)
    expected_version = update_data.pop("expected_version")

    # Content change flag
    content_changed = bool("name" in update_data or "description" in update_data)

    updated = await poi_admin_service.update_poi(
        poi_id=poi_id,
        update_fields=update_data,
        expected_version=expected_version,
        content_changed=content_changed
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xung đột phiên bản (Version conflict). Dữ liệu đã bị người khác thay đổi."
        )
    return updated


@router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poi_admin(
    poi_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Soft deletes POI."""
    success = await poi_admin_service.soft_delete_poi(poi_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI không tồn tại.")
    return None


@router.post("/{poi_id}/toggle-active")
async def toggle_poi_active(
    poi_id: str,
    active: bool = Query(..., description="Requested active state"),
    current_user: dict = Depends(get_current_admin)
):
    """
    Manages publication with Readiness Gate.
    Verifies that English content and audio are valid before activating.
    """
    res = await poi_admin_service.toggle_activation(poi_id=poi_id, request_active=active)
    return res
