"""Centralized AccessService for Content Gating and Playback Grants.

Section 5 & 8 of prompt.
BR-ACCESS-01..03 / BR-TRIAL-01..05 / BR-PAY-07.
"""

from datetime import datetime, timezone, timedelta
import asyncio
import secrets
from typing import Any, Dict, Optional
import uuid
from fastapi import HTTPException

from app.repositories.tour_repo import tour_repo
from app.repositories.poi_repo import poi_repo
from app.repositories.audio_asset_repo import audio_asset_repo
from app.repositories.auth_repo import auth_repo
from app.repositories.playback_grant_repo import playback_grant_repo
from app.services.trial_service import trial_service
from app.services.entitlement_service import entitlement_service
from app.services.audio_service import audio_service
from app.services.rate_limit_service import enforce_rate_limit
from app.services.tts_service import GOOGLE_LANG_MAPPING, tts_service
from app.services.unit_of_work import run_transaction
from pymongo.errors import DuplicateKeyError


def is_paid_tour(tour):
    return bool(tour.get("is_paid") or (tour.get("price_amount") or tour.get("price_vnd") or 0) > 0)


AUDIO_UNAVAILABLE = {
    "success": False,
    "error": "AUDIO_UNAVAILABLE",
    "message": "Chưa tạo được bản thuyết minh. Vui lòng thử lại sau. Lượt nghe thử vẫn còn nếu chưa sử dụng.",
}


