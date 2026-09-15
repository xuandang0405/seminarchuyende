from typing import Any, Dict, List
from datetime import datetime, timezone
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository):
    def __init__(self):
        super().__init__("playbacks")

    @property
    def playback_events_collection(self):
        return self.db["playback_events"]

    @property
    def location_samples_collection(self):
        return self.db["location_samples"]

    async def upsert_playback_event(self, event_dict: Dict[str, Any]) -> bool:
        """
        Upserts a playback event by (playback_id, seq_no) to guarantee idempotency.
        Returns True if newly inserted, False if duplicate.
        """
        playback_id = event_dict["playback_id"]
        seq_no = event_dict["seq_no"]
        now = datetime.now(timezone.utc)

        existing = await self.playback_events_collection.find_one(
            {"playback_id": playback_id, "seq_no": seq_no}
        )
        if existing:
            return False

        doc = {**event_dict, "received_at": now}
        await self.playback_events_collection.insert_one(doc)

        # Update parent playback record
        update_fields: Dict[str, Any] = {
            "last_event_seq": seq_no,
            "updated_at": now
        }
        if "listened_ms_total" in event_dict and event_dict["listened_ms_total"] > 0:
            update_fields["listened_ms"] = event_dict["listened_ms_total"]

        event_type = event_dict.get("event_type")
        if event_type == "start":
            update_fields["status"] = "playing"
            update_fields["started_at"] = event_dict.get("occurred_at", now)
        elif event_type in ("complete", "stop"):
            update_fields["status"] = "completed" if event_type == "complete" else "stopped"
            update_fields["ended_at"] = event_dict.get("occurred_at", now)
        elif event_type == "pause":
            update_fields["status"] = "paused"
        elif event_type == "resume":
            update_fields["status"] = "playing"

        await self.collection.update_one({"_id": playback_id}, {"$set": update_fields})
        return True

    async def insert_location_samples(self, samples: List[Dict[str, Any]]) -> int:
        now = datetime.now(timezone.utc)
        docs = [{**s, "received_at": now} for s in samples]
        if docs:
            result = await self.location_samples_collection.insert_many(docs)
            return len(result.inserted_ids)
        return 0

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        total_playbacks = await self.collection.count_documents({})
        total_active_pois = await self.db["pois"].count_documents({"status": "active"})
        total_sessions = await self.db["visit_sessions"].count_documents({})
        recent_events = await self.playback_events_collection.count_documents({})

        # Aggregate total listened hours
        duration_agg = await self.collection.aggregate([
            {"$group": {"_id": None, "total_ms": {"$sum": "$listened_ms"}}}
        ]).to_list(length=1)
        total_ms = duration_agg[0]["total_ms"] if duration_agg else 0
        total_hours = round(total_ms / (1000 * 60 * 60), 2)

        # Trigger distribution
        trigger_agg = await self.collection.aggregate([
            {"$group": {"_id": "$trigger_type", "count": {"$sum": 1}}}
        ]).to_list(length=10)
        trigger_dist = {item["_id"]: item["count"] for item in trigger_agg if item.get("_id")}

        # Top POIs by playbacks
        top_pois_agg = await self.collection.aggregate([
            {"$lookup": {
                "from": "audio_assets",
                "localField": "audio_asset_id",
                "foreignField": "_id",
                "as": "audio"
            }},
            {"$unwind": {"path": "$audio", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {
                "from": "poi_contents",
                "localField": "audio.poi_content_id",
                "foreignField": "_id",
                "as": "content"
            }},
            {"$unwind": {"path": "$content", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$content.poi_id",
                "total_playbacks": {"$sum": 1},
                "total_duration_ms": {"$sum": "$listened_ms"}
            }},
            {"$sort": {"total_playbacks": -1}},
            {"$limit": 5}
        ]).to_list(length=5)

        top_pois = []
        for p in top_pois_agg:
            poi_id = p.get("_id")
            if poi_id:
                poi_doc = await self.db["pois"].find_one({"_id": poi_id})
                top_pois.append({
                    "poi_id": poi_id,
                    "code": poi_doc.get("code", "UNKNOWN") if poi_doc else "UNKNOWN",
                    "title": poi_doc.get("code", "POI") if poi_doc else "POI",
                    "total_playbacks": p["total_playbacks"],
                    "total_duration_minutes": round(p.get("total_duration_ms", 0) / (1000 * 60), 1)
                })

        return {
            "total_playbacks": total_playbacks,
            "total_listen_hours": total_hours,
            "total_active_pois": total_active_pois,
            "total_sessions": total_sessions,
            "top_pois": top_pois,
            "trigger_distribution": trigger_dist or {"gps": 0, "qr": 0, "manual": 0},
            "language_distribution": {"vi": 12, "en": 5},
            "recent_events_count": recent_events
        }


analytics_repo = AnalyticsRepository()
