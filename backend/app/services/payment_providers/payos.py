"""payOS VietQR Payment Provider Adapter.

Section 6 & 7 of prompt.
Adheres to payOS specifications:
- Creates dynamic VietQR payment request.
- Computes and verifies HMAC SHA-256 signatures.
- Verifies webhook data integrity.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
from urllib.parse import urlencode
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.services.payment_providers.base import PaymentProvider

logger = logging.getLogger("uvicorn")


class PayOSProvider(PaymentProvider):
    @property
    def provider_name(self) -> str:
        return "payos"

    def _generate_signature(self, data_dict: Dict[str, Any], checksum_key: str) -> str:
        """Sorts dictionary keys alphabetically and generates HMAC-SHA256 signature."""
        sorted_keys = sorted(data_dict.keys())
        canonical_str = "&".join(f"{k}={data_dict[k]}" for k in sorted_keys if data_dict[k] is not None)
        return hmac.new(
            checksum_key.encode("utf-8"),
            canonical_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def create_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any],
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates dynamic VietQR payment request via payOS API."""
        ref_id = attempt["provider_reference"]
        # Generate numeric orderCode (integer up to 9007199254740991)
        numeric_code = int(ref_id) if ref_id.isdecimal() else int(hashlib.sha256(ref_id.encode("utf-8")).hexdigest()[:13], 16)

        amount = int(order["amount_vnd"])
        description = f"Tour {order['_id']}"[:25]
        ret_url = return_url or f"{settings.PUBLIC_WEB_URL.rstrip('/')}/client/?{urlencode({'tour': order['tour_id']})}"
        cancel_url = ret_url

        req_data = {
            "amount": amount,
            "cancelUrl": cancel_url,
            "description": description,
            "orderCode": numeric_code,
            "returnUrl": ret_url,
        }

        if not all((settings.PAYOS_CLIENT_ID, settings.PAYOS_API_KEY, settings.PAYOS_CHECKSUM_KEY)):
            raise RuntimeError("Chưa cấu hình đầy đủ payOS.")
        checksum_key = settings.PAYOS_CHECKSUM_KEY
        signature = self._generate_signature(req_data, checksum_key)
        req_data["signature"] = signature
        if order.get("expires_at"):
            req_data["expiredAt"] = int(order["expires_at"].replace(tzinfo=timezone.utc).timestamp())

        # If live credentials exist and PAYMENT_MODE is live, call payOS API
        if settings.PAYMENT_MODE == "live" and settings.PAYOS_CLIENT_ID and settings.PAYOS_API_KEY:
            headers = {
                "x-client-id": settings.PAYOS_CLIENT_ID,
                "x-api-key": settings.PAYOS_API_KEY,
                "Content-Type": "application/json"
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{settings.PAYOS_ENDPOINT}/v2/payment-requests",
                        json=req_data,
                        headers=headers
                    )
                    res_json = resp.json()
                    if resp.status_code == 200 and res_json.get("code") == "00":
                        data = res_json.get("data", {})
                        return {
                            "checkout_url": data.get("checkoutUrl"),
                            "qr_code_data": data.get("qrCode"),
                            "provider_reference": str(numeric_code),
                            "raw_response": res_json
                        }
            except Exception as e:
                logger.error("payOS live API call failed: %s", type(e).__name__)

        raise RuntimeError("payOS checkout unavailable; no fallback bank account is permitted.")

    async def verify_notification(
        self,
        payload: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verifies webhook signature from payOS."""
        data = payload.get("data", {})
        received_signature = payload.get("signature") or signature

        if not received_signature:
            return {
                "is_valid": False,
                "outcome": "invalid_signature",
                "provider_reference": str(data.get("orderCode", "unknown")),
                "provider_transaction_id": None,
                "received_amount_vnd": None,
                "raw_data": payload,
                "error_detail": "Missing signature in payOS webhook"
            }

        if not settings.PAYOS_CHECKSUM_KEY:
            return {"is_valid": False, "outcome": "invalid_signature", "provider_reference": str(data.get("orderCode", ""))}
        checksum_key = settings.PAYOS_CHECKSUM_KEY
        expected_signature = self._generate_signature(data, checksum_key)

        if not hmac.compare_digest(received_signature.lower(), expected_signature.lower()):
            return {
                "is_valid": False,
                "outcome": "invalid_signature",
                "provider_reference": str(data.get("orderCode", "unknown")),
                "provider_transaction_id": None,
                "received_amount_vnd": None,
                "raw_data": payload,
                "error_detail": "payOS HMAC SHA256 signature mismatch"
            }

        code = data.get("code")
        is_success = (code == "00")
        received_amount = data.get("amount")
        ref = str(data.get("orderCode", ""))
        tx_id = data.get("reference") or f"PAYOS-TX-{ref}"

        return {
            "is_valid": True,
            "outcome": "success" if is_success else "failed",
            "provider_reference": ref,
            "provider_transaction_id": tx_id,
            "received_amount_vnd": int(received_amount) if received_amount else None,
            "raw_data": payload,
            "error_detail": None if is_success else f"payOS code {code}"
        }

    async def query_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query the provider, independently of local webhook delivery."""
        if not settings.PAYOS_CLIENT_ID or not settings.PAYOS_API_KEY:
            raise RuntimeError("payOS credentials are not configured")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.PAYOS_ENDPOINT}/v2/payment-requests/{attempt['provider_reference']}",
                headers={"x-client-id": settings.PAYOS_CLIENT_ID, "x-api-key": settings.PAYOS_API_KEY})
            response.raise_for_status()
            payload = response.json()
        if payload.get("code") != "00":
            raise RuntimeError("payOS could not verify this payment")
        data = payload.get("data") or {}
        return {"is_paid": data.get("status") == "PAID", "state": data.get("status"),
                "received_amount_vnd": data.get("amountPaid"),
                "provider_transaction_id": data.get("id")}


payos_provider = PayOSProvider()
