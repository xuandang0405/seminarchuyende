import uuid
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from app.repositories.base import BaseRepository
from app.repositories.poi_repo import poi_repo
from app.db.collections import COLLECTION_OFFLINE_PACK_MANIFESTS, COLLECTION_TOURS, COLLECTION_POI


class OfflinePackageService:
    def __init__(self):
        self.package_repo = BaseRepository(COLLECTION_OFFLINE_PACK_MANIFESTS)
        self.tour_repo = BaseRepository(COLLECTION_TOURS)
        self.poi_repo = BaseRepository(COLLECTION_POI)

    async def list_packages(self) -> List[Dict[str, Any]]:
        """Returns list of offline packages. Seeds a default package if empty."""
        cursor = self.package_repo.collection.find({}).sort([("created_at", -1)])
        pkgs = await cursor.to_list(length=50)
        if not pkgs:
            # Auto-seed initial package for District 4
            initial = await self.build_full_package(language_code="vi", package_name="Goi-Offline-Quan-4-Full")
            pkgs = [initial]
        return pkgs

    async def get_package_by_id(self, package_id: str) -> Optional[Dict[str, Any]]:
        return await self.package_repo.get_by_id(package_id)

    async def generate_tour_package(self, tour_id: str, language_code: str = "vi") -> Dict[str, Any]:
        """Generates or retrieves cached package for a given tour and language."""
        tour = await self.tour_repo.get_by_id(tour_id)
        now = datetime.now(timezone.utc)
        tour_name = tour.get("name") if tour else "Tour Quận 4"
        source_revision = tour.get("version", 1) if tour else 1

        # Check existing package
        existing = await self.package_repo.find_one({
            "tour_id": tour_id,
            "language_code": language_code
        })
        if existing:
            return existing

        # Extract POIs
        poi_ids = []
        if tour:
            if tour.get("stops"):
                poi_ids = [s["poi_id"] if isinstance(s, dict) else s for s in tour["stops"]]
            elif tour.get("poi_ids"):
                poi_ids = tour["poi_ids"]

        if not poi_ids:
            # Fallback to public POIs
            pois = await poi_repo.find_public(limit=10)
            poi_ids = [p["_id"] for p in pois]

        pois_data = []
        audio_assets_data = []
        total_bytes = 0

        for idx, p_id in enumerate(poi_ids):
            poi = await poi_repo.get_by_id(p_id) or await poi_repo.get_public_by_id(p_id)
            if not poi:
                continue

            loc = await poi_repo.get_localization_by_lang(p_id, language_code)
            if not loc:
                loc = await poi_repo.get_localization_by_lang(p_id, "vi") or await poi_repo.get_localization_by_lang(p_id, "en")

            audio_doc = None
            if loc and loc.get("audio_url"):
                storage_key = loc.get("audio_storage_key") or f"audio/{p_id}_{language_code}.mp3"
                duration_ms = loc.get("audio_duration_ms", 30000)
                file_size = duration_ms * 16  # Approx size
                total_bytes += file_size
                audio_doc = {
                    "audio_id": loc.get("audio_asset_id") or f"audio_{p_id}_{language_code}",
                    "poi_id": p_id,
                    "storage_key": storage_key,
                    "duration_ms": duration_ms,
                    "file_size_bytes": file_size,
                    "sha256": loc.get("audio_content_hash", "verified_hash_ok"),
                    "download_url": f"/api/v1/audio/{storage_key}/stream"
                }
                audio_assets_data.append(audio_doc)

            enter_r = poi.get("trigger_radius") or poi.get("radius_enter_m", 30.0)
            pois_data.append({
                "poi_id": poi["_id"],
                "stop_order": idx + 1,
                "code": poi.get("code") or poi.get("name"),
                "category": poi.get("category", "attraction"),
                "address": poi.get("address", ""),
                "location": poi.get("location", {"type": "Point", "coordinates": [106.7035, 10.7655]}),
                "radius_enter_m": enter_r,
                "radius_exit_m": poi.get("radius_exit_m") or (enter_r * 1.5),
                "cooldown_seconds": poi.get("cooldown_seconds", 60),
                "image_key": (poi.get("images") or [None])[0] or poi.get("image_key"),
                "content": {
                    "title": loc.get("name") if loc else poi.get("name"),
                    "description": loc.get("description") if loc else poi.get("description"),
                    "narration_text": loc.get("description") if loc else poi.get("description"),
                } if loc else None,
                "audio": audio_doc
            })

        package_id = f"pkg_{uuid.uuid4().hex[:12]}"
        manifest = {
            "package_id": package_id,
            "tour_id": tour_id,
            "tour_code": tour.get("code", tour_id) if tour else tour_id,
            "language_code": language_code,
            "revision": source_revision,
            "generated_at": now.isoformat(),
            "stops_count": len(pois_data),
            "pois": pois_data,
            "audio_assets": audio_assets_data,
            "total_files": len(audio_assets_data),
            "total_bytes": total_bytes
        }

        checksum = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()

        package_doc = {
            "_id": package_id,
            "code": f"PKG-TOUR-{language_code.upper()}",
            "tour_id": tour_id,
            "tour_name": tour_name,
            "language_code": language_code,
            "version": 1,
            "source_revision": source_revision,
            "checksum_sha256": checksum,
            "manifest": manifest,
            "total_bytes": total_bytes,
            "created_at": now
        }

        await self.package_repo.insert_one(package_doc)
        return package_doc

    async def generate_tour_offline_pack_with_license(
        self,
        user_id: str,
        tour_id: str,
        language_code: str = "vi"
    ) -> Dict[str, Any]:
        """Builds offline pack and issues a signed offline license for entitled users (BR-PAY-08)."""
        from app.services.entitlement_service import entitlement_service
        from app.core.config import settings
        from datetime import timedelta
        import hmac

        if not await entitlement_service.has_tour_entitlement(user_id, tour_id):
            raise HTTPException(
                status_code=403,
                detail="Yêu cầu sở hữu tour hợp lệ để tải gói ngoại tuyến."
            )

        pack = await self.generate_tour_package(tour_id, language_code)
        now = datetime.now(timezone.utc)
        valid_days = settings.OFFLINE_LICENSE_VALID_DAYS
        expires_at = now + timedelta(days=valid_days)

        # Generate cryptographic offline license signature
        license_payload = f"{user_id}:{tour_id}:{expires_at.isoformat()}"
        license_signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            license_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        license_doc = {
            "user_id": user_id,
            "tour_id": tour_id,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "valid_days": valid_days,
            "scope": "offline_7days",
            "license_signature": license_signature,
            "status": "valid"
        }

        pack_with_license = dict(pack)
        pack_with_license["offline_license"] = license_doc
        pack_with_license["license"] = license_doc
        return pack_with_license


    async def build_full_package(self, language_code: str = "vi", package_name: Optional[str] = None) -> Dict[str, Any]:
        """Builds offline package containing all public POIs in District 4."""
        now = datetime.now(timezone.utc)
        pois = await poi_repo.find_public(limit=50)

        pois_data = []
        audio_assets_data = []
        total_bytes = 0

        for idx, poi in enumerate(pois):
            p_id = poi["_id"]
            loc = await poi_repo.get_localization_by_lang(p_id, language_code)
            if not loc:
                loc = await poi_repo.get_localization_by_lang(p_id, "vi") or await poi_repo.get_localization_by_lang(p_id, "en")

            audio_doc = None
            if loc and loc.get("audio_url"):
                storage_key = loc.get("audio_storage_key") or f"audio/{p_id}_{language_code}.mp3"
                duration_ms = loc.get("audio_duration_ms", 30000)
                file_size = duration_ms * 16
                total_bytes += file_size
                audio_doc = {
                    "audio_id": loc.get("audio_asset_id") or f"audio_{p_id}_{language_code}",
                    "poi_id": p_id,
                    "storage_key": storage_key,
                    "duration_ms": duration_ms,
                    "file_size_bytes": file_size,
                    "sha256": loc.get("audio_content_hash", "verified_hash_ok"),
                    "download_url": f"/api/v1/audio/{storage_key}/stream"
                }
                audio_assets_data.append(audio_doc)

            enter_r = poi.get("trigger_radius") or poi.get("radius_enter_m", 30.0)
            pois_data.append({
                "poi_id": p_id,
                "stop_order": idx + 1,
                "code": poi.get("code") or poi.get("name"),
                "category": poi.get("category", "attraction"),
                "address": poi.get("address", ""),
                "location": poi.get("location", {"type": "Point", "coordinates": [106.7035, 10.7655]}),
                "radius_enter_m": enter_r,
                "radius_exit_m": poi.get("radius_exit_m") or (enter_r * 1.5),
                "cooldown_seconds": poi.get("cooldown_seconds", 60),
                "image_key": (poi.get("images") or [None])[0] or poi.get("image_key"),
                "content": {
                    "title": loc.get("name") if loc else poi.get("name"),
                    "description": loc.get("description") if loc else poi.get("description"),
                    "narration_text": loc.get("description") if loc else poi.get("description"),
                } if loc else None,
                "audio": audio_doc
            })

        package_id = f"pkg_{uuid.uuid4().hex[:12]}"
        manifest = {
            "package_id": package_id,
            "tour_id": None,
            "tour_code": package_name or "Di-Tich-Am-Thuc-Quan-4",
            "language_code": language_code,
            "revision": 1,
            "generated_at": now.isoformat(),
            "stops_count": len(pois_data),
            "pois": pois_data,
            "audio_assets": audio_assets_data,
            "total_files": len(audio_assets_data),
            "total_bytes": total_bytes
        }

        checksum = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()

        package_doc = {
            "_id": package_id,
            "code": package_name or f"PKG-Q4-{language_code.upper()}",
            "tour_id": None,
            "tour_name": "Toàn Bộ Di Tích & Ẩm Thực Quận 4",
            "language_code": language_code,
            "version": 1,
            "source_revision": 1,
            "checksum_sha256": checksum,
            "manifest": manifest,
            "total_bytes": total_bytes,
            "created_at": now
        }

        await self.package_repo.insert_one(package_doc)
        return package_doc


offline_package_service = OfflinePackageService()
