"""VNPAY Hosted Checkout Payment Provider Adapter.

Section 6 & 7 of prompt.
Adheres to VNPAY specifications:
- Hosted checkout redirect URL.
- HMAC SHA-512 secure hash.
- Amount multiplied by 100 per VNPAY currency protocol.
- Card method 'INTCARD' for International Cards (Visa / Mastercard).
"""

from datetime import datetime, timezone, timedelta
import uuid
import httpx
import hashlib
import hmac
from typing import Any, Dict, Optional
import urllib.parse

from app.core.config import settings
from app.services.payment_providers.base import PaymentProvider


class VNPayProvider(PaymentProvider):
    @property
    def provider_name(self) -> str:
        return "vnpay"

    def _build_query_string(self, params: Dict[str, Any]) -> str:
        """Sorts keys alphabetically and builds URL-encoded query string for hashing."""
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        return urllib.parse.urlencode([(k, str(v)) for k, v in sorted_params if v is not None])

    def _calculate_hash(self, query_string: str) -> str:
        """Computes HMAC-SHA512 hash using secret key."""
        secret = settings.VNPAY_HASH_SECRET.encode("utf-8")
        data = query_string.encode("utf-8")
        return hmac.new(secret, data, hashlib.sha512).hexdigest()

    async def create_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any],
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates VNPAY hosted checkout URL for international card payments."""
        if not settings.is_development and (settings.VNPAY_TMN_CODE == "DEMO" or settings.VNPAY_HASH_SECRET.startswith("DEMO")):
            raise RuntimeError("Chưa cấu hình VNPAY cho môi trường thật.")
        now = datetime.now(timezone(timedelta(hours=7)))
        create_date = now.strftime("%Y%m%d%H%M%S")
        vnp_txn_ref = attempt["provider_reference"]
        
        # VNPAY protocol requires VND amount * 100
        vnp_amount = int(order["amount_vnd"]) * 100

        params = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": settings.VNPAY_TMN_CODE,
            "vnp_Amount": vnp_amount,
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": vnp_txn_ref,
            "vnp_OrderInfo": f"Thanh toan tour {order.get('tour_title_snapshot', '')} #{order['_id']}"[:100],
            "vnp_OrderType": "billpayment",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": return_url or settings.VNPAY_RETURN_URL,
            "vnp_IpAddr": settings.VNPAY_IP_ADDRESS,
            "vnp_CreateDate": create_date,
        }
        if order.get("expires_at"):
            expires = order["expires_at"].replace(tzinfo=timezone.utc).astimezone(now.tzinfo)
            params["vnp_ExpireDate"] = expires.strftime("%Y%m%d%H%M%S")

        # If paying with Visa / International card, set bank code to INTCARD
        if attempt.get("payment_method") == "visa":
            params["vnp_BankCode"] = "INTCARD"

        query_string = self._build_query_string(params)
        secure_hash = self._calculate_hash(query_string)
        checkout_url = f"{settings.VNPAY_PAY_URL}?{query_string}&vnp_SecureHash={secure_hash}"

        return {
            "checkout_url": checkout_url,
            "qr_code_data": None,
            "provider_reference": vnp_txn_ref,
            "raw_response": {"query_params": params, "vnp_SecureHash": secure_hash}
        }

    async def verify_notification(
        self,
        payload: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verifies IPN or Return callback from VNPAY."""
        vnp_params = {k: v for k, v in payload.items() if k.startswith("vnp_")}
        received_hash = vnp_params.pop("vnp_SecureHash", None)
        vnp_params.pop("vnp_SecureHashType", None)

        if not received_hash:
            return {
                "is_valid": False,
                "outcome": "invalid_signature",
                "provider_reference": vnp_params.get("vnp_TxnRef", "unknown"),
                "provider_transaction_id": None,
                "received_amount_vnd": None,
                "raw_data": payload,
                "error_detail": "Missing vnp_SecureHash in payload"
            }

        query_string = self._build_query_string(vnp_params)
        expected_hash = self._calculate_hash(query_string)

        if not hmac.compare_digest(received_hash.lower(), expected_hash.lower()):
            return {
                "is_valid": False,
                "outcome": "invalid_signature",
                "provider_reference": vnp_params.get("vnp_TxnRef", "unknown"),
                "provider_transaction_id": None,
                "received_amount_vnd": None,
                "raw_data": payload,
                "error_detail": "HMAC SHA512 signature mismatch"
            }

        response_code = vnp_params.get("vnp_ResponseCode")
        txn_status = vnp_params.get("vnp_TransactionStatus", response_code)
        raw_amount = vnp_params.get("vnp_Amount")
        
        # Convert amount back from VNPAY * 100 format
        received_amount_vnd = int(raw_amount) // 100 if raw_amount else None
        txn_id = vnp_params.get("vnp_TransactionNo")

        is_success = (response_code == "00" and txn_status == "00")
        outcome = "success" if is_success else "failed"

        return {
            "is_valid": True,
            "outcome": outcome,
            "provider_reference": vnp_params.get("vnp_TxnRef", ""),
            "provider_transaction_id": txn_id,
            "received_amount_vnd": received_amount_vnd,
            "raw_data": payload,
            "error_detail": None if is_success else f"VNPAY error code {response_code}"
        }

    async def query_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Protocol: https://sandbox.vnpayment.vn/apis/docs/truy-van-hoan-tien/querydr%26refund.html
        original = (attempt.get("raw_response") or {}).get("query_params", {})
        if not original.get("vnp_CreateDate"):
            raise RuntimeError("Missing original VNPAY transaction date")
        req = {"vnp_RequestId": uuid.uuid4().hex, "vnp_Version": "2.1.0", "vnp_Command": "querydr",
               "vnp_TmnCode": settings.VNPAY_TMN_CODE, "vnp_TxnRef": attempt["provider_reference"],
               "vnp_TransactionDate": original["vnp_CreateDate"],
               "vnp_CreateDate": datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%d%H%M%S"),
               "vnp_IpAddr": settings.VNPAY_IP_ADDRESS, "vnp_OrderInfo": "Query " + order["_id"]}
        keys = ["vnp_RequestId", "vnp_Version", "vnp_Command", "vnp_TmnCode", "vnp_TxnRef",
                "vnp_TransactionDate", "vnp_CreateDate", "vnp_IpAddr", "vnp_OrderInfo"]
        req["vnp_SecureHash"] = self._calculate_hash("|".join(str(req[k]) for k in keys))
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(settings.VNPAY_API_URL, json=req)
            response.raise_for_status()
            data = response.json()
        keys = ["vnp_ResponseId", "vnp_Command", "vnp_ResponseCode", "vnp_Message", "vnp_TmnCode",
                "vnp_TxnRef", "vnp_Amount", "vnp_BankCode", "vnp_PayDate", "vnp_TransactionNo",
                "vnp_TransactionType", "vnp_TransactionStatus", "vnp_OrderInfo", "vnp_PromotionCode", "vnp_PromotionAmount"]
        expected = self._calculate_hash("|".join(str(data.get(k, "")) for k in keys))
        if not hmac.compare_digest(expected, str(data.get("vnp_SecureHash", "")).lower()):
            raise RuntimeError("Invalid VNPAY query signature")
        if data.get("vnp_TxnRef") != attempt["provider_reference"] or data.get("vnp_TmnCode") != settings.VNPAY_TMN_CODE:
            raise RuntimeError("VNPAY query does not match requested transaction")
        if data.get("vnp_ResponseCode") != "00":
            raise RuntimeError("VNPAY query rejected: " + str(data.get("vnp_ResponseCode")))
        amount = int(data["vnp_Amount"])
        if amount % 100:
            raise RuntimeError("Invalid VNPAY amount")
        return {"is_paid": data.get("vnp_TransactionStatus") == "00",
                "state": data.get("vnp_TransactionStatus"), "received_amount_vnd": amount // 100,
                "provider_transaction_id": data.get("vnp_TransactionNo")}


vnpay_provider = VNPayProvider()
