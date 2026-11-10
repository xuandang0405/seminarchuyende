"""Repository for Orders and Payment Attempts.

Section 7 & 9 of prompt.
BR-PAY-01..06.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import uuid

from app.db.collections import COLLECTION_ORDERS, COLLECTION_PAYMENT_ATTEMPTS
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_ORDERS)

    @property
    def attempt_collection(self):
        return self.db[COLLECTION_PAYMENT_ATTEMPTS]

    async def create_order(
        self,
        user_id: str,
        tour_id: str,
        tour_title: str,
        amount_vnd: int,
        pricing_version: int,
        idempotency_key: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        expires_minutes: int = 30
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        checkout_key = hashlib.sha256(f"{user_id}:{tour_id}".encode()).hexdigest()
        query = {"user_id": user_id, "tour_id": tour_id, "$or": [
            {"status": "requires_review"},
            {"status": {"$in": ["pending", "pending_payment"]}, "expires_at": {"$gt": now}},
        ]}
        await self.collection.update_many(
            {"checkout_key": checkout_key, "status": {"$in": ["pending", "pending_payment"]}, "expires_at": {"$lte": now}},
            {"$set": {"status": "expired", "updated_at": now}, "$unset": {"checkout_key": ""}},
        )
        existing = await self.collection.find_one(query, sort=[("created_at", -1)])
        if existing:
            return existing
        order_id = f"ORD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        doc = {
            "_id": order_id,
            "user_id": user_id,
            "tour_id": tour_id,
            "tour_title_snapshot": tour_title,
            "amount_vnd": amount_vnd,
            "currency": "VND",
            "pricing_version": pricing_version,
            "status": "pending_payment",  # pending_payment, paid, cancelled, expired, requires_review
            "idempotency_key": idempotency_key,
            "checkout_key": checkout_key,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "created_at": now,
            "expires_at": now + timedelta(minutes=expires_minutes),
            "paid_at": None,
            "updated_at": now
        }
        from pymongo.errors import DuplicateKeyError
        try:
            await self.insert_one(doc)
        except DuplicateKeyError:
            if idempotency_key:
                existing = await self.get_by_user_and_idempotency(user_id, idempotency_key)
                if existing and existing["tour_id"] == tour_id:
                    return existing
            active = await self.collection.find_one(query, sort=[("created_at", -1)])
            if active:
                return active
            raise
        return doc

    async def get_by_user_and_idempotency(self, user_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"user_id": user_id, "idempotency_key": idempotency_key})

    async def list_user_orders(self, user_id: str, skip: int = 0, limit: int = 50, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {"user_id": user_id}
        if status_filter:
            query["status"] = status_filter
        return await self.list(query=query, skip=skip, limit=limit, sort=[("created_at", -1)])

    async def list_all_orders(self, skip: int = 0, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {}
        if status:
            query["status"] = status
        return await self.list(query=query, skip=skip, limit=limit, sort=[("created_at", -1)])

    async def update_order_status(
        self,
        order_id: str,
        status: str,
        paid_at: Optional[datetime] = None,
        session=None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update_doc = {"status": status, "updated_at": now}
        if paid_at:
            update_doc["paid_at"] = paid_at
        kwargs = {"session": session} if session else {}
        query = {"_id": order_id}
        if status != "paid":
            query["status"] = {"$ne": "paid"}
        update = {"$set": update_doc}
        if status in ("paid", "expired", "cancelled"):
            update["$unset"] = {"checkout_key": ""}
        await self.collection.update_one(query, update, **kwargs)
        return await self.collection.find_one({"_id": order_id}, **kwargs)

    async def mark_order_cancelled(self, order_id: str) -> bool:
        """Cancels a pending order. Strictly rejects if order is already paid (Rule BR-PAY-03)."""
        order = await self.get_by_id(order_id)
        if not order or order.get("status") == "paid":
            return False
        res = await self.collection.update_one({"_id": order_id, "status": {"$in": ["pending", "pending_payment"]}},
            {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}, "$unset": {"checkout_key": ""}})
        return res.modified_count > 0

    # =========================================================================
    # PAYMENT ATTEMPTS
    # =========================================================================

    async def create_payment_attempt(
        self,
        order_id: str,
        provider: str,
        payment_method: str,
        provider_reference: str,
        expected_amount_vnd: int,
        checkout_url: Optional[str] = None,
        qr_code_data: Optional[str] = None,
        raw_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        attempt_id = str(uuid.uuid4())
        doc = {
            "_id": attempt_id,
            "order_id": order_id,
            "provider": provider,
            "payment_method": payment_method,
            "provider_reference": provider_reference,
            "provider_transaction_id": None,
            "expected_amount_vnd": expected_amount_vnd,
            "received_amount_vnd": None,
            "state": "pending",  # created, pending, unknown, succeeded, failed, cancelled, expired
            "checkout_url": checkout_url,
            "qr_code_data": qr_code_data,
            "raw_response": raw_response,
            "created_at": now,
            "completed_at": None,
            "updated_at": now
        }
        await self.attempt_collection.insert_one(doc)
        return doc

    async def get_attempt_by_ref(self, provider: str, provider_reference: str) -> Optional[Dict[str, Any]]:
        return await self.attempt_collection.find_one({
            "provider": provider,
            "provider_reference": provider_reference
        })

    async def get_latest_attempt_for_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.attempt_collection.find({"order_id": order_id}).sort("created_at", -1).limit(1)
        results = await cursor.to_list(length=1)
        return results[0] if results else None

    async def update_attempt_state(
        self,
        attempt_id: str,
        state: str,
        provider_transaction_id: Optional[str] = None,
        received_amount_vnd: Optional[int] = None,
        session=None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update_doc = {"state": state, "updated_at": now}
        if state in ("succeeded", "failed", "cancelled", "expired"):
            update_doc["completed_at"] = now
        if provider_transaction_id:
            update_doc["provider_transaction_id"] = provider_transaction_id
        if received_amount_vnd is not None:
            update_doc["received_amount_vnd"] = received_amount_vnd

        kwargs = {"session": session} if session else {}
        query = {"_id": attempt_id}
        if state != "succeeded":
            query["state"] = {"$ne": "succeeded"}
        await self.attempt_collection.update_one(query, {"$set": update_doc}, **kwargs)
        return await self.attempt_collection.find_one({"_id": attempt_id}, **kwargs)


order_repo = OrderRepository()
