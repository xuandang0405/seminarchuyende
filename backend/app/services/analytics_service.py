"""Service for Analytics, consent, idempotent event ingestion, and metrics reporting.

F08 / S05 / S06 / S07 / S08 / O10 / SD11 / AD11 / SD12 / AD12 / SD13 / AD13.
Implements BR-LISTEN-01, BR-LISTEN-02, BR-SYNC-01.
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

    async def ingest_events(
        self,
        events: List[Dict[str, Any]],
        inferred_device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return await analytics_repo.ingest_events_batch(
            events,
            inferred_device_id=inferred_device_id
        )

    async def get_overview(self) -> Dict[str, Any]:
        return await analytics_repo.get_admin_overview()

    async def get_top_pois(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await analytics_repo.get_admin_top_pois(limit=limit)

    async def get_tours(self) -> List[Dict[str, Any]]:
        return await analytics_repo.get_admin_tours_analytics()

    async def get_dashboard(self, actor_role: str, actor_id: str) -> Dict[str, Any]:
        """Provides backward-compatible summary for existing dashboard and owner portal."""
        if actor_role in ("super_admin", "admin"):
            return await analytics_repo.get_admin_overview()
        elif actor_role == "poi_owner":
            return await analytics_repo.get_owner_summary(owner_id=actor_id)
        else:
            return {"error": "Unauthorized"}


analytics_service = AnalyticsService()
