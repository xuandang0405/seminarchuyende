"""Router for Current User's Personal Tours & Orders.

Section 10 of prompt.
P04 / P05.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query

from app.api.v1.endpoints.auth import get_current_user
from app.services.order_service import order_service
from app.services.entitlement_service import entitlement_service
from app.schemas.order import OrderResponse

router = APIRouter(prefix="/me", tags=["My Account (Tours & Orders)"])


@router.get("/orders", response_model=List[OrderResponse])
async def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """P05: Lists order history for current authenticated tourist."""
    orders = await order_service.list_user_orders(user_id=current_user["_id"], skip=skip, limit=limit)
    return [
        {
            "_id": o["_id"],
            "order_id": o["_id"],
            "user_id": o["user_id"],
            "tour_id": o["tour_id"],
            "tour_title": o.get("tour_title_snapshot", ""),
            "amount_vnd": o.get("amount_vnd", o.get("total_amount", 0)),
            "currency": o.get("currency", "VND"),
            "pricing_version": o.get("pricing_version", 1),
            "status": o["status"],
            "idempotency_key": o.get("idempotency_key"),
            "created_at": o["created_at"],
            "expires_at": o.get("expires_at", o["created_at"]),
            "paid_at": o.get("paid_at")
        }
        for o in orders
    ]


@router.get("/tours")
async def get_my_purchased_tours(
    current_user: dict = Depends(get_current_user)
):
    """P04: Lists all tours purchased by current user with active entitlement."""
    return await entitlement_service.get_user_entitled_tours(user_id=current_user["_id"])
