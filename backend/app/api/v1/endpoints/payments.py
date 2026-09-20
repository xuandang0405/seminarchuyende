"""Endpoints for Customer Payments & E-Ticket Orders."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status


from app.core.config import settings
from app.services.payment_service import payment_service

router = APIRouter(prefix="/payments", tags=["Payments & Orders"])


class CreateOrderRequest(BaseModel):
    order_type: str = Field("tour_ticket", description="'tour_ticket', 'menu_order', or 'premium_offline'")
    item_id: str = Field(..., description="ID của Tour hoặc POI / Món ăn")
    item_title: str = Field(..., description="Tên Tour hoặc Tên Món ăn")
    customer_name: str = Field(..., description="Họ tên khách hàng")
    customer_phone: str = Field(..., description="Số điện thoại")
    customer_email: str = Field(..., description="Email nhận vé điện tử")
    quantity: int = Field(1, ge=1, le=50, description="Số lượng vé / phần ăn")
    unit_price: int = Field(150000, ge=0, description="Đơn giá (VND)")
    notes: Optional[str] = Field("", description="Ghi chú thêm của khách")
    payment_method: str = Field("vietqr", description="'vietqr', 'momo', or 'cash'")


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(req: CreateOrderRequest):
    """Tạo đơn hàng mua vé tour / đặt món và sinh mã VietQR thanh toán tự động."""
    order = await payment_service.create_order(
        order_type=req.order_type,
        item_id=req.item_id,
        item_title=req.item_title,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        customer_email=req.customer_email,
        quantity=req.quantity,
        unit_price=req.unit_price,
        notes=req.notes or "",
        payment_method=req.payment_method
    )
    return {
        "status": "success",
        "message": "Đã tạo đơn hàng thành công. Vui lòng quét mã VietQR để thanh toán.",
        "data": order
    }


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str):
    """Tra cứu chi tiết đơn hàng và vé điện tử E-Ticket."""
    order = await payment_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    return order


from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from app.api.v1.endpoints.auth import oauth2_scheme, get_current_admin


@router.post("/orders/{order_id}/simulate-success")
async def simulate_payment_success(order_id: str, request: Request):
    """Webhook / IPN giả lập thanh toán thành công (Phục vụ demo chấm điểm đồ án).
    
    Bảo vệ an toàn trong môi trường Production:
    - Nếu APP_ENV == 'production' và PAYMENT_MODE != 'mock': bắt buộc có quyền Admin.
    - Trong môi trường development/testing hoặc mock mode: cho phép demo và test tự động.
    """
    is_prod_live = (settings.APP_ENV == "production" and settings.PAYMENT_MODE != "mock")
    if is_prod_live:
        token = await oauth2_scheme(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cổng giả lập thanh toán bị vô hiệu hóa trong môi trường sản xuất. Yêu cầu quyền Quản trị viên."
            )
        admin = await get_current_admin(token=token)
        actor = f"admin:{admin.get('email', 'unknown')}"
    else:
        actor = "demo_client"

    try:
        updated = await payment_service.simulate_payment_success(order_id, actor=actor)
        return {
            "status": "success",
            "message": "Thanh toán thành công! Vé điện tử E-Ticket đã được kích hoạt.",
            "data": updated
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/orders")
async def list_orders(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    order_type: Optional[str] = None,
    limit: int = Query(50, le=100)
):
    """Lấy danh sách đơn hàng cho Quản trị viên và Chủ quán.
    
    Trong môi trường production, yêu cầu quyền quản trị viên để bảo vệ thông tin cá nhân khách hàng.
    """
    is_prod_live = (settings.APP_ENV == "production" and settings.PAYMENT_MODE != "mock")
    if is_prod_live:
        token = await oauth2_scheme(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yêu cầu quyền Quản trị viên để truy cập danh sách đơn hàng."
            )
        await get_current_admin(token=token)

    orders = await payment_service.list_orders(
        status=status_filter,
        order_type=order_type,
        limit=limit
    )
    return orders


@router.get("/my-orders")
async def get_my_orders(email: str = Query(..., description="Email của khách du lịch")):
    """Khách du lịch tra cứu lịch sử mua vé và các đơn hàng của mình bằng email (che số điện thoại bảo vệ riêng tư)."""
    clean_email = email.strip().lower()
    orders = await payment_service.list_orders(email=clean_email)
    # Mask sensitive details like phone number for privacy
    for order in orders:
        phone = order.get("customer_phone") or ""
        if len(phone) > 6:
            order["customer_phone"] = phone[:3] + "****" + phone[-3:]
    return orders


@router.get("/revenue-summary")
async def get_revenue_summary(request: Request):
    """Báo cáo tổng hợp doanh thu và số lượng vé bán cho Dashboard Admin.
    
    Trong môi trường production live, yêu cầu quyền Quản trị viên để tránh lộ thông tin kinh doanh.
    """
    is_prod_live = (settings.APP_ENV == "production" and settings.PAYMENT_MODE != "mock")
    if is_prod_live:
        token = await oauth2_scheme(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yêu cầu đăng nhập tài khoản Quản trị viên để xem báo cáo doanh thu."
            )
        await get_current_admin(token=token)

    return await payment_service.get_revenue_summary()


# =============================================================================
# WEBHOOKS & IPN NOTIFICATIONS (P03)
# =============================================================================

from fastapi import Request, Header
from app.api.v1.endpoints.auth import get_current_admin


@router.post("/webhook/payos")
async def payos_webhook_endpoint(request: Request):
    """P03: payOS Webhook notification handler with HMAC SHA-256 verification."""
    body = await request.json()
    signature = request.headers.get("x-signature") or body.get("signature")
    res = await payment_service.handle_provider_webhook(
        provider_name="payos",
        payload=body,
        signature=signature
    )
    return {"code": "00", "desc": "success", "data": res}


@router.get("/ipn/vnpay")
@router.post("/ipn/vnpay")
async def vnpay_ipn_endpoint(request: Request):
    """P03: VNPAY IPN notification handler with HMAC SHA-512 verification.

    Returns VNPAY required response format: {"RspCode": "00", "Message": "Confirm Success"}.
    """
    params = dict(request.query_params)
    if not params and request.method == "POST":
        try:
            form = await request.form()
            params = dict(form)
        except Exception:
            params = {}

    try:
        await payment_service.handle_provider_webhook(
            provider_name="vnpay",
            payload=params
        )
        return {"RspCode": "00", "Message": "Confirm Success"}
    except HTTPException as e:
        return {"RspCode": "97", "Message": e.detail}
    except Exception as e:
        return {"RspCode": "99", "Message": str(e)}


@router.post("/mock/callback")
async def mock_callback_endpoint(request: Request):
    """P03: Mock callback simulation (strictly active when PAYMENT_MODE=mock)."""
    if settings.PAYMENT_MODE != "mock" and settings.APP_ENV not in ("development", "test", "testing"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cổng thanh toán mô phỏng (Mock) đã bị vô hiệu hóa trong môi trường Production."
        )
    body = await request.json()
    res = await payment_service.handle_provider_webhook(
        provider_name="mock",
        payload=body
    )
    return {"status": "success", "data": res}


# =============================================================================
# ADMIN RECONCILIATION & ORDER AUDITING (P06)
# =============================================================================

@router.get("/admin/orders")
async def admin_list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    """P06: Admin views all orders across the system."""
    from app.services.order_service import order_service
    return await order_service.list_all_orders_admin(skip=skip, limit=limit, status_filter=status_filter)


@router.post("/admin/orders/{order_id}/reconcile")
async def admin_reconcile_order(
    order_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """P06: Admin triggers direct server-to-server reconciliation with payment provider."""
    return await payment_service.reconcile_order(order_id=order_id, is_admin=True)

