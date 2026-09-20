"""Router for Tour Purchase Orders & Payment Attempts.

Section 7 & 10 of prompt.
BR-PAY-01..06.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.v1.endpoints.auth import get_current_user
from app.services.order_service import order_service
from app.services.payment_service import payment_service
from app.schemas.order import (
    OrderCreateRequest,
    OrderResponse,
    PaymentAttemptCreateRequest,
    PaymentAttemptResponse,
    OrderReconcileResponse
)

router = APIRouter(prefix="/orders", tags=["Orders & Payments"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_orders_endpoint(
    status: Optional[str] = Query(None, description="Filter by order status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """P05/P06: Lists orders for the current user or all orders if admin."""
    from typing import List
    is_admin = current_user.get("role") in ("admin", "super_admin")
    if is_admin:
        return await order_service.list_all_orders_admin(skip=skip, limit=limit, status_filter=status)
    return await order_service.list_user_orders(user_id=current_user["_id"], skip=skip, limit=limit, status_filter=status)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_tour_order_endpoint(
    body: OrderCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """P01: Creates an immutable tour purchase order. Requires logged-in tourist account."""
    order = await order_service.create_tour_order(
        user_id=current_user["_id"],
        tour_id=body.tour_id,
        idempotency_key=body.idempotency_key,
        customer_name=body.customer_name or current_user.get("full_name"),
        customer_phone=body.customer_phone,
        customer_email=current_user.get("email")
    )
    return {
        "order_id": order["_id"],
        "user_id": order["user_id"],
        "tour_id": order["tour_id"],
        "tour_title": order.get("tour_title_snapshot", ""),
        "amount_vnd": order["amount_vnd"],
        "currency": order.get("currency", "VND"),
        "pricing_version": order.get("pricing_version", 1),
        "status": order["status"],
        "idempotency_key": order.get("idempotency_key"),
        "created_at": order["created_at"],
        "expires_at": order["expires_at"],
        "paid_at": order.get("paid_at")
    }


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_endpoint(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """P05: Gets order details with strict IDOR protection."""
    is_admin = current_user.get("role") in ("admin", "super_admin")
    order = await order_service.get_order_by_id(
        order_id=order_id,
        actor_user_id=current_user["_id"],
        is_admin=is_admin
    )
    return {
        "order_id": order["_id"],
        "user_id": order["user_id"],
        "tour_id": order["tour_id"],
        "tour_title": order.get("tour_title_snapshot", ""),
        "amount_vnd": order.get("amount_vnd", order.get("total_amount", 0)),
        "currency": order.get("currency", "VND"),
        "pricing_version": order.get("pricing_version", 1),
        "status": order["status"],
        "idempotency_key": order.get("idempotency_key"),
        "created_at": order["created_at"],
        "expires_at": order.get("expires_at", order["created_at"]),
        "paid_at": order.get("paid_at")
    }


@router.post("/{order_id}/payment-attempts", response_model=PaymentAttemptResponse)
@router.post("/{order_id}/attempts", response_model=PaymentAttemptResponse)
async def create_payment_attempt_endpoint(
    order_id: str,
    body: PaymentAttemptCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """P02: Initiates a payment session with VNPAY (Visa) or payOS (VietQR)."""
    return await payment_service.create_payment_attempt(
        order_id=order_id,
        payment_method=body.payment_method,
        actor_user_id=current_user["_id"],
        return_url=body.return_url
    )


@router.post("/{order_id}/reconcile", response_model=OrderReconcileResponse)
async def reconcile_order_endpoint(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """P06: Reconciles order payment status by server query to payment provider."""
    is_admin = current_user.get("role") in ("admin", "super_admin")
    return await payment_service.reconcile_order(
        order_id=order_id,
        actor_user_id=current_user["_id"],
        is_admin=is_admin
    )
