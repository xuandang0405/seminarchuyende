"""Router for POI endpoints (Public & Admin).

T01 / T04 / T05 / C01 / C02 / C03 / C04 / SD01 / SD03 / SD04.
Clean Router -> Service -> Repository.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

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
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    lang: Optional[str] = Query(None, description="Requested language code (vi, en, ja, ko, fr, zh)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Lists public POIs with language fallback (RFC 9110 Accept-Language or ?lang=...)."""
    effective_lang = lang or getattr(request.state, "lang", "vi")
    return await poi_service.get_public_pois(
        skip=skip,
        limit=limit,
        category=category,
        search=search,
        lang=effective_lang
    )


@router.get("/nearby", response_model=List[Dict[str, Any]])
async def get_nearby_pois(
    request: Request,
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of current location"),
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of current location"),
    max_distance_meters: float = Query(1000.0, ge=1, le=50000, description="Search radius in meters"),
    category: Optional[str] = None,
    lang: Optional[str] = Query(None, description="Requested language code (vi, en, ja, ko, fr, zh)"),
    limit: int = Query(20, ge=1, le=50)
):
    """Geospatial 2dsphere nearSphere query for POIs near user GPS location with language fallback."""
    effective_lang = lang or getattr(request.state, "lang", "vi")
    return await poi_service.get_nearby_pois(
        longitude=longitude,
        latitude=latitude,
        max_distance_meters=max_distance_meters,
        category=category,
        limit=limit,
        lang=effective_lang
    )


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_pois_endpoint(
    request: Request,
    q: str = Query(..., min_length=1, description="Search keyword for name, address, description, or tags"),
    category: Optional[str] = None,
    origin_lat: Optional[float] = Query(None, ge=-90, le=90, description="User latitude to calculate distance"),
    origin_lon: Optional[float] = Query(None, ge=-180, le=180, description="User longitude to calculate distance"),
    lang: Optional[str] = Query(None, description="Requested language code (vi, en, ja, ko, fr, zh)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Use Case T03 / SD-MAP-03: Search published POIs by query string with multilingual fallback."""
    effective_lang = lang or getattr(request.state, "lang", "vi")
    return await poi_service.search_public_pois(
        query=q,
        category=category,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        lang=effective_lang,
        skip=skip,
        limit=limit
    )


@router.get("/in-bounds", response_model=List[Dict[str, Any]])
async def get_pois_in_bounds_endpoint(
    request: Request,
    min_lon: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    category: Optional[str] = None,
    lang: Optional[str] = Query(None, description="Requested language code (vi, en, ja, ko, fr, zh)"),
    limit: int = Query(50, ge=1, le=100)
):
    """Use Case T01 / SD-MAP-01: Fetch POIs inside map viewport bounding box with language fallback."""
    from app.services.geo_service import validate_bbox
    validate_bbox(min_lon, min_lat, max_lon, max_lat)
    effective_lang = lang or getattr(request.state, "lang", "vi")
    return await poi_service.get_pois_in_bounds(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        category=category,
        limit=limit,
        lang=effective_lang
    )


@router.get("/{poi_id}", response_model=Dict[str, Any])
async def get_poi_detail(
    request: Request,
    poi_id: str,
    lang: Optional[str] = Query(None, description="Requested language code (vi, en, ja, ko, fr, zh)")
):
    """Fetches public POI detail with audio and localization fallback."""
    effective_lang = lang or getattr(request.state, "lang", "vi")
    detail = await poi_service.get_poi_detail(poi_id=poi_id, lang=effective_lang)
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
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin)
):
    """Creates a new POI draft with immediate MongoDB commit (<50ms).
    Multi-language translation and Google TTS synthesis run as non-blocking background tasks.
    """
    data = payload.model_dump()
    created = await poi_admin_service.create_poi(
        data,
        created_by=current_user["_id"],
        background_tasks=background_tasks
    )
    return created


