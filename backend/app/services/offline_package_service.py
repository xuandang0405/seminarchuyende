"""Immutable offline manifests: real sizes/checksums, scoped assets and signed licenses."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import HTTPException
from app.core.config import settings
from app.repositories.base import BaseRepository
from app.repositories.poi_repo import poi_repo
from app.repositories.tour_repo import tour_repo
from app.services.entitlement_service import entitlement_service
from app.services.license_service import sign_license
from app.services.audio_service import audio_service
from app.services.access_service import is_paid_tour
from app.db.collections import COLLECTION_OFFLINE_PACK_MANIFESTS


class OfflinePackageService:
    def __init__(self):
        self.package_repo = BaseRepository(COLLECTION_OFFLINE_PACK_MANIFESTS)

    async def list_packages(self):
        return await self.package_repo.collection.find({}).sort("created_at", -1).to_list(50)

    async def get_package_by_id(self, package_id):
        return await self.package_repo.get_by_id(package_id)

    async def require_access(self, tour_id, user_id):
        tour = await tour_repo.get_public_tour(tour_id)
        if not tour:
            raise HTTPException(404, "Tour không tồn tại.")
        if is_paid_tour(tour) and not await entitlement_service.has_tour_entitlement(user_id, tour_id):
            raise HTTPException(403, "Yêu cầu sở hữu tour để tải gói ngoại tuyến.")
        return tour

    async def generate_tour_package(self, tour_id, language_code="vi"):
        from app.services.translation_service import SUPPORTED_LANGUAGES
        if language_code not in SUPPORTED_LANGUAGES:
            raise HTTPException(422, "Ngôn ngữ không được hỗ trợ.")
        tour = await tour_repo.get_public_tour(tour_id)
        if not tour:
            raise HTTPException(404, "Tour không tồn tại.")
        from app.services.poi_service import poi_service
        pois, files = [], []
        for pid in tour.get("poi_ids", []):
            poi = await poi_repo.get_public_by_id(pid)
            if not poi:
                raise HTTPException(409, "Một điểm dừng chưa sẵn sàng; chưa thể tạo gói.")
            item = await poi_service._resolve_poi_localization(poi, language_code)
            loc = await poi_repo.get_localization_by_lang(pid, item["resolved_lang"])
            if not loc or not loc.get("audio_url") or loc.get("audio_status") != "ready" or (
                loc.get("source_version", 1) != poi.get("content_version", 1)
            ):
                raise HTTPException(409, "Audio chưa sẵn sàng để tải ngoại tuyến.")
            key = loc.get("audio_storage_key") or loc["audio_url"].split("?", 1)[0].removeprefix("/storage/")
            if key.startswith("/api/v1/audio/"):
                key = key.removeprefix("/api/v1/audio/").removesuffix("/stream")
            path = Path(audio_service.get_audio_filepath(key))
            if not path.is_file():
                raise HTTPException(409, "Thiếu file audio; hãy tạo lại audio trước khi đóng gói.")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            aid = hashlib.sha256((pid + ":" + item["resolved_lang"]).encode()).hexdigest()[:20]
            files.append({"asset_id": aid, "poi_id": pid, "kind": "audio", "storage_key": key,
                          "file_size_bytes": path.stat().st_size, "sha256": digest})
            item["audio_asset_id"] = aid
            item["audio_url"] = None
            pois.append(item)
            # Only self-hosted, verified image assets enter an offline pack.
            for image in poi.get("images", []):
                if not image.startswith("/storage/images/"):
                    continue
                relative = image.removeprefix("/storage/")
                base = Path(settings.MEDIA_STORAGE_DIR).resolve()
                image_path = (base / relative).resolve()
                if image_path.is_relative_to(base / "images") and image_path.is_file():
                    iid = hashlib.sha256(relative.encode()).hexdigest()[:20]
                    files.append({"asset_id": iid, "poi_id": pid, "kind": "image", "source_url": image,
                                  "storage_key": relative, "file_size_bytes": image_path.stat().st_size,
                                  "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest()})
        tour_name = tour.get("name") or tour.get("title") or tour_id
        fingerprint = hashlib.sha256(json.dumps({"tour_id": tour_id, "tour_name": tour_name, "tour_version": tour.get("version", 1),
             "lang": language_code, "pois": pois, "files": files}, sort_keys=True, default=str).encode()).hexdigest()
        package_id = "pkg_" + fingerprint[:24]
        existing = await self.get_package_by_id(package_id)
        if existing:
            return existing
        for file in files:
            file["download_url"] = f"/api/v1/packages/{package_id}/assets/{file['asset_id']}"
        manifest = {"package_id": package_id, "tour_id": tour_id, "tour_name": tour_name, "tour_code": tour.get("code", tour_id),
                    "language_code": language_code, "revision": fingerprint, "pois": pois, "files": files,
                    "audio_assets": [f for f in files if f["kind"] == "audio"],
                    "total_files": len(files), "total_bytes": sum(f["file_size_bytes"] for f in files)}
        checksum = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        doc = {"_id": package_id, "tour_id": tour_id, "tour_name": tour.get("name"), "language_code": language_code,
               "version": fingerprint, "source_revision": tour.get("version", 1), "checksum_sha256": checksum,
               "manifest": manifest, "manifest_json": json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str), "total_bytes": manifest["total_bytes"], "created_at": datetime.now(timezone.utc)}
        await self.package_repo.collection.update_one({"_id": package_id}, {"$setOnInsert": doc}, upsert=True)
        return doc

    async def generate_tour_offline_pack_with_license(self, user_id, tour_id, language_code="vi"):
        await self.require_access(tour_id, user_id)
        pack = await self.generate_tour_package(tour_id, language_code)
        now = datetime.now(timezone.utc)
        license = sign_license({"user_id": user_id, "tour_id": tour_id, "package_id": pack["_id"],
            "manifest_sha256": pack["checksum_sha256"], "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=settings.OFFLINE_LICENSE_VALID_DAYS)).isoformat(),
            "valid_days": settings.OFFLINE_LICENSE_VALID_DAYS, "scope": "offline", "status": "valid"})
        return {**pack, "license": license, "offline_license": license}

    async def build_full_package(self, language_code="vi", package_name=None):
        raise HTTPException(422, "Chọn tour cụ thể để đóng gói và kiểm tra quyền truy cập.")


offline_package_service = OfflinePackageService()
