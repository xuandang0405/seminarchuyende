"""Payment Providers Package.

Factory function to resolve active provider based on configuration and requested method.
"""

from typing import Optional
from app.core.config import settings
from app.services.payment_providers.base import PaymentProvider
from app.services.payment_providers.vnpay import vnpay_provider
from app.services.payment_providers.payos import payos_provider
from app.services.payment_providers.mock_provider import mock_payment_provider


def get_payment_provider(provider_name: Optional[str] = None, method: Optional[str] = None) -> PaymentProvider:
    """Resolves payment provider by name or payment method.

    Methods:
    - 'visa' -> vnpay_provider (or mock_payment_provider if PAYMENT_MODE == 'mock')
    - 'vietqr' -> payos_provider (or mock_payment_provider if PAYMENT_MODE == 'mock')
    - 'mock' -> mock_payment_provider
    """
    if provider_name == "mock" or (settings.PAYMENT_MODE == "mock" and provider_name is None):
        return mock_payment_provider

    if provider_name == "vnpay" or method == "visa":
        return vnpay_provider

    if provider_name == "payos" or method == "vietqr":
        return payos_provider

    # Fallback to mock if configured
    if settings.PAYMENT_MODE == "mock":
        return mock_payment_provider

    raise ValueError(f"Unsupported payment provider or method: {provider_name or method}")


__all__ = [
    "PaymentProvider",
    "vnpay_provider",
    "payos_provider",
    "mock_payment_provider",
    "get_payment_provider",
]
