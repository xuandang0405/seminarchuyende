"""Service for Analytics, consent, event ingestion, and metrics reporting.

F08 / S05 / S06 / S07 / S08 / O10 / SD11 / AD11 / SD12 / AD12 / SD13 / AD13.
"""

from typing import Any, Dict, List, Optional
from app.repositories.analytics_repo import analytics_repo


class AnalyticsService:
    async def set_device_consent(
        self,
        device_id: str,
        consent: bool,
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        return await analytics_repo.record_device_consent(
            device_id=device_id,
            consent_granted=consent,
            scopes=scopes
        )

    async def ingest_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        return await analytics_repo.ingest_events_batch(events)

    async def get_dashboard(self, actor_role: str, actor_id: str) -> Dict[str, Any]:
        if actor_role in ("super_admin", "admin"):
            return await analytics_repo.get_dashboard_summary()
        elif actor_role == "poi_owner":
            return await analytics_repo.get_owner_summary(owner_id=actor_id)
        else:
            return {"error": "Unauthorized"}


analytics_service = AnalyticsService()
