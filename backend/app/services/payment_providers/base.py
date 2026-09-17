"""Abstract Payment Provider Interface.

Section 6 & 7 of prompt.
BR-PAY-03..05.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PaymentProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name identifier, e.g., 'vnpay', 'payos', 'mock'."""
        pass

    @abstractmethod
    async def create_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any],
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiates payment transaction with the external provider.

        Returns dict containing:
        - checkout_url: Optional[str]
        - qr_code_data: Optional[str]
        - provider_reference: str
        - raw_response: Dict[str, Any]
        """
        pass

    @abstractmethod
    async def verify_notification(
        self,
        payload: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cryptographically verifies incoming webhook or IPN notification.

        Returns dict containing:
        - is_valid: bool
        - outcome: str ("success", "failed", "invalid_signature", "amount_mismatch")
        - provider_reference: str
        - provider_transaction_id: Optional[str]
        - received_amount_vnd: Optional[int]
        - raw_data: Dict[str, Any]
        - error_detail: Optional[str]
        """
        pass

    @abstractmethod
    async def query_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Directly queries the provider server for the definitive transaction state.

        Returns dict containing:
        - is_paid: bool
        - state: str ("succeeded", "pending", "failed", "unknown")
        - provider_transaction_id: Optional[str]
        - received_amount_vnd: Optional[int]
        """
        pass

    async def cancel_payment(
        self,
        order: Dict[str, Any],
        attempt: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cancels a pending payment transaction if supported by the provider."""
        return {"cancelled": False, "message": "Provider does not support cancellation"}