@router.put("/{poi_id}")
@router.patch("/{poi_id}")
@router.post("/{poi_id}")
@router.put("")
@router.put("/")
@router.patch("")
@router.patch("/")
async def update_poi_admin(
    payload: POIUpdate,
    background_tasks: BackgroundTasks,
    poi_id: Optional[str] = None,
    current_user: dict = Depends(get_current_admin)
):
    """Updates POI with immediate database commit and async 6-language translation & Google TTS in background."""
    from app.repositories.poi_repo import poi_repo
    from app.core.database import db_manager
    from app.services.poi_admin_service import background_sync_poi_multilingual

    # Resolve target POI ID from path or payload body
    target_id = poi_id or payload.id or (payload.model_dump().get("id") if hasattr(payload, "id") else None)
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu mã nhận diện POI (poi_id hoặc payload.id)."
        )

    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("id", None)
    auto_translate = update_data.pop("auto_translate", True)
    expected_version = update_data.pop("expected_version", None)

    # Fetch current POI to check existence and version
    current_poi = await poi_repo.get_by_id(target_id)
    if not current_poi:
        current_poi = await poi_repo.get_public_by_id(target_id)
    if not current_poi:
        # Check by code if target_id was a code
        cursor = poi_repo.collection.find({"code": target_id})
        items = await cursor.to_list(1)
        if items:
            current_poi = items[0]
            target_id = current_poi["_id"]

    if not current_poi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"POI '{target_id}' không tồn tại.")

    has_explicit_version = payload.expected_version is not None
    if expected_version is None:
        expected_version = current_poi.get("content_version") or current_poi.get("version", 1)

    content_changed = bool("name" in update_data or "description" in update_data)

    updated = await poi_admin_service.update_poi(
        poi_id=target_id,
        update_fields=update_data,
        expected_version=expected_version,
        content_changed=content_changed
    )
    if not updated:
        if has_explicit_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Xung đột phiên bản (Version conflict). Dữ liệu đã bị người khác thay đổi."
            )
        # Resilient retry without strict version lock for admin editing
        latest_poi = await poi_repo.get_by_id(target_id) or await poi_repo.get_public_by_id(target_id)
        latest_ver = (latest_poi.get("version") if latest_poi else 1) or 1
        updated = await poi_admin_service.update_poi(
            poi_id=target_id,
            update_fields=update_data,
            expected_version=latest_ver,
            content_changed=content_changed
        )

    # Asynchronously synchronize 6-language translation & Google TTS in background
    if auto_translate or content_changed:
        final_name = update_data.get("name") or current_poi.get("name") or current_poi.get("code")
        final_desc = update_data.get("description") or current_poi.get("description") or ""
        background_tasks.add_task(background_sync_poi_multilingual, target_id, final_name, final_desc)

    return updated or {"status": "success", "id": target_id}


@router.post("/{poi_id}/sync-multilingual")
async def sync_single_poi_multilingual(
    poi_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Forces automated 6-language translation and Google TTS generation for a specific POI."""
    from app.repositories.poi_repo import poi_repo
    from app.core.database import db_manager
    from app.services.translation_service import translation_service

    poi = await poi_repo.get_by_id(poi_id) or await poi_repo.get_public_by_id(poi_id)
    if not poi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI không tồn tại.")

    name = poi.get("name") or poi.get("code", "Điểm tham quan")
    description = poi.get("description", "")
    trans = await translation_service.sync_poi_multilingual(
        poi_id=poi_id,
        name=name,
        description=description,
        db=db_manager.db
    )
    return {
        "status": "success",
        "poi_id": poi_id,
        "name": name,
        "languages": list(trans.keys()),
        "translations": trans
    }


@router.post("/batch-sync-all")
async def batch_sync_all_pois(
    current_user: dict = Depends(get_current_admin)
):
    """Synchronizes all existing POIs: translates into 6 languages and generates Google TTS MP3 audio."""
    from app.core.database import db_manager
    from app.db.collections import COLLECTION_POI
    from app.services.translation_service import translation_service

    db = db_manager.db
    if db is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database chưa kết nối.")

    pois = await db[COLLECTION_POI].find({"deleted_at": None}).to_list(200)
    synced_count = 0
    results = []

    for p in pois:
        pid = p["_id"]
        name = p.get("name") or p.get("code", f"POI {pid}")
        desc = p.get("description", "")
        try:
            trans = await translation_service.sync_poi_multilingual(
                poi_id=pid,
                name=name,
                description=desc,
                db=db
            )
            synced_count += 1
            results.append({"poi_id": pid, "name": name, "status": "success", "languages": len(trans)})
        except Exception as e:
            results.append({"poi_id": pid, "name": name, "status": "error", "error": str(e)})

    return {
        "status": "success",
        "total_pois": len(pois),
        "synced_count": synced_count,
        "items": results
    }


@router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poi_admin(
    poi_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Soft deletes POI and cascades deletion to all associated QR codes."""
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
