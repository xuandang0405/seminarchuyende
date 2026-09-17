"""Repository for Payment Webhook/IPN Events Ledger.

Section 7 & 9 of prompt.
BR-PAY-04 / BR-PAY-05.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from app.db.collections import COLLECTION_PAYMENT_EVENTS
from app.repositories.base import BaseRepository


class PaymentEventRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_PAYMENT_EVENTS)

    async def get_event(self, provider: str, event_key: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"provider": provider, "event_key": event_key})

    async def record_event(
        self,
        provider: str,
        event_key: str,
        provider_reference: str,
        outcome: str,
        payload_hash: str,
        processing_state: str = "processed",
        error_detail: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": str(uuid.uuid4()),
            "provider": provider,
            "event_key": event_key,
            "provider_reference": provider_reference,
            "verified_outcome": outcome,
            "payload_hash": payload_hash,
            "processing_state": processing_state,
            "error_detail": error_detail,
            "received_at": now,
            "processed_at": now
        }
        await self.insert_one(doc)
        return doc


payment_event_repo = PaymentEventRepository()
