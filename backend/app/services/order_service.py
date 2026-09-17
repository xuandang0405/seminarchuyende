"""Service for Tour Orders Lifecycle & Price Snapshots.

Section 7 of prompt.
BR-PAY-01..02 / BR-PAY-06.
"""

from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.repositories.order_repo import order_repo
from app.repositories.tour_repo import tour_repo
from app.services.entitlement_service import entitlement_service


class OrderService:
    async def create_tour_order(
        self,
        user_id: str,
        tour_id: str,
        idempotency_key: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a purchase order for a tour.

        Enforces:
        - Rule BR-PAY-01: Must be authenticated user.
        - Already purchased check (Rule BR-PAY-07): Prevent duplicate orders.
        - Rule BR-PAY-02: Snapshot price and pricing_version from database.
        - Idempotency support.
        """
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yêu cầu đăng nhập tài khoản để mua tour."
            )

        # 1. Check if user already owns this tour
        if await entitlement_service.has_tour_entitlement(user_id, tour_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bạn đã sở hữu tour này rồi, không cần mua lại."
            )

        # 2. Check idempotency
        if idempotency_key:
            existing = await order_repo.get_by_user_and_idempotency(user_id, idempotency_key)
            if existing:
                return existing

        # 3. Read tour from database (Price snapshot invariant)
        tour = await tour_repo.get_by_id(tour_id)
        if not tour or not tour.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tour không tồn tại hoặc đã ngừng hoạt động."
            )

        if not tour.get("is_purchasable", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tour này hiện chưa được mở bán."
            )

        amount_vnd = int(tour.get("price_amount", 0))
        if amount_vnd <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Giá tour chưa được cấu hình hợp lệ."
            )

        pricing_version = int(tour.get("pricing_version", 1))
        tour_title = tour.get("name", "Tour Du Lịch Quận 4")

        # 4. Save order snapshot
        order = await order_repo.create_order(
            user_id=user_id,
            tour_id=tour_id,
            tour_title=tour_title,
            amount_vnd=amount_vnd,
            pricing_version=pricing_version,
            idempotency_key=idempotency_key,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            expires_minutes=30
        )

        return order

    async def get_order_by_id(
        self,
        order_id: str,
        actor_user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """Fetches order with strict IDOR protection."""
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Đơn hàng không tồn tại.")

        # IDOR check: Only owner or admin can view
        if not is_admin and order.get("user_id") != actor_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem thông tin đơn hàng này."
            )

        return order

    async def list_user_orders(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        return await order_repo.list_user_orders(user_id=user_id, skip=skip, limit=limit)

    async def list_all_orders_admin(self, skip: int = 0, limit: int = 50, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        return await order_repo.list_all_orders(skip=skip, limit=limit, status=status_filter)


order_service = OrderService()
