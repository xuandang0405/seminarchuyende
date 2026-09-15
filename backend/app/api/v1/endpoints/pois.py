import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.repositories.poi_repo import poi_repo
from app.schemas.poi import POICreate, POIUpdate, POIResponse, PoiCategory, MenuItem

router = APIRouter(prefix="/pois", tags=["POIs (Points of Interest)"])


@router.get("", response_model=List[POIResponse])
async def list_pois(
    category: Optional[PoiCategory] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    query = {}
    if category:
        query["category"] = category
    if status_filter:
        query["status"] = status_filter
    if search:
        query["$or"] = [
            {"code": {"$regex": search, "$options": "i"}},
            {"address": {"$regex": search, "$options": "i"}}
        ]

    pois = await poi_repo.list(query=query, skip=skip, limit=limit)
    return pois


@router.get("/nearby", response_model=List[POIResponse])
async def get_nearby_pois(
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of current location"),
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of current location"),
    max_distance_meters: float = Query(1000.0, ge=1, le=50000, description="Search radius in meters"),
    category: Optional[PoiCategory] = None,
    limit: int = Query(20, ge=1, le=50)
):
    """Geospatial 2dsphere search for POIs near user's current GPS location."""
    pois = await poi_repo.find_nearby(
        longitude=longitude,
        latitude=latitude,
        max_distance_meters=max_distance_meters,
        category=category,
        status="active",
        limit=limit
    )
    return pois


@router.get("/{poi_id}", response_model=POIResponse)
async def get_poi(poi_id: str):
    poi = await poi_repo.get_by_id(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi


@router.post("", response_model=POIResponse, status_code=status.HTTP_201_CREATED)
async def create_poi(
    poi_in: POICreate,
    current_user: dict = Depends(get_current_admin)
):
    existing = await poi_repo.find_by_code(poi_in.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"POI code '{poi_in.code}' already exists"
        )

    now = datetime.now(timezone.utc)
    poi_doc = {
        "_id": str(uuid.uuid4()),
        **poi_in.model_dump(),
        "revision": 1,
        "published_contents": {},
        "created_by": current_user["_id"],
        "created_at": now,
        "updated_at": now
    }

    await poi_repo.insert_one(poi_doc)
    return poi_doc


@router.put("/{poi_id}", response_model=POIResponse)
async def update_poi(
    poi_id: str,
    poi_in: POIUpdate,
    current_user: dict = Depends(get_current_user)
):
    existing = await poi_repo.get_by_id(poi_id)
    if not existing:
        raise HTTPException(status_code=404, detail="POI not found")

    # Only admin or POI owner can edit
    role = current_user.get("role")
    if role not in ("admin", "super_admin") and existing.get("owner_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this POI")

    update_data = {k: v for k, v in poi_in.model_dump(exclude_unset=True).items() if v is not None}
    if not update_data:
        return existing

    enter_m = update_data.get("radius_enter_m", existing.get("radius_enter_m", 25))
    exit_m = update_data.get("radius_exit_m", existing.get("radius_exit_m", 50))
    if exit_m <= enter_m:
        raise HTTPException(
            status_code=400,
            detail="radius_exit_m must be strictly greater than radius_enter_m"
        )

    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data["revision"] = existing.get("revision", 1) + 1

    updated_poi = await poi_repo.update_by_id(poi_id, update_data)
    return updated_poi


@router.post("/{poi_id}/menu", response_model=POIResponse)
async def add_or_update_menu_item(
    poi_id: str,
    item: MenuItem,
    current_user: dict = Depends(get_current_user)
):
    """Add a specialty or dish to POI's menu."""
    poi = await poi_repo.get_by_id(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")

    role = current_user.get("role")
    if role not in ("admin", "super_admin") and poi.get("owner_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to manage menu for this POI")

    menu_item_dict = item.model_dump()
    if not menu_item_dict.get("id"):
        menu_item_dict["id"] = str(uuid.uuid4())

    menu_list = poi.get("menu_items", [])
    menu_list.append(menu_item_dict)

    updated = await poi_repo.update_by_id(poi_id, {
        "menu_items": menu_list,
        "updated_at": datetime.now(timezone.utc)
    })
    return updated


@router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poi(
    poi_id: str,
    current_user: dict = Depends(get_current_admin)
):
    success = await poi_repo.delete_by_id(poi_id)
    if not success:
        raise HTTPException(status_code=404, detail="POI not found")
    return None
