"""Payment & Settlement Service for Tour Purchases & Entitlements.

Implements Sections 6, 7 & 10 of prompt.
Adheres to:
- BR-PAY-01..07.
- Unified PaymentProvider interface (VNPAY, payOS, Mock).
- Idempotent Webhook & IPN processing.
- Multi-document atomic transactions for settlement and entitlement issuance.
- Legacy backward-compatibility for existing tests.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.database import get_database, db_manager
from app.db.collections import COLLECTION_ORDERS, COLLECTION_PAYMENTS
from app.repositories.order_repo import order_repo
from app.repositories.entitlement_repo import entitlement_repo
from app.repositories.payment_event_repo import payment_event_repo
from app.services.entitlement_service import entitlement_service
from app.services.payment_providers import get_payment_provider

logger = logging.getLogger("uvicorn")


class PaymentService:
    @property
    def orders_col(self):
        return get_database()[COLLECTION_ORDERS]

    @property
    def payments_col(self):
        return get_database()[COLLECTION_PAYMENTS]

    # =========================================================================
    # PRODUCTION ATTEMPTS & CHECKOUT (V1)
    # =========================================================================

    async def create_payment_attempt(
        self,
        order_id: str,
        payment_method: str,
        actor_user_id: str,
        return_url: Optional[str] = None,
        *,
        mock_only: bool = False,
    ) -> Dict[str, Any]:
        """Serializes checkout setup per order across API processes."""
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Đơn hàng không tồn tại.")

        if order.get("user_id") != actor_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền thao tác trên đơn hàng này.")
        if order.get("status") != "paid" and await entitlement_service.has_tour_entitlement(actor_user_id, order["tour_id"]):
            raise HTTPException(409, "Bạn đã sở hữu tour này.")

        if order.get("status") == "paid":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng này đã được thanh toán thành công.")

        expires = order.get("expires_at")
        if expires and expires.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(409, "Phiên thanh toán đã hết hạn. Vui lòng tạo đơn mới.")
        if order.get("status") not in ("pending_payment", "pending"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trạng thái đơn hàng '{order.get('status')}' không cho phép thanh toán tiếp."
            )

        owner = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        claimed = await order_repo.collection.find_one_and_update(
            {"_id": order_id, "status": {"$in": ["pending", "pending_payment"]},
             "$or": [{"payment_setup_until": None}, {"payment_setup_until": {"$lte": now}}]},
            {"$set": {"payment_setup_owner": owner, "payment_setup_until": now + timedelta(seconds=30)}},
            return_document=True,
        )
        if not claimed:
            raise HTTPException(409, "Đơn đang được xử lý. Vui lòng kiểm tra lại sau.")
        try:
            return await self._setup_payment(claimed, payment_method, return_url, mock_only=mock_only)
        finally:
            await order_repo.collection.update_one(
                {"_id": order_id, "payment_setup_owner": owner},
                {"$unset": {"payment_setup_owner": "", "payment_setup_until": ""}},
            )

    async def _setup_payment(self, order, payment_method, return_url, *, mock_only=False):
        order_id = order["_id"]
        existing_attempt = await order_repo.get_latest_attempt_for_order(order_id)
        if mock_only and existing_attempt and existing_attempt["provider"] != "mock":
            raise HTTPException(409, "Đơn đã mở tại cổng thanh toán thật.")
        reuse = existing_attempt and existing_attempt.get("state") in ("pending", "unknown", "created")
        if reuse and existing_attempt.get("payment_method") != payment_method:
            raise HTTPException(409, "Đơn đã có phương thức thanh toán. Hãy dùng lại phương thức đã chọn.")
        if reuse and (existing_attempt.get("checkout_url") or existing_attempt.get("qr_code_data")):
            return {
                "attempt_id": existing_attempt["_id"],
                "order_id": order_id,
                "provider": existing_attempt["provider"],
                "payment_method": existing_attempt["payment_method"],
                "provider_reference": existing_attempt["provider_reference"],
                "amount_vnd": existing_attempt["expected_amount_vnd"],
                "currency": "VND",
                "state": existing_attempt["state"],
                "checkout_url": existing_attempt.get("checkout_url"),
                "qr_code_data": existing_attempt.get("qr_code_data"),
                "mock_mode": existing_attempt["provider"] == "mock",
                "message": "Sử dụng lại phiên thanh toán hiện hành."
            }

        provider = get_payment_provider(provider_name=existing_attempt["provider"]) if reuse else get_payment_provider(method=payment_method)
        provider_name = provider.provider_name
        if mock_only and provider_name != "mock":
            raise HTTPException(403, "Mô phỏng thanh toán đang tắt.")

        provider_reference = f"{order_id}-{uuid.uuid4().hex[:12].upper()}"
        if provider_name == "payos":
            provider_reference = str(int(hashlib.sha256(provider_reference.encode()).hexdigest()[:13], 16))
        amount_vnd = int(order.get("amount_vnd") or order.get("total_amount", 0))

        # Create attempt record
        attempt_doc = existing_attempt if reuse else await order_repo.create_payment_attempt(
            order_id=order_id,
            provider=provider_name,
            payment_method=payment_method,
            provider_reference=provider_reference,
            expected_amount_vnd=amount_vnd
        )

        # Call provider outside database transaction (Network I/O)
        try:
            prov_res = await provider.create_payment(
                order=order,
                attempt=attempt_doc,
                return_url=return_url
            )
        except Exception as e:
            logger.error("Payment provider %s setup failed: %s", provider_name, type(e).__name__)
            # The provider may have accepted the reference before the response was lost.
            await order_repo.update_attempt_state(attempt_doc["_id"], "unknown")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Không thể mở cổng thanh toán. Hãy thử lại với cùng đơn.",
            ) from e

        # Update attempt with checkout info
        attempt = await order_repo.update_attempt_state(
            attempt_id=attempt_doc["_id"],
            state="pending"
        )
        await order_repo.attempt_collection.update_one(
            {"_id": attempt_doc["_id"]},
            {
                "$set": {
                    "checkout_url": prov_res.get("checkout_url"),
                    "qr_code_data": prov_res.get("qr_code_data"),
                    "raw_response": prov_res.get("raw_response"),
                    "provider_reference": prov_res.get("provider_reference", provider_reference),
                }
            }
        )

        return {
            "attempt_id": attempt_doc["_id"],
            "order_id": order_id,
            "provider": provider_name,
            "payment_method": payment_method,
            "provider_reference": prov_res.get("provider_reference", provider_reference),
            "amount_vnd": amount_vnd,
            "currency": "VND",
            "state": attempt["state"],
            "checkout_url": prov_res.get("checkout_url"),
            "qr_code_data": prov_res.get("qr_code_data"),
            "bank_account_info": prov_res.get("bank_account_info"),
            "mock_mode": prov_res.get("mock_mode", False),
            "message": "Khởi tạo phiên thanh toán thành công."
        }

    # =========================================================================
    # WEBHOOK / IPN & SETTLEMENT
    # =========================================================================

    async def handle_provider_webhook(
        self,
        provider_name: str,
        payload: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Processes incoming webhook or IPN from payment gateway with cryptographic verification."""
        provider = get_payment_provider(provider_name=provider_name)

        # 1. Cryptographic verification
        verify_res = await provider.verify_notification(
            payload=payload,
            raw_body=raw_body,
            signature=signature
        )

        provider_ref = verify_res.get("provider_reference")
        outcome = verify_res.get("outcome", "failed")
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        event_key = verify_res.get("provider_transaction_id") or f"{provider_ref}-{payload_hash[:8]}"

        if not verify_res.get("is_valid") or outcome == "invalid_signature":
            await payment_event_repo.record_event(
                provider=provider_name,
                event_key="invalid-" + payload_hash,
                provider_reference=provider_ref,
                outcome="invalid_signature",
                payload_hash=payload_hash,
                processing_state="failed",
                error_detail=verify_res.get("error_detail")
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chữ ký số không hợp lệ.")

        # 2. Check duplicate event (Rule BR-PAY-05)
        existing_event = await payment_event_repo.get_event(provider_name, event_key)
        if existing_event and existing_event.get("processing_state") == "processed":
            logger.info(f"Duplicate payment event received for {provider_name}:{event_key}. Returning idempotent ACK.")
            return {"status": "ok", "message": "Duplicate event ignored"}


        # 3. Resolve attempt & order
        attempt = await order_repo.get_attempt_by_ref(provider_name, provider_ref)
        if not attempt:
            logger.error(f"Cannot find payment attempt for reference: {provider_ref}")
            await payment_event_repo.record_event(
                provider=provider_name,
                event_key=event_key,
                provider_reference=provider_ref,
                outcome=outcome,
                payload_hash=payload_hash,
                processing_state="failed",
                error_detail="Attempt not found"
            )
            return {"status": "error", "message": "Transaction reference not found"}

        order_id = attempt["order_id"]
        order = await order_repo.get_by_id(order_id)
        if not order:
            return {"status": "error", "message": "Order not found"}
        if order.get("status") == "paid":
            return {"status": "ok", "order_id": order_id, "state": "paid"}

        # 4. Check for successful payment
        if outcome == "success":
            received_amount = verify_res.get("received_amount_vnd")
            expected_amount = int(attempt.get("expected_amount_vnd") or order.get("amount_vnd", 0))

            # Validate amount matching (Rule BR-PAY-04)
            if received_amount is None or received_amount != expected_amount:
                logger.warning(f"Amount mismatch for order {order_id}: expected {expected_amount}, received {received_amount}")
                reviewed = await order_repo.update_order_status(order_id, "requires_review")
                if reviewed and reviewed.get("status") == "paid":
                    return {"status": "ok", "order_id": order_id, "state": "paid"}
                await order_repo.update_attempt_state(
                    attempt["_id"],
                    state="unknown",
                    received_amount_vnd=received_amount,
                    provider_transaction_id=verify_res.get("provider_transaction_id")
                )
                await payment_event_repo.record_event(
                    provider=provider_name,
                    event_key=event_key,
                    provider_reference=provider_ref,
                    outcome="amount_mismatch",
                    payload_hash=payload_hash,
                    processing_state="requires_review",
                    error_detail=f"Amount mismatch: {received_amount} != {expected_amount}"
                )
                return {"status": "requires_review", "message": "Số tiền thanh toán không khớp"}

            # Execute settlement & grant entitlement (Rule BR-PAY-06)
            now = datetime.now(timezone.utc)
            tx_id = verify_res.get("provider_transaction_id") or f"TX-{now.strftime('%Y%m%d%H%M%S')}"

            await self._settle(order, attempt, tx_id, received_amount)

            await order_repo.collection.update_one({"_id": order_id, "ticket_code": None},
                {"$set": {"ticket_code": f"TICKET-Q4-{uuid.uuid4().hex[:16].upper()}"}})
            # Record event
            await payment_event_repo.record_event(
                provider=provider_name,
                event_key=event_key,
                provider_reference=provider_ref,
                outcome="success",
                payload_hash=payload_hash,
                processing_state="processed"
            )

            logger.info(f"Payment settled successfully for order {order_id}. Tour {order['tour_id']} unlocked for user {order['user_id']}.")
            return {"status": "ok", "order_id": order_id, "state": "paid"}

        else:
            # Payment failed
            updated = await order_repo.update_attempt_state(attempt["_id"], state="failed")
            if updated and updated.get("state") == "succeeded":
                return {"status": "ok", "order_id": order_id, "state": "paid"}
            await payment_event_repo.record_event(
                provider=provider_name,
                event_key=event_key,
                provider_reference=provider_ref,
                outcome="failed",
                payload_hash=payload_hash,
                processing_state="processed",
                error_detail=verify_res.get("error_detail")
            )
            return {"status": "failed", "order_id": order_id}

    async def _settle(self, order, attempt, tx_id, amount):
        now = datetime.now(timezone.utc)
        async def commit(session=None):
            kwargs = {"session": session} if session else {}
            latest = await order_repo.collection.find_one({"_id": order["_id"]}, **kwargs)
            if latest and latest.get("status") == "paid":
                return
            await order_repo.update_attempt_state(attempt["_id"], "succeeded",
                provider_transaction_id=tx_id, received_amount_vnd=amount, session=session)
            await entitlement_repo.create_entitlement(order["user_id"], order["tour_id"], order["_id"], session=session)
            await order_repo.update_order_status(order["_id"], "paid", paid_at=now, session=session)
            await order_repo.collection.update_one({"_id": order["_id"], "ticket_code": None},
                {"$set": {"ticket_code": "TICKET-Q4-" + uuid.uuid4().hex[:16].upper()}}, **kwargs)
        if db_manager.is_mock and settings.is_development:
            await commit()
            return
        try:
            async with get_database().client.start_session() as session:
                # Driver retries transient transaction/commit errors.
                await session.with_transaction(commit)
        except Exception as exc:
            logger.exception("Atomic payment settlement failed")
            raise HTTPException(503, "Giao dịch đang chờ đối soát lại.") from exc

    async def reconcile_order(
        self,
        order_id: str,
        actor_user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """Reconciles order state with payment provider by server query."""
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại.")

        if not is_admin and order.get("user_id") != actor_user_id:
            raise HTTPException(status_code=403, detail="Không có quyền đối soát đơn hàng này.")

        if order.get("status") == "paid":
            return {
                "order_id": order_id,
                "status": "paid",
                "is_paid": True,
                "entitlement_granted": True,
                "message": "Đơn hàng đã được thanh toán thành công."
            }

        attempt = await order_repo.get_latest_attempt_for_order(order_id)
        if not attempt:
            return {
                "order_id": order_id,
                "status": order.get("status"),
                "is_paid": False,
                "entitlement_granted": False,
                "message": "Chưa có nỗ lực thanh toán nào cho đơn hàng này."
            }

        provider = get_payment_provider(provider_name=attempt["provider"])
        try:
            query_res = await provider.query_payment(order=order, attempt=attempt)
        except Exception as exc:
            raise HTTPException(502, "Không thể xác minh giao dịch với cổng thanh toán.") from exc

        if query_res.get("is_paid"):
            if query_res.get("received_amount_vnd") != attempt.get("expected_amount_vnd"):
                reviewed = await order_repo.update_order_status(order_id, "requires_review")
                if reviewed and reviewed.get("status") == "paid":
                    return {"order_id": order_id, "status": "paid", "is_paid": True, "entitlement_granted": True}
                raise HTTPException(409, "Số tiền đối soát không khớp đơn hàng.")
            # Settle order
            now = datetime.now(timezone.utc)
            tx_id = query_res.get("provider_transaction_id") or "RECONCILED-TX"
            await self._settle(order, attempt, tx_id, query_res["received_amount_vnd"])
            return {
                "order_id": order_id,
                "status": "paid",
                "is_paid": True,
                "attempt_state": "succeeded",
                "provider_transaction_id": tx_id,
                "entitlement_granted": True,
                "message": "Giao dịch đã được xác nhận thành công từ cổng thanh toán."
            }

        return {
            "order_id": order_id,
            "status": order.get("status"),
            "is_paid": False,
            "attempt_state": attempt.get("state"),
            "provider_reference": attempt.get("provider_reference"),
            "entitlement_granted": False,
            "message": "Giao dịch chưa hoàn tất trên hệ thống ngân hàng. Vui lòng kiểm tra lại sau ít phút."
        }

    # =========================================================================
    # BACKWARD-COMPATIBLE METHODS FOR EXISTING TESTS
    # =========================================================================

    async def list_orders(
        self,
        status: Optional[str] = None,
        order_type: Optional[str] = None,
        email: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = {}
        if status:
            query["status"] = status
        if order_type:
            query["order_type"] = order_type
        if email:
            query["customer_email"] = email.strip().lower()

        cursor = self.orders_col.find(query).sort([("created_at", -1)]).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_revenue_summary(self) -> Dict[str, Any]:
        all_paid = await self.orders_col.find({"status": "paid"}).to_list(length=None)
        total_revenue = sum(o.get("total_amount", o.get("amount_vnd", 0)) for o in all_paid)
        total_tickets = sum(o.get("quantity", 1) for o in all_paid if o.get("order_type") == "tour_ticket")
        total_dish_orders = sum(1 for o in all_paid if o.get("order_type") == "menu_order")
        recent_orders = await self.list_orders(limit=10)

        return {
            "total_revenue_vnd": total_revenue,
            "total_paid_orders": len(all_paid),
            "total_tickets_sold": total_tickets,
            "total_dish_orders": total_dish_orders,
            "recent_orders": recent_orders,
            "currency": "VND",
        }


payment_service = PaymentService()
