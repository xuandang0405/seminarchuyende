"""Mock Payment Provider for Local & Test Environments.

Section 6 & 12 of prompt.
Rules:
- Strictly restricted to PAYMENT_MODE=mock.
- Explicit label: "MÔ PHỎNG — KHÔNG CHUYỂN TIỀN THẬT".
- Never enabled or accessible in production.
"""

from typing import Any, Dict, Optional
import uuid

from app.core.config import settings
from app.services.payment_providers.base import PaymentProvider


class MockPaymentProvider(PaymentProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    def _ensure_mock_mode_allowed(self):
        if settings.PAYMENT_MODE != "mock":
            raise RuntimeError("Mock payment provider is disabled in production environments!")

    async def create_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any],
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        self._ensure_mock_mode_allowed()

        ref = attempt["provider_reference"]
        amount = order["amount_vnd"]
        title = order.get("tour_title_snapshot", "Tour District 4")

        base_url = return_url.split("?")[0] if return_url else f"{settings.PUBLIC_WEB_URL}/admin/orders"
        mock_checkout_url = f"{base_url}?mock_payment=true&order_id={order['_id']}&ref={ref}"
        mock_qr = f"https://img.vietqr.io/image/970422-0909123456-compact2.png?amount={amount}&addInfo=MOCK-{order['_id']}&accountName=TOURVOICE%20DEMO"

        return {
            "checkout_url": mock_checkout_url,
            "qr_code_data": mock_qr,
            "provider_reference": ref,
            "bank_account_info": {
                "bank_name": "MB Bank (MÔ PHỎNG — KHÔNG CHUYỂN TIỀN THẬT)",
                "account_number": "0909123456",
                "account_name": "TOURVOICE DEMO MOCK",
                "amount": amount,
                "transfer_content": f"MOCK-{order['_id']}"
            },
            "mock_mode": True,
            "notice": "MÔ PHỎNG — KHÔNG CHUYỂN TIỀN THẬT",
            "raw_response": {"status": "mock_created", "ref": ref}
        }

    async def verify_notification(
        self,
        payload: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        self._ensure_mock_mode_allowed()

        ref = payload.get("provider_reference") or payload.get("order_id", "unknown")
        amount = payload.get("amount_vnd") if payload.get("amount_vnd") is not None else payload.get("amount")
        secret_token = payload.get("mock_secret")

        # Basic security check for mock callbacks
        if secret_token and secret_token != "mock_dev_secret":
            return {
                "is_valid": False,
                "outcome": "invalid_signature",
                "provider_reference": ref,
                "provider_transaction_id": None,
                "received_amount_vnd": None,
                "raw_data": payload,
                "error_detail": "Invalid mock secret token"
            }

        return {
            "is_valid": True,
            "outcome": "success",
            "provider_reference": ref,
            "provider_transaction_id": f"MOCK-TX-{uuid.uuid4().hex[:8].upper()}",
            "received_amount_vnd": int(amount) if amount is not None else None,
            "raw_data": payload,
            "error_detail": None
        }

    async def query_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._ensure_mock_mode_allowed()
        return {
            "is_paid": attempt.get("state") == "succeeded",
            "state": attempt.get("state", "pending"),
            "provider_transaction_id": attempt.get("provider_transaction_id") or "MOCK-QUERY-TX",
            "received_amount_vnd": order.get("amount_vnd")
        }


mock_payment_provider = MockPaymentProvider()
