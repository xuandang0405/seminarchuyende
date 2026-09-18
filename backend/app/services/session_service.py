"""Service layer coordinating Device bootstrap, Visitor Sessions, and Tour Sessions.

Implements:
- BR-DEVICE-01, BR-DEVICE-02
- BR-SESSION-01
- BR-TOUR-SESSION-01
"""

from typing import Any, Dict, List, Optional, Tuple

from app.repositories.device_repo import device_repo
from app.repositories.session_repo import session_repo
from app.repositories.tour_session_repo import tour_session_repo


class SessionService:
    async def bootstrap_device(
        self,
        device_token: Optional[str] = None,
        platform: str = "web",
        app_version: Optional[str] = "1.0.0"
    ) -> Tuple[Dict[str, Any], str, bool]:
        """Issues or recovers a cryptographic device identity."""
        return await device_repo.get_or_create_device(
            token=device_token,
            platform=platform,
            app_version=app_version
        )

    async def verify_device_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies device token and returns device document if valid."""
        if not token:
            return None
        token_hash = device_repo.hash_token(token.strip())
        return await device_repo.find_by_token_hash(token_hash)

    async def start_or_resume_visitor_session(
        self,
        device_id: str,
        platform: str = "web",
        app_version: Optional[str] = "1.0.0",
        locale: str = "vi",
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        consent_granted: bool = True,
        consent_version: int = 1,
    ) -> Dict[str, Any]:
        """Creates or idempotently resumes an active visitor session within inactivity window."""
        return await session_repo.start_or_resume_session(
            device_id=device_id,
            platform=platform,
            app_version=app_version,
            locale=locale,
            user_id=user_id,
            guest_session_id=guest_session_id,
            consent_granted=consent_granted,
            consent_version=consent_version
        )

    async def heartbeat_visitor_session(
        self,
        session_id: str,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Conditional heartbeat with device ownership verification."""
        return await session_repo.heartbeat(session_id=session_id, device_id=device_id)

    async def end_visitor_session(
        self,
        session_id: str,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Explicitly ends a visitor session."""
        return await session_repo.end_session(session_id=session_id, device_id=device_id)

    async def expire_inactive_sessions(self, timeout_minutes: int = 15) -> int:
        """Background maintenance helper to expire inactive visitor sessions."""
        return await session_repo.expire_inactive_sessions(timeout_minutes=timeout_minutes)

    async def start_tour_session(
        self,
        idempotency_key: str,
        tour_id: str,
        visitor_session_id: str,
        device_id: str,
        start_poi_id: Optional[str] = None,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Starts a tour session with client-provided idempotency_key."""
        return await tour_session_repo.start_tour_session(
            idempotency_key=idempotency_key,
            tour_id=tour_id,
            visitor_session_id=visitor_session_id,
            device_id=device_id,
            start_poi_id=start_poi_id,
            user_id=user_id,
            guest_session_id=guest_session_id
        )

    async def update_tour_progress(
        self,
        tour_session_id: str,
        device_id: str,
        last_poi_id: Optional[str] = None,
        completed_poi_ids: Optional[List[str]] = None,
        progress_percentage: Optional[float] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates tour session progress or status."""
        return await tour_session_repo.update_progress(
            tour_session_id=tour_session_id,
            device_id=device_id,
            last_poi_id=last_poi_id,
            completed_poi_ids=completed_poi_ids,
            progress_percentage=progress_percentage,
            status=status
        )

    async def get_active_tour_session(self, device_id: str) -> Optional[Dict[str, Any]]:
        return await tour_session_repo.get_active_by_device(device_id=device_id)


session_service = SessionService()
