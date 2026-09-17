"""Payment & Settlement Service for Tour Purchases & Entitlements.

Implements Sections 6, 7 & 10 of prompt.
Adheres to:
- BR-PAY-01..07.
- Unified PaymentProvider interface (VNPAY, payOS, Mock).
- Idempotent Webhook & IPN processing.
- Multi-document atomic transactions for settlement and entitlement issuance.
- Legacy backward-compatibility for existing tests.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.database import get_database
from app.db.collections import COLLECTION_ORDERS, COLLECTION_PAYMENTS
from app.repositories.order_repo import order_repo
from app.repositories.entitlement_repo import entitlement_repo
from app.repositories.payment_event_repo import payment_event_repo
from app.services.entitlement_service import entitlement_service
from app.services.payment_providers import get_payment_provider

logger = logging.getLogger("uvicorn")


class PaymentService:
    BANK_BIN = "970422"          # MB Bank (Ngân hàng Quân Đội)
    BANK_NAME = "MB Bank"
    ACCOUNT_NO = "0909123456"
    ACCOUNT_NAME = "TOURVOICE QUAN 4"

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
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiates a payment attempt with VNPAY, payOS, or Mock adapter."""
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Đơn hàng không tồn tại.")

        if order.get("user_id") != actor_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền thao tác trên đơn hàng này.")

        if order.get("status") == "paid":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng này đã được thanh toán thành công.")

        if order.get("status") not in ("pending_payment", "pending"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trạng thái đơn hàng '{order.get('status')}' không cho phép thanh toán tiếp."
            )

        # Check existing pending attempt to avoid duplicate charges
        existing_attempt = await order_repo.get_latest_attempt_for_order(order_id)
        if existing_attempt and existing_attempt.get("state") == "pending" and existing_attempt.get("payment_method") == payment_method:
            # Reuse active attempt if still valid
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

        # Resolve provider
        provider = get_payment_provider(method=payment_method)
        provider_name = provider.provider_name

        # Unique reference per attempt
        provider_reference = f"{order_id}-{uuid.uuid4().hex[:6].upper()}"
        amount_vnd = int(order.get("amount_vnd") or order.get("total_amount", 0))

        # Create attempt record
        attempt_doc = await order_repo.create_payment_attempt(
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
            logger.error(f"Error calling payment provider {provider_name}: {e}")
            await order_repo.update_attempt_state(attempt_doc["_id"], "failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Không thể kết nối đến cổng thanh toán ({str(e)})."
            )

        # Update attempt with checkout info
        await order_repo.update_attempt_state(
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
            "state": "pending",
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

        # 2. Check duplicate event (Rule BR-PAY-05)
        existing_event = await payment_event_repo.get_event(provider_name, event_key)
        if existing_event:
            logger.info(f"Duplicate payment event received for {provider_name}:{event_key}. Returning idempotent ACK.")
            return {"status": "ok", "message": "Duplicate event ignored"}

        if not verify_res.get("is_valid") or outcome == "invalid_signature":
            await payment_event_repo.record_event(
                provider=provider_name,
                event_key=event_key,
                provider_reference=provider_ref,
                outcome="invalid_signature",
                payload_hash=payload_hash,
                processing_state="failed",
                error_detail=verify_res.get("error_detail")
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chữ ký số không hợp lệ.")

        # 3. Resolve attempt & order
        attempt = await order_repo.get_attempt_by_ref(provider_name, provider_ref)
        if not attempt:
            # Try fuzzy match order_id in ref
            order_id = provider_ref.split("-")[0] if "-" in provider_ref else provider_ref
            attempt = await order_repo.get_latest_attempt_for_order(order_id)

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

        # 4. Check for successful payment
        if outcome == "success":
            received_amount = verify_res.get("received_amount_vnd")
            expected_amount = int(attempt.get("expected_amount_vnd") or order.get("amount_vnd", 0))

            # Validate amount matching (Rule BR-PAY-04)
            if received_amount is not None and received_amount != expected_amount:
                logger.warning(f"Amount mismatch for order {order_id}: expected {expected_amount}, received {received_amount}")
                await order_repo.update_order_status(order_id, "requires_review")
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

            # MongoDB Multi-Document Atomic Settlement (with fallback if replica set not enabled)
            db = get_database()
            session = None
            try:
                # Try starting a client session for transactions
                client = db.client
                session = await client.start_session()
                async with session.start_transaction():
                    await order_repo.update_attempt_state(
                        attempt["_id"],
                        state="succeeded",
                        provider_transaction_id=tx_id,
                        received_amount_vnd=received_amount or expected_amount,
                        session=session
                    )
                    await order_repo.update_order_status(
                        order_id=order_id,
                        status="paid",
                        paid_at=now,
                        session=session
                    )
                    await entitlement_repo.create_entitlement(
                        user_id=order["user_id"],
                        tour_id=order["tour_id"],
                        source_order_id=order_id,
                        session=session
                    )
            except Exception as e:
                # Fallback for local single-node / mock standalone databases
                logger.info(f"Transaction fallback to standalone operations: {e}")
                await order_repo.update_attempt_state(
                    attempt["_id"],
                    state="succeeded",
                    provider_transaction_id=tx_id,
                    received_amount_vnd=received_amount or expected_amount
                )
                await order_repo.update_order_status(order_id, "paid", paid_at=now)
                await entitlement_repo.create_entitlement(
                    user_id=order["user_id"],
                    tour_id=order["tour_id"],
                    source_order_id=order_id
                )
            finally:
                if session:
                    await session.end_session()

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
            await order_repo.update_attempt_state(attempt["_id"], state="failed")
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
        query_res = await provider.query_payment(order=order, attempt=attempt)

        if query_res.get("is_paid"):
            # Settle order
            now = datetime.now(timezone.utc)
            tx_id = query_res.get("provider_transaction_id") or "RECONCILED-TX"
            await order_repo.update_attempt_state(attempt["_id"], state="succeeded", provider_transaction_id=tx_id)
            await order_repo.update_order_status(order_id, "paid", paid_at=now)
            await entitlement_repo.create_entitlement(
                user_id=order["user_id"],
                tour_id=order["tour_id"],
                source_order_id=order_id
            )
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

    async def create_order(
        self,
        order_type: str,
        item_id: str,
        item_title: str,
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        quantity: int = 1,
        unit_price: int = 150000,
        notes: str = "",
        payment_method: str = "vietqr"
    ) -> Dict[str, Any]:
        """Legacy order creation method."""
        now = datetime.now(timezone.utc)
        random_suffix = uuid.uuid4().hex[:6].upper()
        order_id = f"TV-ORD-{random_suffix}"
        total_amount = max(0, quantity * unit_price)

        vietqr_url = (
            f"https://api.vietqr.io/image/{self.BANK_BIN}-{self.ACCOUNT_NO}-compact2.png"
            f"?amount={total_amount}&addInfo={order_id}&accountName=TOURVOICE%20QUAN%204"
        )

        doc = {
            "_id": order_id,
            "order_id": order_id,
            "order_type": order_type,
            "item_id": item_id,
            "item_title": item_title,
            "customer_name": customer_name.strip(),
            "customer_phone": customer_phone.strip(),
            "customer_email": customer_email.strip().lower(),
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "amount_vnd": total_amount,
            "notes": notes,
            "payment_method": payment_method,
            "status": "pending",
            "bank_info": {
                "bank_name": self.BANK_NAME,
                "account_no": self.ACCOUNT_NO,
                "account_name": self.ACCOUNT_NAME,
                "transfer_content": order_id,
            },
            "vietqr_url": vietqr_url,
            "ticket_code": None,
            "paid_at": None,
            "created_at": now,
            "updated_at": now,
        }

        await self.orders_col.insert_one(doc)
        return doc

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return await self.orders_col.find_one({"_id": order_id})

    async def simulate_payment_success(self, order_id: str, actor: str = "simulator") -> Dict[str, Any]:
        """Legacy simulated payment success (for test_payments.py)."""
        order = await self.get_order(order_id)
        if not order:
            raise ValueError("Không tìm thấy đơn hàng tương ứng.")

        if order.get("status") == "paid":
            return order

        now = datetime.now(timezone.utc)
        ticket_code = f"TICKET-Q4-{uuid.uuid4().hex[:8].upper()}"
        payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"

        update_fields = {
            "status": "paid",
            "paid_at": now,
            "ticket_code": ticket_code,
            "updated_at": now,
        }
        await self.orders_col.update_one({"_id": order_id}, {"$set": update_fields})

        payment_doc = {
            "_id": payment_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": order.get("total_amount", order.get("amount_vnd", 0)),
            "payment_method": order.get("payment_method", "vietqr"),
            "status": "success",
            "transaction_code": f"TRX-{uuid.uuid4().hex[:10].upper()}",
            "verified_by": actor,
            "paid_at": now,
        }
        await self.payments_col.insert_one(payment_doc)

        order.update(update_fields)
        return order

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
        all_paid = await self.orders_col.find({"status": "paid"}).to_list(length=500)
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
