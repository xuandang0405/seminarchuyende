"""Repository for the analytics collections with idempotent batch ingestion and per-item ACK.

Implements:
- BR-LISTEN-01: listen_started_count increments exactly once per valid playback on first narration_started.
- BR-LISTEN-02: pause/resume/range retry do NOT increment listen count.
- BR-SYNC-01: Idempotent event ingestion returning per-item ACK status (accepted, duplicate, rejected_permanent, retryable).
- Section 17: Admin dashboard metrics with distinct devices and safe non-zero division.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.db.collections import (
    COLLECTION_ANALYTICS_DEVICES,
    COLLECTION_ANALYTICS_SESSIONS,
    COLLECTION_ANALYTICS_EVENTS,
    COLLECTION_ANALYTICS_POI_DAILY_METRICS,
    COLLECTION_ANALYTICS_DAILY_METRICS,
    COLLECTION_ANALYTICS_HOURLY_METRICS,
    COLLECTION_ANALYTICS_AGGREGATION_JOBS,
    COLLECTION_TOUR_SESSIONS,
    COLLECTION_POI,
    COLLECTION_TOURS,
)
from app.repositories.base import BaseRepository


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
    def tour_sessions_col(self):
        return self.db[COLLECTION_TOUR_SESSIONS]

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
        scopes = scopes or (["events", "route_sampling"] if consent_granted else [])
        doc = {
            "consent_granted": consent_granted,
            "consent_version": 1,
            "consent_scopes": scopes,
            "consent_updated_at": now,
            "last_seen_at": now,
        }
        if not consent_granted:
            doc["consent_revoked_at"] = now

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
    # IDEMPOTENT BATCH EVENT INGESTION WITH PER-ITEM ACK
    # =========================================================================

    async def ingest_events_batch(
        self,
        events: List[Dict[str, Any]],
        inferred_device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingests a batch of analytics events idempotently and returns per-item ACKs.
        
        Enforces BR-LISTEN-01 and BR-LISTEN-02 for playback counting.
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        acks: List[Dict[str, Any]] = []
        accepted_count = 0
        duplicate_count = 0
        rejected_count = 0

        for ev in events:
            event_id = ev.get("event_id") or ev.get("_id")
            event_type = ev.get("event_type")

            if not event_id or not event_type:
                acks.append({
                    "event_id": event_id or "unknown",
                    "status": "rejected_permanent",
                    "reason": "Thiếu event_id hoặc event_type bắt buộc."
                })
                rejected_count += 1
                continue

            # Check for deduplication by event_id
            existing_event = await self.collection.find_one({"_id": event_id})
            if existing_event:
                acks.append({
                    "event_id": event_id,
                    "status": "duplicate",
                    "reason": "Sự kiện đã được ghi nhận trước đó."
                })
                duplicate_count += 1
                continue

            # Build validated document
            device_id = inferred_device_id or ev.get("device_id") or "anonymous_device"
            playback_id = ev.get("playback_id")
            poi_id = ev.get("poi_id")
            tour_id = ev.get("tour_id")
            client_time = ev.get("client_occurred_at")

            doc = {
                "_id": event_id,
                "event_id": event_id,
                "event_type": event_type,
                "playback_id": playback_id,
                "visitor_session_id": ev.get("visitor_session_id"),
                "tour_session_id": ev.get("tour_session_id"),
                "device_id": device_id,
                "poi_id": poi_id,
                "tour_id": tour_id,
                "locale": ev.get("locale", "vi"),
                "source": ev.get("source", "manual"),
                "client_occurred_at": client_time or now,
                "server_received_at": now,
                "properties": ev.get("properties") or {},
            }

            try:
                await self.collection.insert_one(doc)
                acks.append({
                    "event_id": event_id,
                    "status": "accepted",
                    "reason": None
                })
                accepted_count += 1
            except Exception as e:
                # Handle unique index race condition
                if "duplicate" in str(e).lower() or "11000" in str(e):
                    acks.append({
                        "event_id": event_id,
                        "status": "duplicate",
                        "reason": "Đã ghi nhận đồng thời."
                    })
                    duplicate_count += 1
                    continue
                else:
                    acks.append({
                        "event_id": event_id,
                        "status": "retryable",
                        "reason": f"Lỗi ghi dữ liệu: {str(e)}"
                    })
                    rejected_count += 1
                    continue

            # =================================================================
            # IDEMPOTENT BUSINESS METRICS COUNTING (BR-LISTEN-01 / BR-LISTEN-02)
            # =================================================================
            if event_type == "narration_started" and poi_id and playback_id:
                # Check if this playback_id has already been counted as started
                prior_start = await self.collection.find_one({
                    "playback_id": playback_id,
                    "event_type": "narration_started",
                    "_id": {"$ne": event_id}
                })
                if not prior_start:
                    # First genuine start for this playback -> increment listen_started_count
                    await self._increment_poi_metrics(
                        poi_id=poi_id,
                        metric_date=date_str,
                        inc_started=1,
                        inc_completed=0,
                        inc_ms=0,
                        device_id=device_id
                    )

            elif event_type == "narration_completed" and poi_id and playback_id:
                # Check if this playback_id has already been counted as completed
                prior_complete = await self.collection.find_one({
                    "playback_id": playback_id,
                    "event_type": "narration_completed",
                    "_id": {"$ne": event_id}
                })
                if not prior_complete:
                    await self._increment_poi_metrics(
                        poi_id=poi_id,
                        metric_date=date_str,
                        inc_started=0,
                        inc_completed=1,
                        inc_ms=0,
                        device_id=device_id
                    )

            elif event_type == "narration_progress" and poi_id:
                # Clamp delta_ms to max 15s to prevent absurd listening times
                props = ev.get("properties") or {}
                raw_delta = props.get("delta_ms", 0)
                if isinstance(raw_delta, (int, float)) and 0 < raw_delta <= 15000:
                    await self._increment_poi_metrics(
                        poi_id=poi_id,
                        metric_date=date_str,
                        inc_started=0,
                        inc_completed=0,
                        inc_ms=int(raw_delta),
                        device_id=device_id
                    )

        return {
            "total": len(events),
            "accepted_count": accepted_count,
            "duplicate_count": duplicate_count,
            "rejected_count": rejected_count,
            "acks": acks,
            "success_count": accepted_count,
            "acked_ids": [a["event_id"] for a in acks if a["status"] in ("accepted", "duplicate")]
        }

    async def _increment_poi_metrics(
        self,
        poi_id: str,
        metric_date: str,
        inc_started: int,
        inc_completed: int,
        inc_ms: int,
        device_id: str
    ):
        """Atomic upsert to analytics_poi_daily_metrics with device tracking."""
        doc_id = f"{poi_id}_{metric_date}"
        now = datetime.now(timezone.utc)
        update_doc: Dict[str, Any] = {
            "$set": {
                "poi_id": poi_id,
                "metric_date": metric_date,
                "updated_at": now
            },
            "$addToSet": {"unique_device_ids": device_id}
        }
        inc_fields: Dict[str, Any] = {}
        if inc_started > 0:
            inc_fields["listen_started_count"] = inc_started
            inc_fields["audio_plays"] = inc_started
        if inc_completed > 0:
            inc_fields["listen_completed_count"] = inc_completed
        if inc_ms > 0:
            inc_fields["listened_ms"] = inc_ms

        if inc_fields:
            update_doc["$inc"] = inc_fields

        await self.poi_daily_col.update_one(
            {"_id": doc_id},
            update_doc,
            upsert=True
        )

    # =========================================================================
    # ADMIN ANALYTICS DASHBOARD READ MODELS
    # =========================================================================

    async def get_admin_overview(self) -> Dict[str, Any]:
        """Calculates system-wide metrics safely for the admin dashboard.
        
        Section 17: Unique devices computed via distinct query, avoiding sum-of-daily duplicates.
        """
        now = datetime.now(timezone.utc)
        inactivity_threshold = now - timedelta(minutes=15)
        start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        # 1. Active visitor sessions in the last 15 minutes
        active_sessions_now = await self.sessions_col.count_documents({
            "status": "active",
            "last_seen_at": {"$gte": inactivity_threshold}
        })

        # 2. Daily visitor sessions today
        daily_sessions = await self.sessions_col.count_documents({
            "started_at": {"$gte": start_of_today}
        })

        # 3. Unique devices count (distinct across visitor sessions)
        distinct_devices = await self.sessions_col.distinct("device_id")
        unique_devices_count = len(distinct_devices)

        # 4. Unique accounts count (distinct user_id where user_id is not null)
        distinct_users = await self.sessions_col.distinct("user_id", {"user_id": {"$ne": None}})
        unique_accounts_count = len(distinct_users)

        # 5. Tour sessions stats
        tour_started_count = await self.tour_sessions_col.count_documents({})
        tour_completed_count = await self.tour_sessions_col.count_documents({"status": "completed"})
        tour_completion_rate = (
            round((tour_completed_count / tour_started_count) * 100.0, 1)
            if tour_started_count > 0 else 0.0
        )

        # 6. Audio listening stats (aggregated across analytics_poi_daily_metrics)
        pipeline = [
            {"$group": {
                "_id": None,
                "total_started": {"$sum": "$listen_started_count"},
                "total_completed": {"$sum": "$listen_completed_count"},
                "total_ms": {"$sum": "$listened_ms"}
            }}
        ]
        agg_res = await self.poi_daily_col.aggregate(pipeline).to_list(length=1)
        totals = agg_res[0] if agg_res else {"total_started": 0, "total_completed": 0, "total_ms": 0}

        listen_started = totals.get("total_started", 0)
        listen_completed = totals.get("total_completed", 0)
        total_ms = totals.get("total_ms", 0)

        listen_completion_rate = (
            round((listen_completed / listen_started) * 100.0, 1)
            if listen_started > 0 else 0.0
        )
        avg_listening_sec = (
            round((total_ms / 1000.0) / listen_started, 1)
            if listen_started > 0 else 0.0
        )
        total_listening_minutes = round(total_ms / (1000.0 * 60.0), 1)

        # 7. Total active POIs for legacy dashboard compatibility
        total_pois = await self.db[COLLECTION_POI].count_documents({"deleted_at": None})

        return {
            "active_visitor_sessions_now": active_sessions_now,
            "daily_visitor_sessions": daily_sessions,
            "unique_devices_count": unique_devices_count,
            "unique_accounts_count": unique_accounts_count,
            "tour_sessions_started": tour_started_count,
            "tour_sessions_completed": tour_completed_count,
            "tour_completion_rate_percent": tour_completion_rate,
            "listen_started_count": listen_started,
            "listen_completed_count": listen_completed,
            "listen_completion_rate_percent": listen_completion_rate,
            "average_listening_time_seconds": avg_listening_sec,
            "avg_listen_duration_seconds": avg_listening_sec,
            "total_listening_time_minutes": total_listening_minutes,
            "total_listen_hours": round(total_ms / (1000 * 3600), 2),
            "total_active_pois": total_pois,
            "total_audio_plays": listen_started,
            "data_freshness_watermark": now.isoformat(),
            "updated_at": now.isoformat(),
            "timezone": "Asia/Ho_Chi_Minh"
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
                "plays": {"$sum": "$listen_started_count"},
                "listened_ms": {"$sum": "$listened_ms"}
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

    async def get_admin_top_pois(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns top POIs ranked by listen_started_count with device count."""
        pipeline = [
            {"$group": {
                "_id": "$poi_id",
                "listen_started": {"$sum": "$listen_started_count"},
                "listen_completed": {"$sum": "$listen_completed_count"},
                "total_ms": {"$sum": "$listened_ms"},
                "all_devices": {"$push": "$unique_device_ids"}
            }},
            {"$sort": {"listen_started": -1}},
            {"$limit": limit}
        ]
        agg_res = await self.poi_daily_col.aggregate(pipeline).to_list(length=limit)

        result: List[Dict[str, Any]] = []
        for item in agg_res:
            pid = item["_id"]
            poi_doc = await self.db[COLLECTION_POI].find_one({"_id": pid})
            poi_name = poi_doc.get("name", pid) if poi_doc else pid
            poi_cat = poi_doc.get("category") if poi_doc else None

            # Flatten device IDs set
            dev_set = set()
            for dev_list in item.get("all_devices", []):
                if isinstance(dev_list, list):
                    dev_set.update(dev_list)

            result.append({
                "poi_id": pid,
                "name": poi_name,
                "category": poi_cat,
                "listen_started_count": item.get("listen_started", 0),
                "listen_completed_count": item.get("listen_completed", 0),
                "unique_devices": len(dev_set),
                "total_listened_seconds": round(item.get("total_ms", 0) / 1000.0, 1)
            })

        return result

    async def get_admin_tours_analytics(self) -> List[Dict[str, Any]]:
        """Returns tour usage analytics by tour."""
        pipeline = [
            {"$group": {
                "_id": "$tour_id",
                "total_sessions": {"$sum": 1},
                "completed_sessions": {
                    "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                },
                "abandoned_sessions": {
                    "$sum": {"$cond": [{"$eq": ["$status", "abandoned"]}, 1, 0]}
                },
                "devices": {"$addToSet": "$device_id"}
            }},
            {"$sort": {"total_sessions": -1}}
        ]
        agg_res = await self.tour_sessions_col.aggregate(pipeline).to_list(length=20)

        result: List[Dict[str, Any]] = []
        for item in agg_res:
            tid = item["_id"]
            tour_doc = await self.db[COLLECTION_TOURS].find_one({"_id": tid})
            title = tour_doc.get("title", tid) if tour_doc else tid
            tot = item.get("total_sessions", 0)
            comp = item.get("completed_sessions", 0)
            rate = round((comp / tot) * 100.0, 1) if tot > 0 else 0.0

            result.append({
                "tour_id": tid,
                "title": title,
                "total_sessions": tot,
                "completed_sessions": comp,
                "abandoned_sessions": item.get("abandoned_sessions", 0),
                "completion_rate_percent": rate,
                "unique_devices": len(item.get("devices", []))
            })

        return result


analytics_repo = AnalyticsRepository()