class AccessService:
    async def _resolve_narration(self, poi, lang, allow_legacy=False):
        version = poi.get("content_version", 1)
        locs = {loc["lang"]: loc for loc in await poi_repo.get_localizations(poi["_id"])
                if loc.get("lang") and loc.get("source_version", 1) == version}
        published = poi.get("published_contents") or {}
        source_lang = poi.get("source_lang") or "vi"
        languages = dict.fromkeys((lang.lower().split("-", 1)[0], "en", source_lang))
        for language in languages:
            loc = locs.get(language) or {}
            if loc.get("audio_status") == "ready" and audio_service.localization_file_exists(loc):
                key = loc.get("audio_storage_key") or loc["audio_url"]
                return language, self._stream_key(key), None
            content = published.get(language) or {}
            asset_id = content.get("audio_asset_id")
            if asset_id and content.get("source_version", 1) == version:
                asset = await audio_asset_repo.get_by_id(asset_id)
                if asset and asset.get("content_version", 1) == version:
                    key = asset.get("storage_key")
                    if audio_service.localization_file_exists({"audio_storage_key": key}):
                        return language, self._stream_key(key), None
            if allow_legacy and version == 1:
                key = f"audio/{poi['_id']}_{language}.mp3"
                if audio_service.localization_file_exists({"audio_storage_key": key}):
                    return language, key, None

        for language in languages:
            if language not in GOOGLE_LANG_MAPPING:
                continue
            loc = locs.get(language) or {}
            content = published.get(language) or {}
            text = None
            if content.get("source_version", 1) == version:
                text = content.get("narration_text") or content.get("description")
            if not text and loc.get("translation_status") in (None, "ready"):
                text = loc.get("description")
            if not text and language == source_lang:
                text = poi.get("description")
            if text and text.strip():
                digest = tts_service.calculate_content_hash(text, language, "google")
                return language, f"audio/narration_google_{digest}.mp3", text.strip()
        return None

    @staticmethod
    def _stream_key(key):
        return key.split("?", 1)[0].removeprefix("/storage/").removeprefix("/api/v1/audio/").removesuffix("/stream")

    async def _ensure_narration(self, narration, poi, subject_id):
        if not narration:
            return False
        language, key, text = narration
        if not text or audio_service.localization_file_exists({"audio_storage_key": key}):
            return True
        await enforce_rate_limit(f"narration-tts:{subject_id}", 12, 60)
        await enforce_rate_limit("narration-tts", 60, 60)
        try:
            result = await asyncio.wait_for(tts_service.generate_with_google_tts(
                text, language, output_filename=key.removeprefix("audio/")), timeout=25)
        except (OSError, TimeoutError):
            return False
        if not result.get("success") or not audio_service.localization_file_exists({"audio_storage_key": key}):
            return False
        current = await poi_repo.get_public_by_id(poi["_id"])
        return bool(current and current.get("content_version", 1) == poi.get("content_version", 1))

    async def request_poi_grant(self, poi_id, lang, source, consent_trial, user, guest, idempotency_key=None, device_id=None):
        poi = await poi_repo.get_public_by_id(poi_id)
        if not poi:
            raise HTTPException(404, "Địa điểm chưa được công bố.")
        tours = await tour_repo.collection.find({"poi_ids": poi_id, "is_active": True, "deleted_at": None}).sort("_id", 1).to_list(None)
        # A stop offered on a free published tour is public on the map as well.
        if tours and all(is_paid_tour(tour) for tour in tours):
            chosen = next((tour for tour in tours if tour.get("preview_enabled", True)
                           and poi_id in (tour.get("preview_poi_ids") or tour["poi_ids"])), tours[0])
            if user:
                for tour in tours:
                    if await entitlement_service.has_tour_entitlement(user["_id"], tour["_id"]):
                        chosen = tour
                        break
            result = await self.request_playback_grant(chosen["_id"], poi_id, lang, source, consent_trial,
                                                       user=user, guest=guest, idempotency_key=idempotency_key, device_id=device_id)
            if not result.get("success"):
                raise HTTPException(409 if result.get("error") == "AUDIO_UNAVAILABLE" else 403,
                                    {"error_code": result.get("error"), "message": result.get("message"), "tour_id": chosen["_id"]})
            return {**result, "granted": True}
        subject_id = (user or guest)["_id"]
        narration = await self._resolve_narration(poi, lang, allow_legacy=True)
        if not await self._ensure_narration(narration, poi, subject_id):
            raise HTTPException(409, {"error_code": AUDIO_UNAVAILABLE["error"], "message": AUDIO_UNAVAILABLE["message"]})
        lang, key, _ = narration
        token, playback_id = secrets.token_urlsafe(32), str(uuid.uuid4())
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        await playback_grant_repo.create_grant(playback_id=playback_id, grant_token=token,
            subject_type="user" if user else "guest", subject_id=subject_id,
            tour_id="public", poi_id=poi_id, lang=lang, scope="public", asset_storage_key=key, expires_at=expires,
            device_id=device_id, auth_session_id=(user or {}).get("session_id"),
            auth_version=(user or {}).get("auth_version", 1), content_version=poi.get("content_version", 1))
        return {"success": True, "granted": True, "playback_id": playback_id, "grant_token": token,
                "scope": "public", "stream_url": f"/api/v1/audio/{key}/stream?grant_token={token}",
                "tour_id": "public", "poi_id": poi_id, "lang": lang, "expires_at": expires,
                "trial_consumed": False, "message": "Nội dung công khai"}

    async def get_tour_access(
        self,
        tour_id: str,
        user: Optional[Dict[str, Any]] = None,
        guest: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculates unified access permissions for the current subject on a tour."""
        tour = await tour_repo.get_by_id(tour_id)
        if not tour or tour.get("deleted_at") or not tour.get("is_active", True):
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

        is_free = not is_paid_tour(tour)
        if has_entitled or is_free:
            return {
                "tour_id": tour_id,
                "identity_type": identity_type,
                "subject_id": subject_id,
                "trial_remaining": 0,  # Entitled users don't need trial
                "can_preview": True,
                "has_entitlement": has_entitled,
                "can_play_full_tour": True,
                "can_download": bool(user_id),
                "requires_auth_for_purchase": False,
                "reason": "FREE_TOUR" if is_free else "ENTITLED"
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
        guest: Optional[Dict[str, Any]] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authorizes and issues a short-lived playback grant token for narration streaming."""
        # 1. Verify Tour & POI relation
        tour = await tour_repo.get_by_id(tour_id)
        if not tour or tour.get("deleted_at") or not tour.get("is_active", True):
            return {"success": False, "error": "TOUR_NOT_FOUND", "message": "Tour không tồn tại hoặc đã bị ẩn."}

        if poi_id not in tour.get("poi_ids", []):
            return {"success": False, "error": "POI_NOT_IN_TOUR", "message": "Địa điểm không thuộc lộ trình tour này."}

        poi = await poi_repo.get_by_id(poi_id)
        if not poi or poi.get("deleted_at") or not poi.get("is_active", True):
            return {"success": False, "error": "POI_NOT_FOUND", "message": "Địa điểm tham quan không tồn tại."}

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

        narration = await self._resolve_narration(poi, lang, allow_legacy=True)
        if idempotency_key:
            existing = await playback_grant_repo.find_one({"subject_type": subject_type, "subject_id": subject_id,
                "idempotency_key": idempotency_key, "expires_at": {"$gt": datetime.now(timezone.utc)}})
            if existing:
                if not narration:
                    return AUDIO_UNAVAILABLE
                lang, storage_key, _ = narration
                if (existing["poi_id"], existing["tour_id"], existing["lang"], existing["asset_storage_key"],
                    existing.get("auth_session_id"), existing.get("device_id"), existing.get("content_version", 1)) != (
                    poi_id, tour_id, lang, storage_key, (user or {}).get("session_id"), device_id, poi.get("content_version", 1)):
                    return {"success": False, "error": "IDEMPOTENCY_CONFLICT", "message": "Mã yêu cầu đã dùng cho nội dung khác."}
                if not await self._ensure_narration(narration, poi, subject_id):
                    return AUDIO_UNAVAILABLE
                return {"success": True, "playback_id": existing["_id"], "grant_token": existing["grant_token"],
                    "scope": existing["scope"], "stream_url": f"/api/v1/audio/{existing['asset_storage_key']}/stream?grant_token={existing['grant_token']}",
                    "tour_id": existing["tour_id"], "poi_id": poi_id, "lang": lang, "expires_at": existing["expires_at"],
                    "trial_consumed": existing["scope"] == "trial", "message": "Sử dụng lại quyền phát hiện hành."}

        # 2. Check Entitlement
        is_entitled = False
        if user_id:
            is_entitled = await entitlement_service.has_tour_entitlement(user_id, tour_id)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=15)
        playback_id = str(uuid.uuid4())
        grant_token = secrets.token_urlsafe(32)

        is_free = not is_paid_tour(tour)
        if not is_free:
            memberships = tour_repo.collection.find({"poi_ids": poi_id, "is_active": True, "deleted_at": None})
            is_free = any(not is_paid_tour(item) for item in await memberships.to_list(None))
        identity = {"device_id": device_id, "auth_session_id": (user or {}).get("session_id"),
                    "auth_version": (user or {}).get("auth_version", 1), "content_version": poi.get("content_version", 1)}
        if is_entitled or is_free:
            if not await self._ensure_narration(narration, poi, subject_id):
                return AUDIO_UNAVAILABLE
            lang, storage_key, _ = narration
            # Grant full playback without touching trial quota
            await playback_grant_repo.create_grant(
                playback_id=playback_id,
                grant_token=grant_token,
                subject_type=subject_type,
                subject_id=subject_id,
                tour_id=tour_id,
                poi_id=poi_id,
                lang=lang,
                scope="public" if is_free else "entitled",
                asset_storage_key=storage_key,
                expires_at=expires_at, **identity,
            )
            return {
                "success": True,
                "playback_id": playback_id,
                "grant_token": grant_token,
                "scope": "public" if is_free else "entitled",
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
        if (await trial_service.get_trial_status(subject_type, subject_id))["trial_remaining"] == 0:
            return {"success": False, "error": "TRIAL_EXHAUSTED", "message": "Bạn đã sử dụng hết lượt nghe thử. Vui lòng mua vé để nghe tiếp."}
        if not consent_trial:
            return {
                "success": False,
                "error": "TRIAL_CONSENT_REQUIRED",
                "message": "Bạn còn 1 lượt nghe thử miễn phí. Hãy bấm xác nhận để sử dụng lượt nghe thử này."
            }

        if not await self._ensure_narration(narration, poi, subject_id):
            return AUDIO_UNAVAILABLE
        lang, storage_key, _ = narration

        # Rule BR-TRIAL-04: Atomic Quota Reservation
        reserved, reservation_id, _ = await trial_service.reserve_trial_quota(
            subject_type=subject_type,
            subject_id=subject_id,
            tour_id=tour_id,
            poi_id=poi_id,
            lang=lang,
        )
        if not reserved:
            return {
                "success": False,
                "error": "TRIAL_EXHAUSTED",
                "message": "Bạn đã sử dụng hết lượt nghe thử miễn phí. Vui lòng mua tour để tiếp tục nghe."
            }

        async def commit(session):
            try:
                saved = await playback_grant_repo.create_grant(
                    playback_id=playback_id, grant_token=grant_token, subject_type=subject_type,
                    subject_id=subject_id, tour_id=tour_id, poi_id=poi_id, lang=lang, scope="trial",
                    asset_storage_key=storage_key, expires_at=expires_at, idempotency_key=idempotency_key,
                    session=session, **identity,
                )
            except DuplicateKeyError as error:
                raise HTTPException(409, "Mã yêu cầu đã được sử dụng.") from error
            if not saved or saved["_id"] != playback_id:
                raise HTTPException(409, "Mã yêu cầu đã được sử dụng.")
            consumed = await trial_service.consume_trial_quota(
                subject_type, subject_id, reservation_id, playback_id, session=session,
            )
            if not consumed:
                if session is None:
                    await playback_grant_repo.collection.delete_one({"_id": playback_id})
                raise HTTPException(409, "Lượt nghe thử đã thay đổi. Vui lòng thử lại.")
        try:
            await run_transaction(commit)
        except Exception:
            await trial_service.release_trial_quota(subject_type, subject_id, reservation_id)
            raise

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

    async def verify_grant_token(self, grant_token: str, storage_key: str):
        """Validates playback grant token and ensures it matches requested asset."""
        if not grant_token:
            return False
        grant = await playback_grant_repo.get_by_token(grant_token)
        if not grant:
            return False
        session_id = grant.get("auth_session_id")
        if session_id and not await auth_repo.is_session_active(session_id, grant["subject_id"], grant.get("auth_version", 1)):
            return False
        poi = await poi_repo.get_public_by_id(grant["poi_id"])
        if not poi or (grant.get("content_version") is not None and poi.get("content_version", 1) != grant["content_version"]):
            return False
        if grant["scope"] == "entitled" and not await entitlement_service.has_tour_entitlement(grant["subject_id"], grant["tour_id"]):
            return False
        # Verify asset matching or general prefix
        expected = grant.get("asset_storage_key")
        if not expected or audio_service.get_audio_filepath(expected) != audio_service.get_audio_filepath(storage_key):
            return False
        return grant


access_service = AccessService()
