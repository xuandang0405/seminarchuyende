from typing import List, Dict, Any
from pydantic import BaseModel


class TopPoiStat(BaseModel):
    poi_id: str
    code: str
    title: str
    total_playbacks: int
    total_duration_minutes: float


class AnalyticsDashboardResponse(BaseModel):
    total_playbacks: int
    total_listen_hours: float
    total_active_pois: int
    total_sessions: int
    top_pois: List[TopPoiStat]
    trigger_distribution: Dict[str, int]
    language_distribution: Dict[str, int]
    recent_events_count: int
