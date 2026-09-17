"""Pydantic schemas for Tour Access & Playback Grants.

Section 5 & 10 of prompt.
BR-ACCESS-01 / BR-TRIAL-01..05.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TourAccessResponse(BaseModel):
    tour_id: str
    identity_type: str  # "guest", "user", "anonymous"
    subject_id: Optional[str] = None
    trial_remaining: int
    can_preview: bool
    has_entitlement: bool
    can_play_full_tour: bool
    can_download: bool
    requires_auth_for_purchase: bool
    reason: str  # "ENTITLED", "TRIAL_AVAILABLE", "TRIAL_EXHAUSTED", "TOUR_NOT_PURCHASABLE", etc.


class PlaybackGrantRequest(BaseModel):
    tour_id: str = Field(..., description="ID của tour chứa POI")
    poi_id: str = Field(..., description="ID của POI cần phát thuyết minh")
    lang: str = Field("vi", description="Mã ngôn ngữ (vi, en, zh, ja)")
    language: Optional[str] = None
    trigger_source: str = Field("manual", description="Nguồn kích hoạt: manual, gps, qr")
    trigger_type: Optional[str] = None
    consent_trial: bool = Field(False, description="Xác nhận đồng ý dùng lượt nghe thử nếu chưa mua tour")
    user_consent_trial: Optional[bool] = None
    idempotency_key: Optional[str] = Field(None, description="Khóa chống trùng lặp")

    def model_post_init(self, __context):
        if self.language:
            self.lang = self.language
        if self.trigger_type:
            self.trigger_source = self.trigger_type
        if self.user_consent_trial is not None:
            self.consent_trial = self.user_consent_trial


class PlaybackGrantResponse(BaseModel):
    success: bool
    granted: bool = True
    playback_id: str
    grant_token: str
    scope: str  # "trial" hoặc "entitled"
    stream_url: str
    tour_id: str
    poi_id: str
    lang: str
    expires_at: datetime
    trial_consumed: bool = False
    message: str
