import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_admin
from app.schemas.poi import POICreate, POIUpdate, POIResponse, PoiCategory

router = APIRouter(prefix="/pois", tags=["POIs (Points of Interest)"])


@router.get("", response_model=List[POIResponse])
async def list_pois(
    category: Optional[PoiCategory] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    query = {}
    if category:
        query["category"] = category
    if status_filter:
        query["status"] = status_filter

    cursor = db["pois"].find(query).skip(skip).limit(limit)
    pois = await cursor.to_list(length=limit)
    return pois


@router.post("", response_model=POIResponse, status_code=status.HTTP_201_CREATED)
async def create_poi(
    poi_in: POICreate,
    current_user: dict = Depends(get_current_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    # Check unique code
    existing = await db["pois"].find_one({"code": poi_in.code})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"POI code '{poi_in.code}' already exists"
        )

    now = datetime.now(timezone.utc)
    poi_dict = poi_in.model_dump()
    poi_doc = {
        "_id": str(uuid.uuid4()),
        **poi_dict,
        "revision": 1,
        "published_contents": {},
        "created_by": current_user["_id"],
        "created_at": now,
        "updated_at": now
    }

    await db["pois"].insert_one(poi_doc)
    return poi_doc


@router.get("/{poi_id}", response_model=POIResponse)
async def get_poi(poi_id: str):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    poi = await db["pois"].find_one({"_id": poi_id})
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi


@router.put("/{poi_id}", response_model=POIResponse)
async def update_poi(
    poi_id: str,
    poi_in: POIUpdate,
    current_user: dict = Depends(get_current_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    existing = await db["pois"].find_one({"_id": poi_id})
    if not existing:
        raise HTTPException(status_code=404, detail="POI not found")

    update_data = {k: v for k, v in poi_in.model_dump(exclude_unset=True).items() if v is not None}
    if not update_data:
        return existing

    # Validate radius if either radius_enter_m or radius_exit_m is updated
    enter_m = update_data.get("radius_enter_m", existing["radius_enter_m"])
    exit_m = update_data.get("radius_exit_m", existing["radius_exit_m"])
    if exit_m <= enter_m:
        raise HTTPException(
            status_code=400,
            detail="radius_exit_m must be strictly greater than radius_enter_m"
        )

    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data["revision"] = existing.get("revision", 1) + 1

    await db["pois"].update_one({"_id": poi_id}, {"$set": update_data})
    updated_poi = await db["pois"].find_one({"_id": poi_id})
    return updated_poi


@router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poi(
    poi_id: str,
    current_user: dict = Depends(get_current_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await db["pois"].delete_one({"_id": poi_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="POI not found")
    return None
