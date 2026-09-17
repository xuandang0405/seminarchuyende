"""Pydantic schemas for Tour Entitlements & Offline License.

Section 8 & 9 of prompt.
BR-PAY-07 / BR-PAY-08.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TourEntitlementResponse(BaseModel):
    entitlement_id: str
    user_id: str
    tour_id: str
    tour_title: str
    source_order_id: str
    status: str  # "active", "revoked"
    granted_at: datetime
    revoked_at: Optional[datetime] = None


class OfflineLicenseResponse(BaseModel):
    tour_id: str
    user_id: str
    entitlement_id: str
    issued_at: datetime
    expires_at: datetime
    signature: str
    allowed_poi_ids: List[str]
    allowed_languages: List[str]
    max_offline_days: int = 7
