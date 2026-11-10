"""Authenticated checkout, signed notifications and scoped order queries."""
from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from app.api.v1.endpoints.auth import get_current_user, get_current_admin
from app.services.payment_service import payment_service
from app.services.order_service import order_service
from app.services.checkout_service import (
    create_checkout, simulate_checkout, checkout_view, checkout_detail, simulation_enabled, simulate_tour_checkout,
)

router = APIRouter(prefix="/payments", tags=["Payments & Orders"])


class CreateOrderRequest(BaseModel):
    order_type: Literal["tour_ticket"] = "tour_ticket"
    item_id: str = Field(min_length=1, max_length=100)
    item_title: Optional[str] = None
    customer_name: str = Field(min_length=1, max_length=150)
    customer_phone: str = Field(min_length=8, max_length=20)
    customer_email: Optional[EmailStr] = None
    quantity: int = Field(1, ge=1, le=1)
    unit_price: Optional[int] = None  # Ignored; never trust client prices.
    notes: str = Field("", max_length=1000)
    payment_method: Literal["vietqr", "visa"] = "vietqr"


class SimulateTourRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=100)


@router.get("/config")
async def payment_config():
    return {"simulation_enabled": simulation_enabled()}


@router.post("/simulate-checkout")
async def simulate_order_checkout(
    req: SimulateTourRequest,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=100),
):
    return {"status": "success", "data": await simulate_tour_checkout(req.item_id, current_user, idempotency_key)}


@router.post("/orders", status_code=201)
async def create_order(req: CreateOrderRequest, current_user: dict = Depends(get_current_user),
                       idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    return {"status": "success", "data": await create_checkout(req, current_user, idempotency_key)}


@router.get("/orders")
async def list_orders(status_filter: Optional[str] = Query(None, alias="status"),
                      limit: int = Query(50, ge=1, le=100), current_admin: dict = Depends(get_current_admin)):
    return [checkout_view(o) for o in await order_service.list_all_orders_admin(limit=limit, status_filter=status_filter)]


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str, current_user: dict = Depends(get_current_user)):
    return await checkout_detail(await order_service.get_order_by_id(order_id, current_user["_id"],
                         current_user.get("role") in ("admin", "super_admin")))


@router.post("/orders/{order_id}/simulate-success")
async def simulate_payment_success(order_id: str, current_user: dict = Depends(get_current_user)):
    return {"status": "success", "data": await simulate_checkout(order_id, current_user)}


@router.get("/my-orders")
async def get_my_orders(current_user: dict = Depends(get_current_user)):
    return [checkout_view(o) for o in await order_service.list_user_orders(current_user["_id"])]


@router.get("/revenue-summary")
async def get_revenue_summary(current_admin: dict = Depends(get_current_admin)):
    return await payment_service.get_revenue_summary()


@router.post("/webhook/payos")
async def payos_webhook_endpoint(request: Request):
    body = await request.json()
    res = await payment_service.handle_provider_webhook("payos", body, signature=body.get("signature"))
    if res.get("status") == "error":
        raise HTTPException(404, "Không tìm thấy giao dịch tương ứng.")
    return {"code": "00", "desc": "success", "data": res}


@router.get("/ipn/vnpay")
@router.post("/ipn/vnpay")
async def vnpay_ipn_endpoint(request: Request):
    params = dict(request.query_params)
    if not params and request.method == "POST":
        params = dict(await request.form())
    try:
        result = await payment_service.handle_provider_webhook("vnpay", params)
        return {"RspCode": "01" if result.get("status") == "error" else "00", "Message": result.get("status")}
    except HTTPException:
        return {"RspCode": "97", "Message": "Invalid signature or notification"}


@router.post("/mock/callback")
async def mock_callback_endpoint(request: Request):
    if not simulation_enabled():
        raise HTTPException(403, "Mock callback is disabled.")
    return {"status": "success", "data": await payment_service.handle_provider_webhook("mock", await request.json())}


@router.get("/admin/orders")
async def admin_list_orders(status_filter: Optional[str] = Query(None, alias="status"),
                            skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                            current_admin: dict = Depends(get_current_admin)):
    return await order_service.list_all_orders_admin(skip=skip, limit=limit, status_filter=status_filter)


@router.post("/admin/orders/{order_id}/reconcile")
async def admin_reconcile_order(order_id: str, current_admin: dict = Depends(get_current_admin)):
    return await payment_service.reconcile_order(order_id, is_admin=True)
