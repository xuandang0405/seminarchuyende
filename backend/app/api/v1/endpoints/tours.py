import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_admin
from app.schemas.tour import TourCreate, TourUpdate, TourResponse, TourStatus

router = APIRouter(prefix="/tours", tags=["Tours"])


@router.get("", response_model=List[TourResponse])
async def list_tours(
    status_filter: Optional[TourStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    query = {}
    if status_filter:
        query["status"] = status_filter

    cursor = db["tours"].find(query).skip(skip).limit(limit)
    tours = await cursor.to_list(length=limit)
    return tours


@router.post("", response_model=TourResponse, status_code=status.HTTP_201_CREATED)
async def create_tour(
    tour_in: TourCreate,
    current_user: dict = Depends(get_current_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    existing = await db["tours"].find_one({"code": tour_in.code})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tour with code '{tour_in.code}' already exists"
        )

    # Optional: verify stops POIs exist in pois collection
    if tour_in.stops:
        poi_ids = [s.poi_id for s in tour_in.stops]
        existing_count = await db["pois"].count_documents({"_id": {"$in": poi_ids}})
        if existing_count != len(poi_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more POI IDs in stops do not exist in the database"
            )

    now = datetime.now(timezone.utc)
    tour_doc = {
        "_id": str(uuid.uuid4()),
        **tour_in.model_dump(),
        "content_revision": 1,
        "created_by": current_user["_id"],
        "created_at": now,
        "updated_at": now
    }

    await db["tours"].insert_one(tour_doc)
    return tour_doc


@router.get("/{tour_id}", response_model=TourResponse)
async def get_tour(tour_id: str):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    tour = await db["tours"].find_one({"_id": tour_id})
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    return tour


@router.put("/{tour_id}", response_model=TourResponse)
async def update_tour(
    tour_id: str,
    tour_in: TourUpdate,
    current_user: dict = Depends(get_current_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    existing = await db["tours"].find_one({"_id": tour_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Tour not found")

    update_data = {k: v for k, v in tour_in.model_dump(exclude_unset=True).items() if v is not None}
    if not update_data:
        return existing

    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data["content_revision"] = existing.get("content_revision", 1) + 1

    await db["tours"].update_one({"_id": tour_id}, {"$set": update_data})
    updated_tour = await db["tours"].find_one({"_id": tour_id})
    return updated_tour


@router.delete("/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tour(
    tour_id: str,
    current_user: dict = Depends(get_current_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await db["tours"].delete_one({"_id": tour_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tour not found")
    return None
