"""Router for Menu endpoints.

T06 / C05 / O09.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.endpoints.auth import get_current_user
from app.services.menu_service import menu_service
from app.schemas.menu import MenuItemCreate, MenuItemUpdate

router = APIRouter(tags=["Menu Items"])


@router.get("/pois/{poi_id}/menu", response_model=List[Dict[str, Any]])
async def list_poi_menu(poi_id: str):
    """Use Case T06: Public menu view for a POI."""
    return await menu_service.get_poi_menu(poi_id=poi_id)


@router.post("/pois/{poi_id}/menu", status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    poi_id: str,
    item_in: MenuItemCreate,
    current_user: dict = Depends(get_current_user)
):
    """Use Case C05, O09: Add a dish to POI menu."""
    role = current_user.get("role", "user")
    user_id = current_user["_id"]
    res = await menu_service.create_menu_item(
        poi_id=poi_id,
        payload=item_in.model_dump(),
        actor_id=user_id,
        actor_role=role
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=res.get("error"))
    return res["item"]


@router.patch("/menu/{item_id}")
async def update_menu_item(
    item_id: str,
    item_in: MenuItemUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Use Case C05, O09: Update dish."""
    role = current_user.get("role", "user")
    user_id = current_user["_id"]
    data = item_in.model_dump(exclude_unset=True)
    expected_version = data.pop("expected_version", None)

    res = await menu_service.update_menu_item(
        item_id=item_id,
        payload=data,
        actor_id=user_id,
        actor_role=role,
        expected_version=expected_version
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))
    return res["item"]


@router.delete("/menu/{item_id}")
async def delete_menu_item(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Use Case C05, O09: Delete dish or deactivate."""
    role = current_user.get("role", "user")
    user_id = current_user["_id"]
    res = await menu_service.delete_menu_item(
        item_id=item_id,
        actor_id=user_id,
        actor_role=role
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=res.get("error"))
    return res
