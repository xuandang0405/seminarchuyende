"""Centralized AccessService for Content Gating and Playback Grants.

Section 5 & 8 of prompt.
BR-ACCESS-01..03 / BR-TRIAL-01..05 / BR-PAY-07.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import secrets
from typing import Any, Dict, Optional, Tuple
import uuid

from app.core.config import settings
from app.repositories.tour_repo import tour_repo
from app.repositories.poi_repo import poi_repo
from app.repositories.audio_repo import audio_repo
from app.repositories.playback_grant_repo import playback_grant_repo
from app.services.trial_service import trial_service
from app.services.entitlement_service import entitlement_service


class AccessService:
    async def get_tour_access(
        self,
        tour_id: str,
        user: Optional[Dict[str, Any]] = None,
        guest: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculates unified access permissions for the current subject on a tour."""
        tour = await tour_repo.get_by_id(tour_id)
        if not tour or not tour.get("is_active", True):
            return {
                "tour_id": tour_id,
                "identity_type": "anonymous",
                "subject_id": None,
                "trial_remaining": 0,
                "can_preview": False,
                "has_entitlement": False,
                "can_play_full_tour": False,
                "can_download": False,
                "requires_auth_for_purchase": True,
                "reason": "TOUR_NOT_FOUND"
            }

        # Resolve subject
        user_id = user.get("_id") if user else None
        guest_id = guest.get("_id") if guest else None

        if user_id:
            subject_type = "user"
            subject_id = user_id
            identity_type = "user"
            requires_auth = False
        elif guest_id:
            subject_type = "guest"
            subject_id = guest_id
            identity_type = "guest"
            requires_auth = True
        else:
            subject_type = "anonymous"
            subject_id = None
            identity_type = "anonymous"
            requires_auth = True

        # 1. Check Tour Entitlement
        has_entitled = False
        if user_id:
            has_entitled = await entitlement_service.has_tour_entitlement(user_id, tour_id)

        if has_entitled:
            return {
                "tour_id": tour_id,
                "identity_type": identity_type,
                "subject_id": subject_id,
                "trial_remaining": 0,  # Entitled users don't need trial
                "can_preview": True,
                "has_entitlement": True,
                "can_play_full_tour": True,
                "can_download": True,
                "requires_auth_for_purchase": False,
                "reason": "ENTITLED"
            }

        # 2. Check Trial Quota
        trial_status = await trial_service.get_trial_status(subject_type, subject_id) if subject_id else {"trial_remaining": 1}
        remaining = trial_status.get("trial_remaining", 0)

        preview_enabled = tour.get("preview_enabled", True)
        can_preview = (remaining > 0) and preview_enabled

        reason = "TRIAL_AVAILABLE" if can_preview else ("TRIAL_EXHAUSTED" if remaining == 0 else "PREVIEW_DISABLED")

        return {
            "tour_id": tour_id,
            "identity_type": identity_type,
            "subject_id": subject_id,
            "trial_remaining": remaining,
            "can_preview": can_preview,
            "has_entitlement": False,
            "can_play_full_tour": False,
            "can_download": False,
            "requires_auth_for_purchase": requires_auth,
            "reason": reason
        }

    async def request_playback_grant(
        self,
        tour_id: str,
        poi_id: str,
        lang: str = "vi",
        trigger_source: str = "manual",
        consent_trial: bool = False,
        idempotency_key: Optional[str] = None,
        user: Optional[Dict[str, Any]] = None,
        guest: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Authorizes and issues a short-lived playback grant token for narration streaming."""
        # 1. Verify Tour & POI relation
        tour = await tour_repo.get_by_id(tour_id)
        if not tour or not tour.get("is_active", True):
            return {"success": False, "error": "TOUR_NOT_FOUND", "message": "Tour không tồn tại hoặc đã bị ẩn."}

        if poi_id not in tour.get("poi_ids", []):
            return {"success": False, "error": "POI_NOT_IN_TOUR", "message": "Địa điểm không thuộc lộ trình tour này."}

        poi = await poi_repo.get_by_id(poi_id)
        if not poi or not poi.get("is_active", True):
            return {"success": False, "error": "POI_NOT_FOUND", "message": "Địa điểm tham quan không tồn tại."}

        # Resolve asset storage key
        pub_content = poi.get("published_contents", {}).get(lang) or poi.get("published_contents", {}).get("vi")
        audio_asset_id = pub_content.get("audio_asset_id") if pub_content else None
        audio_doc = await audio_repo.get_by_id(audio_asset_id) if audio_asset_id else None
        storage_key = audio_doc.get("storage_key") if audio_doc else f"audio/{poi_id}_{lang}.mp3"

        # Resolve subject
        user_id = user.get("_id") if user else None
        guest_id = guest.get("_id") if guest else None

        if user_id:
            subject_type = "user"
            subject_id = user_id
        elif guest_id:
            subject_type = "guest"
            subject_id = guest_id
        else:
            return {"success": False, "error": "UNAUTHENTICATED", "message": "Cần phiên đăng nhập hoặc phiên khách hợp lệ."}

        # 2. Check Entitlement
        is_entitled = False
        if user_id:
            is_entitled = await entitlement_service.has_tour_entitlement(user_id, tour_id)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=15)
        playback_id = str(uuid.uuid4())
        grant_token = secrets.token_urlsafe(32)

        if is_entitled:
            # Grant full playback without touching trial quota
            await playback_grant_repo.create_grant(
                playback_id=playback_id,
                grant_token=grant_token,
                subject_type=subject_type,
                subject_id=subject_id,
                tour_id=tour_id,
                poi_id=poi_id,
                lang=lang,
                scope="entitled",
                asset_storage_key=storage_key,
                expires_at=expires_at
            )
            return {
                "success": True,
                "playback_id": playback_id,
                "grant_token": grant_token,
                "scope": "entitled",
                "stream_url": f"/api/v1/audio/{storage_key}/stream?grant_token={grant_token}",
                "tour_id": tour_id,
                "poi_id": poi_id,
                "lang": lang,
                "expires_at": expires_at,
                "trial_consumed": False,
                "message": "Cấp quyền phát âm thanh thành công (Đã sở hữu tour)."
            }

        # 3. Handle Free Trial (Not Entitled)
        # Check preview eligibility
        if not tour.get("preview_enabled", True):
            return {
                "success": False,
                "error": "TOUR_PURCHASE_REQUIRED",
                "message": "Tour này không mở nghe thử miễn phí, vui lòng mua tour để nghe."
            }

        allowed_preview_pois = tour.get("preview_poi_ids") or tour.get("poi_ids", [])
        if poi_id not in allowed_preview_pois:
            return {
                "success": False,
                "error": "TOUR_PURCHASE_REQUIRED",
                "message": "Điểm tham quan này không nằm trong danh mục nghe thử miễn phí. Vui lòng mua tour."
            }

        # Rule BR-TRIAL-03: User consent required (GPS cannot burn trial silently)
        if not consent_trial:
            return {
                "success": False,
                "error": "TRIAL_CONSENT_REQUIRED",
                "message": "Bạn còn 1 lượt nghe thử miễn phí. Hãy bấm xác nhận để sử dụng lượt nghe thử này."
            }

        # Rule BR-TRIAL-04: Atomic Quota Reservation
        reserved, reservation_id, reason = await trial_service.reserve_trial_quota(
            subject_type=subject_type,
            subject_id=subject_id,
            tour_id=tour_id,
            poi_id=poi_id,
            lang=lang,
            idempotency_key=idempotency_key
        )
        if not reserved:
            return {
                "success": False,
                "error": "TRIAL_EXHAUSTED",
                "message": "Bạn đã sử dụng hết lượt nghe thử miễn phí. Vui lòng mua tour để tiếp tục nghe."
            }

        # Create playback grant
        await playback_grant_repo.create_grant(
            playback_id=playback_id,
            grant_token=grant_token,
            subject_type=subject_type,
            subject_id=subject_id,
            tour_id=tour_id,
            poi_id=poi_id,
            lang=lang,
            scope="trial",
            asset_storage_key=storage_key,
            expires_at=expires_at
        )

        # Rule BR-TRIAL-05: Mark trial as consumed immediately upon first media authorization
        await trial_service.consume_trial_quota(
            subject_type=subject_type,
            subject_id=subject_id,
            reservation_id=reservation_id,
            playback_id=playback_id
        )

        return {
            "success": True,
            "playback_id": playback_id,
            "grant_token": grant_token,
            "scope": "trial",
            "stream_url": f"/api/v1/audio/{storage_key}/stream?grant_token={grant_token}",
            "tour_id": tour_id,
            "poi_id": poi_id,
            "lang": lang,
            "expires_at": expires_at,
            "trial_consumed": True,
            "message": "Cấp quyền nghe thử miễn phí thành công."
        }

    async def verify_grant_token(self, grant_token: str, storage_key: str) -> bool:
        """Validates playback grant token and ensures it matches requested asset."""
        if not grant_token:
            return False
        grant = await playback_grant_repo.get_by_token(grant_token)
        if not grant:
            return False
        # Verify asset matching or general prefix
        expected = grant.get("asset_storage_key")
        if expected and not storage_key.endswith(expected.split("/")[-1]):
            return False
        # Mark streaming delivery
        await playback_grant_repo.mark_delivery(grant["_id"])
        return True


access_service = AccessService()
