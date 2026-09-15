import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import HTTPException
from app.repositories.base import BaseRepository
from app.repositories.poi_repo import poi_repo
from app.repositories.content_repo import content_repo
from app.repositories.audio_repo import audio_repo


class OfflinePackageService:
    def __init__(self):
        self.package_repo = BaseRepository("tour_packages")
        self.tour_repo = BaseRepository("tours")

    async def generate_tour_package(self, tour_id: str, language_code: str = "vi") -> Dict[str, Any]:
        tour = await self.tour_repo.get_by_id(tour_id)
        if not tour:
            raise HTTPException(status_code=404, detail="Tour not found")

        source_revision = tour.get("content_revision", 1)
        now = datetime.now(timezone.utc)

        # Assemble POIs and associated contents
        stops = tour.get("stops", [])
        poi_ids = [s["poi_id"] for s in stops]

        pois_data = []
        audio_assets_data = []
        total_bytes = 0

        for stop in stops:
            poi = await poi_repo.get_by_id(stop["poi_id"])
            if not poi:
                continue

            # Find matching content for this language
            contents = await content_repo.find_by_poi_and_lang(poi["_id"], language_code, status="approved")
            content_doc = contents[0] if contents else None

            audio_doc = None
            if content_doc:
                audios = await audio_repo.find_by_content_id(content_doc["_id"])
                if audios:
                    audio_doc = audios[0]
                    total_bytes += audio_doc.get("file_size_bytes", 0)
                    audio_assets_data.append({
                        "audio_id": audio_doc["_id"],
                        "poi_id": poi["_id"],
                        "storage_key": audio_doc["storage_key"],
                        "duration_ms": audio_doc["duration_ms"],
                        "file_size_bytes": audio_doc["file_size_bytes"],
                        "sha256": audio_doc["sha256"],
                        "download_url": f"/api/v1/audio/{audio_doc['storage_key']}/stream"
                    })

            pois_data.append({
                "poi_id": poi["_id"],
                "stop_order": stop["stop_order"],
                "code": poi.get("code"),
                "category": poi.get("category"),
                "address": poi.get("address"),
                "location": poi.get("location"),
                "radius_enter_m": poi.get("radius_enter_m"),
                "radius_exit_m": poi.get("radius_exit_m"),
                "cooldown_seconds": poi.get("cooldown_seconds"),
                "priority": poi.get("priority"),
                "image_key": poi.get("image_key"),
                "menu_items": poi.get("menu_items", []),
                "content": {
                    "title": content_doc.get("title") if content_doc else poi.get("code"),
                    "description": content_doc.get("description") if content_doc else "",
                    "narration_text": content_doc.get("narration_text") if content_doc else ""
                } if content_doc else None,
                "audio": audio_doc
            })

        package_id = str(uuid.uuid4())
        manifest = {
            "package_id": package_id,
            "tour_id": tour_id,
            "tour_code": tour.get("code"),
            "language_code": language_code,
            "revision": source_revision,
            "generated_at": now.isoformat(),
            "stops_count": len(pois_data),
            "pois": pois_data,
            "audio_assets": audio_assets_data,
            "total_files": len(audio_assets_data),
            "total_bytes": total_bytes
        }

        package_doc = {
            "_id": package_id,
            "tour_id": tour_id,
            "language_code": language_code,
            "source_revision": source_revision,
            "manifest": manifest,
            "total_bytes": total_bytes,
            "created_at": now
        }

        # Upsert package by (tour_id, language_code, source_revision)
        existing = await self.package_repo.find_one({
            "tour_id": tour_id,
            "language_code": language_code,
            "source_revision": source_revision
        })
        if existing:
            await self.package_repo.update_by_id(existing["_id"], {"manifest": manifest, "total_bytes": total_bytes})
            return await self.package_repo.get_by_id(existing["_id"])
        else:
            await self.package_repo.insert_one(package_doc)
            return package_doc


offline_package_service = OfflinePackageService()
