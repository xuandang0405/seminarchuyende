"""Repository for the 7 analytics collections:
- analytics_devices
- analytics_sessions
- analytics_events
- analytics_poi_daily_metrics
- analytics_daily_metrics
- analytics_hourly_metrics
- analytics_aggregation_jobs
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.repositories.base import BaseRepository
from app.db.collections import (
    COLLECTION_ANALYTICS_DEVICES,
    COLLECTION_ANALYTICS_SESSIONS,
    COLLECTION_ANALYTICS_EVENTS,
    COLLECTION_ANALYTICS_POI_DAILY_METRICS,
    COLLECTION_ANALYTICS_DAILY_METRICS,
    COLLECTION_ANALYTICS_HOURLY_METRICS,
    COLLECTION_ANALYTICS_AGGREGATION_JOBS,
    COLLECTION_POI,
)


class AnalyticsRepository(BaseRepository):
    def __init__(self):
        super().__init__(COLLECTION_ANALYTICS_EVENTS)

    @property
    def devices_col(self):
        return self.db[COLLECTION_ANALYTICS_DEVICES]

    @property
    def sessions_col(self):
        return self.db[COLLECTION_ANALYTICS_SESSIONS]

    @property
    def poi_daily_col(self):
        return self.db[COLLECTION_ANALYTICS_POI_DAILY_METRICS]

    @property
    def daily_col(self):
        return self.db[COLLECTION_ANALYTICS_DAILY_METRICS]

    @property
    def hourly_col(self):
        return self.db[COLLECTION_ANALYTICS_HOURLY_METRICS]

    @property
    def jobs_col(self):
        return self.db[COLLECTION_ANALYTICS_AGGREGATION_JOBS]

    # =========================================================================
    # CONSENT & DEVICES
    # =========================================================================

    async def record_device_consent(
        self,
        device_id: str,
        consent_granted: bool,
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        scopes = scopes or ["events", "route_sampling"]
        doc = {
            "_id": device_id,
            "consent_at": now if consent_granted else None,
            "consent_version": 1,
            "consent_scopes": scopes if consent_granted else [],
            "consent_revoked_at": None if consent_granted else now,
            "last_seen_at": now,
        }
        await self.devices_col.update_one(
            {"_id": device_id},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )
        return doc

    # =========================================================================
    # INGEST EVENTS (analytics_events)
    # =========================================================================

    async def ingest_events_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Idempotent batch ingestion with per-event ACK."""
        now = datetime.now(timezone.utc)
        acked_ids = []
        duplicate_count = 0
        success_count = 0

        for ev in events:
            event_id = ev.get("event_id") or ev.get("_id")
            if not event_id:
                continue

            doc = {
                "_id": event_id,
                "session_id": ev.get("session_id"),
                "poi_id": ev.get("poi_id"),
                "event_type": ev.get("event_type"),
                "occurred_at": ev.get("occurred_at") or now,
                "received_at": now,
                "properties": ev.get("properties") or {},
            }
            try:
                # Upsert by _id (event_id)
                res = await self.collection.update_one(
                    {"_id": event_id},
                    {"$setOnInsert": doc},
                    upsert=True
                )
                if res.upserted_id is not None:
                    success_count += 1
                else:
                    duplicate_count += 1
                acked_ids.append(event_id)
            except Exception:
                pass

        return {
            "success_count": success_count,
            "duplicate_count": duplicate_count,
            "acked_ids": acked_ids
        }

    # =========================================================================
    # AGGREGATION READ MODELS (Daily & POI Daily)
    # =========================================================================

    async def update_poi_daily_metric(
        self,
        poi_id: str,
        metric_date: str,
        env: str,
        additional_plays: int,
        additional_listened_ms: int,
        additional_listens: int
    ) -> Dict[str, Any]:
        doc_id = f"{poi_id}_{metric_date}_{env}"
        now = datetime.now(timezone.utc)
        await self.poi_daily_col.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "poi_id": poi_id,
                    "metric_date": metric_date,
                    "env": env,
                    "updated_at": now
                },
                "$inc": {
                    "audio_plays": additional_plays,
                    "listened_ms": additional_listened_ms,
                    "listens_count": additional_listens,
                }
            },
            upsert=True
        )
        return await self.poi_daily_col.find_one({"_id": doc_id})

    async def get_dashboard_summary(self, env: str = "prod") -> Dict[str, Any]:
        """Aggregate data for admin dashboard."""
        total_events = await self.collection.count_documents({})
        total_pois = await self.db[COLLECTION_POI].count_documents({"is_active": True, "deleted_at": None})

        # Sum from analytics_poi_daily_metrics
        pipeline = [
            {"$group": {
                "_id": None,
                "total_plays": {"$sum": "$audio_plays"},
                "total_ms": {"$sum": "$listened_ms"},
                "total_listens": {"$sum": "$listens_count"}
            }}
        ]
        agg_res = await self.poi_daily_col.aggregate(pipeline).to_list(length=1)
        totals = agg_res[0] if agg_res else {"total_plays": 0, "total_ms": 0, "total_listens": 0}

        total_plays = totals.get("total_plays", 0)
        total_ms = totals.get("total_ms", 0)
        total_listens = totals.get("total_listens", 0)

        # Average duration = total_ms / total_listens (guarding against division by zero)
        avg_duration_sec = round((total_ms / 1000.0) / total_listens, 1) if total_listens > 0 else 0.0

        # Top POIs
        top_pipeline = [
            {"$group": {
                "_id": "$poi_id",
                "audio_plays": {"$sum": "$audio_plays"},
                "listened_ms": {"$sum": "$listened_ms"},
                "listens_count": {"$sum": "$listens_count"}
            }},
            {"$sort": {"audio_plays": -1}},
            {"$limit": 5}
        ]
        top_res = await self.poi_daily_col.aggregate(top_pipeline).to_list(length=5)

        top_pois = []
        for item in top_res:
            pid = item["_id"]
            poi_doc = await self.db[COLLECTION_POI].find_one({"_id": pid})
            poi_name = poi_doc.get("name", pid) if poi_doc else pid
            listens = item.get("listens_count", 0)
            avg_sec = round((item.get("listened_ms", 0) / 1000.0) / listens, 1) if listens > 0 else 0.0
            top_pois.append({
                "poi_id": pid,
                "poi_name": poi_name,
                "audio_plays": item.get("audio_plays", 0),
                "total_minutes": round(item.get("listened_ms", 0) / (1000 * 60), 1),
                "avg_duration_seconds": avg_sec
            })

        return {
            "total_active_pois": total_pois,
            "total_events_ingested": total_events,
            "total_audio_plays": total_plays,
            "total_listen_hours": round(total_ms / (1000 * 3600), 2),
            "avg_listen_duration_seconds": avg_duration_sec,
            "top_pois": top_pois,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_owner_summary(self, owner_id: str) -> Dict[str, Any]:
        """Aggregate stats for POIs belonging to a specific owner (IDOR protection)."""
        owner_pois_cursor = self.db[COLLECTION_POI].find({"owner_id": owner_id, "deleted_at": None})
        owner_pois = await owner_pois_cursor.to_list(length=100)
        owner_poi_ids = [p["_id"] for p in owner_pois]

        if not owner_poi_ids:
            return {
                "owner_id": owner_id,
                "total_pois": 0,
                "audio_plays": 0,
                "total_listen_hours": 0.0,
                "top_pois": []
            }

        pipeline = [
            {"$match": {"poi_id": {"$in": owner_poi_ids}}},
            {"$group": {
                "_id": "$poi_id",
                "plays": {"$sum": "$audio_plays"},
                "listened_ms": {"$sum": "$listened_ms"},
                "listens_count": {"$sum": "$listens_count"}
            }},
            {"$sort": {"plays": -1}}
        ]
        agg_res = await self.poi_daily_col.aggregate(pipeline).to_list(length=100)

        total_plays = sum(item["plays"] for item in agg_res)
        total_ms = sum(item["listened_ms"] for item in agg_res)

        return {
            "owner_id": owner_id,
            "total_pois": len(owner_pois),
            "audio_plays": total_plays,
            "total_listen_hours": round(total_ms / (1000 * 3600), 2),
            "top_pois": [
                {
                    "poi_id": item["_id"],
                    "plays": item["plays"],
                    "minutes": round(item["listened_ms"] / (1000 * 60), 1)
                }
                for item in agg_res[:5]
            ]
        }


analytics_repo = AnalyticsRepository()
