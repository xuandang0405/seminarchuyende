"""Service for Atomic Trial Quota Management.

G02 / BR-TRIAL-01..05.
"""

from typing import Any, Dict, Optional, Tuple
from app.core.config import settings
from app.repositories.trial_repo import trial_repo


class TrialService:
    @property
    def policy_version(self) -> int:
        return settings.TRIAL_POLICY_VERSION

    async def get_trial_status(self, subject_type: str, subject_id: str) -> Dict[str, Any]:
        """Returns the trial quota status for a given subject."""
        usage = await trial_repo.get_or_create_usage(subject_type, subject_id, self.policy_version)
        state = usage.get("state", "available")
        remaining = 1 if state == "available" else 0
        return {
            "trial_remaining": remaining,
            "state": state,
            "reservation_id": usage.get("reservation_id"),
            "consumed_at": usage.get("consumed_at")
        }

    async def reserve_trial_quota(
        self,
        subject_type: str,
        subject_id: str,
        tour_id: str,
        poi_id: str,
        lang: str,
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, Optional[str], str]:
        """Atomically reserves the single trial quota for a narration session."""
        success, res_id, doc = await trial_repo.reserve_quota_atomic(
            subject_type=subject_type,
            subject_id=subject_id,
            policy_version=self.policy_version,
            tour_id=tour_id,
            poi_id=poi_id,
            lang=lang,
            idempotency_key=idempotency_key
        )
        if success:
            return True, res_id, "RESERVED"
        return False, None, "TRIAL_EXHAUSTED"

    async def consume_trial_quota(
        self,
        subject_type: str,
        subject_id: str,
        reservation_id: str,
        playback_id: str
    ) -> bool:
        """Permanently marks the trial quota as consumed upon media delivery."""
        return await trial_repo.consume_quota_atomic(
            subject_type=subject_type,
            subject_id=subject_id,
            policy_version=self.policy_version,
            reservation_id=reservation_id,
            playback_id=playback_id
        )

    async def release_trial_quota(
        self,
        subject_type: str,
        subject_id: str,
        reservation_id: str
    ) -> bool:
        """Rolls back the reservation if media delivery failed before streaming."""
        return await trial_repo.release_quota_atomic(
            subject_type=subject_type,
            subject_id=subject_id,
            policy_version=self.policy_version,
            reservation_id=reservation_id
        )


trial_service = TrialService()
