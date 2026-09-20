"""Schemas for Device Identity, Visitor Sessions, Tour Sessions, and Analytics Events.

Implements BR-DEVICE-*, BR-SESSION-*, BR-TOUR-SESSION-*, BR-LISTEN-*, BR-SYNC-*.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# DEVICE IDENTITY SCHEMAS
# ==============================================================================

class PlatformEnum(str, Enum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"


class DeviceBootstrapRequest(BaseModel):
    device_token: Optional[str] = Field(None, description="Existing device token if available")
    platform: PlatformEnum = Field(default=PlatformEnum.WEB)
    app_version: Optional[str] = Field(default="1.0.0")


class DeviceBootstrapResponse(BaseModel):
    device_id: str = Field(..., description="Public non-sensitive device identifier")
    device_token: str = Field(..., description="Secret bearer/cookie token issued to client")
    created_at: datetime
    is_new: bool = Field(default=False)


# ==============================================================================
# VISITOR SESSION SCHEMAS
# ==============================================================================

class VisitorSessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    EXPIRED = "expired"


class VisitorSessionStartRequest(BaseModel):
    device_token: Optional[str] = None
    platform: PlatformEnum = Field(default=PlatformEnum.WEB)
    app_version: Optional[str] = Field(default="1.0.0")
    locale: str = Field(default="vi")
    consent_granted: bool = Field(default=True)
    consent_version: int = Field(default=1)


class VisitorSessionResponse(BaseModel):
    session_id: str = Field(..., alias="_id")
    device_id: str
    user_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    platform: str
    app_version: Optional[str] = None
    locale: str
    started_at: datetime
    last_seen_at: datetime
    ended_at: Optional[datetime] = None
    status: VisitorSessionStatus
    consent_granted: bool = True
    consent_version: int = 1

    model_config = {
        "populate_by_name": True
    }


# ==============================================================================
# TOUR SESSION SCHEMAS
# ==============================================================================

class TourSessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class TourSessionStartRequest(BaseModel):
    tour_id: str = Field(..., min_length=1)
    visitor_session_id: str = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=1, description="Client UUID for double-click protection")
    start_poi_id: Optional[str] = None


class TourSessionPatchRequest(BaseModel):
    status: Optional[TourSessionStatus] = None
    last_poi_id: Optional[str] = None
    completed_poi_ids: Optional[List[str]] = None
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)


class TourSessionResponse(BaseModel):
    tour_session_id: str = Field(..., alias="_id")
    tour_id: str
    tour_version: int = 1
    visitor_session_id: str
    device_id: str
    user_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    started_at: datetime
    last_activity_at: datetime
    ended_at: Optional[datetime] = None
    status: TourSessionStatus
    start_poi_id: Optional[str] = None
    last_poi_id: Optional[str] = None
    completed_poi_ids: List[str] = Field(default_factory=list)
    progress_percentage: float = 0.0

    model_config = {
        "populate_by_name": True
    }


# ==============================================================================
# ANALYTICS EVENT SCHEMAS & PER-ITEM ACK
# ==============================================================================

class EventTypeEnum(str, Enum):
    NARRATION_REQUESTED = "narration_requested"
    NARRATION_STARTED = "narration_started"
    NARRATION_PROGRESS = "narration_progress"
    NARRATION_PAUSED = "narration_paused"
    NARRATION_RESUMED = "narration_resumed"
    NARRATION_COMPLETED = "narration_completed"
    NARRATION_STOPPED = "narration_stopped"
    NARRATION_FAILED = "narration_failed"
    TOUR_STARTED = "tour_started"
    TOUR_COMPLETED = "tour_completed"
    POI_VIEWED = "poi_viewed"
    QR_SCANNED = "qr_scanned"


class EventItemIn(BaseModel):
    event_id: str = Field(..., min_length=1, description="Client-generated unique event UUID")
    event_type: str = Field(..., description="One of EventTypeEnum or custom milestone")
    playback_id: Optional[str] = None
    visitor_session_id: Optional[str] = None
    tour_session_id: Optional[str] = None
    poi_id: Optional[str] = None
    tour_id: Optional[str] = None
    locale: str = "vi"
    source: str = Field(default="manual", description="'gps', 'qr', 'manual'")
    client_occurred_at: Optional[datetime] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class EventAckStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED_PERMANENT = "rejected_permanent"
    RETRYABLE = "retryable"


class EventAckItem(BaseModel):
    event_id: str
    status: EventAckStatus
    reason: Optional[str] = None


class EventBatchIn(BaseModel):
    events: List[EventItemIn] = Field(..., min_length=1, max_length=100)


class EventBatchResponse(BaseModel):
    total: int
    accepted_count: int
    duplicate_count: int
    rejected_count: int
    acks: List[EventAckItem]
    success_count: Optional[int] = None
    acked_ids: Optional[List[str]] = None


# ==============================================================================
# ADMIN ANALYTICS DASHBOARD SCHEMAS
# ==============================================================================

class AnalyticsOverviewResponse(BaseModel):
    active_visitor_sessions_now: int
    daily_visitor_sessions: int
    unique_devices_count: int
    unique_accounts_count: int
    tour_sessions_started: int
    tour_sessions_completed: int
    tour_completion_rate_percent: float
    listen_started_count: int
    listen_completed_count: int
    listen_completion_rate_percent: float
    average_listening_time_seconds: float
    total_listening_time_minutes: float
    total_revenue_vnd: int = 0
    total_orders_count: int = 0
    paid_orders_count: int = 0
    pending_orders_count: int = 0
    total_registered_users: int = 0
    total_guest_sessions: int = 0
    total_pois_count: int = 0
    total_tours_count: int = 0
    total_qr_scans: int = 0
    revenue_by_tour: List[Dict[str, Any]] = Field(default_factory=list)
    popular_languages: List[Dict[str, Any]] = Field(default_factory=list)
    data_freshness_watermark: datetime
    timezone: str = "Asia/Ho_Chi_Minh"


class TopPoiAnalyticsItem(BaseModel):
    poi_id: str
    name: str
    poi_name: Optional[str] = None
    category: Optional[str] = None
    listen_started_count: int = 0
    listen_completed_count: int = 0
    unique_devices: int = 0
    total_listened_seconds: float = 0.0
    completion_rate_percent: float = 0.0
    avg_listen_duration_seconds: float = 0.0
    total_listen_minutes: float = 0.0


class TourAnalyticsItem(BaseModel):
    tour_id: str
    title: str
    total_sessions: int
    completed_sessions: int
    abandoned_sessions: int
    completion_rate_percent: float
    unique_devices: int
