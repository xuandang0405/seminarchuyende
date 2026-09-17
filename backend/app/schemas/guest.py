"""Pydantic schemas for Guest Sessions.

G01 / G03 / BR-ACCESS-02 / BR-ACCESS-04.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class GuestSessionCreateResponse(BaseModel):
    guest_session_id: str
    guest_credential: str
    guest_token: Optional[str] = None
    expires_at: datetime
    message: str = "Phiên khách được tạo thành công."


class GuestClaimRequest(BaseModel):
    guest_credential: str = Field(..., description="Credential ngẫu nhiên của phiên khách cần claim")


class GuestClaimResponse(BaseModel):
    success: bool
    claimed: bool
    guest_session_id: str
    user_id: str
    trial_quota_merged: bool
    trial_remaining: int
    message: str
