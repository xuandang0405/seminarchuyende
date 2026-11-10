"""Checkout adapter shared by web/mobile; catalog prices are server-authoritative."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.core.config import settings
from app.repositories.order_repo import order_repo
from app.services.order_service import order_service
from app.services.payment_service import payment_service


PENDING = ("pending", "pending_payment")


def simulation_enabled():
    return settings.is_development and settings.PAYMENT_MODE == "mock"


def _require_simulation():
    if not simulation_enabled():
        raise HTTPException(403, "Mô phỏng thanh toán chỉ khả dụng trong môi trường phát triển.")


def _expired(order):
    expires = order.get("expires_at")
    return bool(expires and expires.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc))


def checkout_view(order):
    public_order = {key: value for key, value in order.items() if not key.startswith("payment_setup_") and key != "checkout_key"}
    return {**public_order, "order_id": order["_id"], "order_type": "tour_ticket",
            "item_id": order.get("tour_id"), "item_title": order.get("tour_title_snapshot"),
            "total_amount": order.get("amount_vnd", 0), "unit_price": order.get("amount_vnd", 0),
            "quantity": 1, "mock_mode": simulation_enabled()}


async def checkout_detail(order):
    view = checkout_view(order)
    if order["status"] not in PENDING:
        return view
    if _expired(order):
        return {**view, "status": "expired"}
    attempt = await order_repo.get_latest_attempt_for_order(order["_id"])
    view["mock_mode"] = simulation_enabled() and bool(attempt and attempt["provider"] == "mock")
    if attempt and attempt.get("state") in ("created", "pending", "unknown"):
        payment = {field: attempt.get(field) for field in ("checkout_url", "qr_code_data", "payment_method")}
        if view["mock_mode"] or payment["checkout_url"] or payment["qr_code_data"]:
            view.update(payment=payment, checkout_url=payment["checkout_url"])
    return view


async def create_checkout(req, user, idempotency_key=None):
    if req.order_type != "tour_ticket" or req.quantity != 1:
        raise HTTPException(422, "Mỗi đơn hàng cấp một quyền truy cập tour.")
    order = await order_service.create_tour_order(
        user_id=user["_id"], tour_id=req.item_id, idempotency_key=idempotency_key,
        customer_name=req.customer_name, customer_phone=req.customer_phone,
        customer_email=user["email"])
    if order.get("status") in ("paid", "requires_review"):
        return checkout_view(order)
    attempt = await payment_service.create_payment_attempt(order["_id"], req.payment_method, user["_id"])
    current = await order_repo.get_by_id(order["_id"])
    return {**checkout_view(current), "payment": attempt, "vietqr_url": attempt.get("qr_code_data"),
            "checkout_url": attempt.get("checkout_url"), "mock_mode": attempt.get("mock_mode", False),
            "bank_info": attempt.get("bank_account_info")}


async def simulate_checkout(order_id, user):
    _require_simulation()
    order = await order_service.get_order_by_id(order_id, user["_id"], user.get("role") in ("admin", "super_admin"))
    attempt = await order_repo.get_latest_attempt_for_order(order_id)
    if not attempt or attempt["provider"] != "mock":
        raise HTTPException(409, "Không có phiên thanh toán mô phỏng hợp lệ.")
    if order.get("status") != "paid":
        _require_pending(order)
        if attempt.get("state") not in ("created", "pending", "unknown", "succeeded"):
            raise HTTPException(409, "Phiên thanh toán mô phỏng đã kết thúc.")
        await payment_service.handle_provider_webhook("mock", {
            "provider_reference": attempt["provider_reference"], "amount": order["amount_vnd"],
            "transaction_id": "MOCK-" + order_id, "status": "PAID"})
    current = await order_repo.get_by_id(order_id)
    if not current or current["status"] != "paid":
        raise HTTPException(409, "Chưa xác nhận được thanh toán mô phỏng. Hãy kiểm tra lại đơn.")
    return {**checkout_view(current), "simulated": True}


def _require_pending(order):
    if order["status"] == "expired" or _expired(order):
        raise HTTPException(409, {"error_code": "CHECKOUT_EXPIRED", "message": "Đơn đã hết hạn. Hãy tạo đơn mới."})
    if order["status"] not in PENDING:
        raise HTTPException(409, "Đơn đã đóng hoặc cần đối soát.")


async def simulate_tour_checkout(tour_id, user, idempotency_key):
    """Run checkout and settlement with the mock provider in a single test action."""
    _require_simulation()
    order = await order_service.create_tour_order(
        user_id=user["_id"], tour_id=tour_id, idempotency_key=idempotency_key,
        customer_name=user.get("full_name"), customer_email=user.get("email"),
    )
    attempt = await order_repo.get_latest_attempt_for_order(order["_id"])
    if attempt and attempt["provider"] != "mock":
        raise HTTPException(409, "Đơn đã mở tại cổng thanh toán thật. Hãy kiểm tra trạng thái đơn.")
    if order["status"] != "paid":
        _require_pending(order)
        if not attempt or attempt.get("state") not in ("pending", "succeeded"):
            await payment_service.create_payment_attempt(
                order["_id"], attempt["payment_method"] if attempt else "vietqr", user["_id"],
                mock_only=True,
            )
    return await simulate_checkout(order["_id"], user)
