"""Pydantic schemas for Orders & Checkout.

Section 6, 7 & 10 of prompt.
BR-PAY-01..06.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    tour_id: str = Field(..., description="ID của tour muốn mua")
    idempotency_key: Optional[str] = Field(None, description="Khóa chống trùng lặp tạo đơn")
    customer_name: Optional[str] = Field(None, description="Tên người mua hiển thị trên hóa đơn/vé")
    customer_phone: Optional[str] = Field(None, description="Số điện thoại liên hệ")


class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    tour_id: str
    tour_title: str
    amount_vnd: int
    currency: str = "VND"
    pricing_version: int
    status: str  # "pending_payment", "paid", "cancelled", "expired", "requires_review"
    idempotency_key: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    paid_at: Optional[datetime] = None


class PaymentAttemptCreateRequest(BaseModel):
    payment_method: str = Field(..., description="Phương thức: 'visa' (VNPAY) hoặc 'vietqr' (payOS)")
    return_url: Optional[str] = Field(None, description="URL chuyển hướng sau khi thanh toán")


class PaymentAttemptResponse(BaseModel):
    attempt_id: str
    order_id: str
    provider: str  # "vnpay", "payos", "mock"
    payment_method: str
    provider_reference: str
    amount_vnd: int
    currency: str = "VND"
    state: str
    checkout_url: Optional[str] = None
    qr_code_data: Optional[str] = None
    bank_account_info: Optional[Dict[str, Any]] = None
    mock_mode: bool = False
    message: str


class OrderReconcileResponse(BaseModel):
    order_id: str
    status: str
    is_paid: bool
    attempt_state: Optional[str] = None
    provider_reference: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    entitlement_granted: bool = False
    message: str
