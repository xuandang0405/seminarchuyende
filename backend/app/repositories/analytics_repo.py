"""Repository for the analytics collections with idempotent batch ingestion and per-item ACK.

Implements:
- BR-LISTEN-01: listen_started_count increments exactly once per valid playback on first narration_started.
- BR-LISTEN-02: pause/resume/range retry do NOT increment listen count.
- BR-SYNC-01: Idempotent event ingestion returning per-item ACK status (accepted, duplicate, rejected_permanent, retryable).
- Section 17: Admin dashboard metrics with distinct devices and safe non-zero division.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.db.collections import (
    COLLECTION_ANALYTICS_DEVICES,
    COLLECTION_ANALYTICS_SESSIONS,
    COLLECTION_ANALYTICS_EVENTS,
    COLLECTION_ANALYTICS_POI_DAILY_METRICS,
    COLLECTION_ANALYTICS_DAILY_METRICS,
    COLLECTION_ANALYTICS_HOURLY_METRICS,
    COLLECTION_ANALYTICS_AGGREGATION_JOBS,
    COLLECTION_RUNTIME_WEB_PRESENCE,
    COLLECTION_RUNTIME_AUDIO_DAILY,
    COLLECTION_TOUR_SESSIONS,
    COLLECTION_POI,
    COLLECTION_TOURS,
    COLLECTION_ORDERS,
    COLLECTION_ADMIN_USERS,
    COLLECTION_GUEST_SESSIONS,
    COLLECTION_PLAYBACK_GRANTS,
)
from app.repositories.base import BaseRepository
from app.services.unit_of_work import run_transaction

LISTEN_METRICS = {
    "narration_started": "started", "audio_play": "started",
    "narration_completed": "completed", "audio_completed": "completed",
    "narration_progress": "progress", "audio_progress": "progress",
}


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

    @property
    def runtime_audio_col(self):
        return self.db[COLLECTION_RUNTIME_AUDIO_DAILY]

    async def update_web_presence(self, lease_id: str, active: bool):
        leases = self.db[COLLECTION_RUNTIME_WEB_PRESENCE]
        if active:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=45)
            await leases.update_one({"_id": lease_id}, {"$max": {"expires_at": expiry}}, upsert=True)
        else:
            await leases.delete_one({"_id": lease_id})

    async def record_runtime_listen(self, token: str, listened_ms: int, completed: bool):
        """Count an authorized playback without collecting a device or visitor history."""
        now = datetime.now(timezone.utc)
        grants = self.db[COLLECTION_PLAYBACK_GRANTS]
        query = {"grant_token": token, "expires_at": {"$gt": now},
                 "first_delivered_at": {"$type": "date"}}
        grant = await grants.find_one(query)
        if not grant:
            raise HTTPException(404, "Phiên phát chưa được xác thực hoặc đã hết hạn.")
        if grant.get("device_id"):
            return  # Opt-in playback is counted by the verified analytics event batch.

        delivered = grant["first_delivered_at"].replace(tzinfo=timezone.utc)
        elapsed_ms = max(0, int((now - delivered).total_seconds() * 1000))
        position = min(listened_ms, elapsed_ms + 2000)
        finished = completed and position > 0

        async def commit(session):
            kwargs = {"session": session} if session else {}
            previous = await grants.find_one_and_update(
                {**query, "_id": grant["_id"], "metric_completed": {"$ne": True}},
                {"$max": {"metric_listened_ms": position},
                 "$set": {"metric_started": True, **({"metric_completed": True} if finished else {})}},
                **kwargs,
            )
            if not previous:
                return
            increments = {
                "listen_started_count": int(not previous.get("metric_started")),
                "listen_completed_count": int(finished),
                "listened_ms": max(0, position - (previous.get("metric_listened_ms") or 0)),
            }
            if any(increments.values()):
                day = delivered.strftime("%Y-%m-%d")
                poi_id, lang = grant["poi_id"], grant["lang"]
                await self.runtime_audio_col.update_one(
                    {"_id": f"{poi_id}_{day}_{lang}"},
                    {"$setOnInsert": {"poi_id": poi_id, "metric_date": day, "locale": lang}, "$inc": increments},
                    upsert=True, **kwargs,
                )

        await run_transaction(commit)

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
        scopes = (scopes if scopes is not None else ["events", "route_sampling"]) if consent_granted else []
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
            {"$set": doc},
        )
        if not consent_granted:
            await self.sessions_col.update_many({"device_id": device_id, "status": "active"},
                {"$set": {"status": "ended", "ended_at": now, "updated_at": now}})
            await self.tour_sessions_col.update_many({"device_id": device_id, "status": "active"},
                {"$set": {"status": "abandoned", "ended_at": now, "updated_at": now}})
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
            metric = LISTEN_METRICS.get(event_type)
            grant_filter = {"_id": playback_id, "device_id": device_id, "poi_id": poi_id,
                            "first_delivered_at": {"$type": "date"}, "expires_at": {"$gt": now}}
            grant = None
            if metric:
                grant = await self.db[COLLECTION_PLAYBACK_GRANTS].find_one(grant_filter) if playback_id and poi_id else None
                if not grant:
                    rejected_count += 1
                    acks.append({"event_id": event_id, "status": "rejected_permanent", "reason": "PLAYBACK_NOT_VERIFIED"})
                    continue

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

            async def persist(session=None):
                kwargs = {"session": session} if session else {}
                try:
                    await self.collection.insert_one(doc, **kwargs)
                except DuplicateKeyError as error:
                    raise HTTPException(409, "Sự kiện đã tồn tại.") from error
                if metric:
                    await self._count_verified_listen(metric, grant, grant_filter, doc, date_str, now, session)

            try:
                if metric:
                    await run_transaction(persist)
                else:
                    await persist()
                acks.append({
                    "event_id": event_id,
                    "status": "accepted",
                    "reason": None
                })
                accepted_count += 1
            except Exception as error:
                if isinstance(error, HTTPException) and error.status_code == 409:
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
                        "reason": "Chưa ghi được sự kiện. Có thể gửi lại."
                    })
                    rejected_count += 1
                    continue

        return {
            "total": len(events),
            "accepted_count": accepted_count,
            "duplicate_count": duplicate_count,
            "rejected_count": rejected_count,
            "acks": acks,
            "success_count": accepted_count,
            "acked_ids": [a["event_id"] for a in acks if a["status"] in ("accepted", "duplicate")]
        }

    async def _count_verified_listen(self, metric, grant, query, event, date_str, now, session=None):
        started = completed = delta = 0
        if metric == "progress":
            raw = event["properties"].get("delta_ms", 0)
            if type(raw) not in (int, float) or not 0 < raw <= 15000:
                return
            elapsed = int((now - grant["first_delivered_at"].replace(tzinfo=timezone.utc)).total_seconds() * 1000)
            delta = int(raw)
            if delta < 1 or elapsed + 2000 < delta:
                return
            query.update(metric_started=True, metric_completed={"$ne": True}, **{"$or": [
                {"metric_listened_ms": None}, {"metric_listened_ms": {"$lte": elapsed + 2000 - delta}},
            ]})
            update = {"$inc": {"metric_listened_ms": delta}}
        else:
            flag = "metric_" + metric
            query[flag] = {"$ne": True}
            if metric == "completed":
                query["metric_started"] = True
            started, completed = int(metric == "started"), int(metric == "completed")
            update = {"$set": {flag: True}}
        result = await self.db[COLLECTION_PLAYBACK_GRANTS].update_one(
            query, update, **({"session": session} if session else {}),
        )
        if result.modified_count:
            await self._increment_poi_metrics(grant["poi_id"], date_str, started, completed, delta, grant["device_id"], session)

    async def _increment_poi_metrics(
        self,
        poi_id: str,
        metric_date: str,
        inc_started: int,
        inc_completed: int,
        inc_ms: int,
        device_id: str,
        session=None,
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
            upsert=True, **({"session": session} if session else {}),
        )

    # =========================================================================
    # ADMIN ANALYTICS DASHBOARD READ MODELS
    # =========================================================================

    async def _listen_rollup(self, group_by=None, match=None, include_devices=False):
        fields = {"_id": group_by, "started": {"$sum": "$listen_started_count"},
                  "completed": {"$sum": "$listen_completed_count"}, "ms": {"$sum": "$listened_ms"}}
        if include_devices:
            fields["device_lists"] = {"$push": "$unique_device_ids"}
        pipeline = ([{"$match": match}] if match else []) + [{"$group": fields}]
        streams = await asyncio.gather(*(self.aggregate_to_list(col, pipeline, length=None)
                                         for col in (self.poi_daily_col, self.runtime_audio_col)))
        totals = {}
        for rows in streams:
            for row in rows:
                target = totals.setdefault(row["_id"], {"started": 0, "completed": 0, "ms": 0, "devices": set()})
                for field in ("started", "completed", "ms"):
                    target[field] += row[field]
                for devices in row.get("device_lists", []):
                    if isinstance(devices, list):
                        target["devices"].update(devices)
        return totals

    async def get_admin_overview(self) -> Dict[str, Any]:
        """Calculates system-wide metrics safely for the admin dashboard.
        
        Section 17: Unique devices computed via distinct query, avoiding sum-of-daily duplicates.
        """
        now = datetime.now(timezone.utc)
        inactivity_threshold = now - timedelta(minutes=15)
        start_of_today = now.astimezone(timezone(timedelta(hours=7))).replace(hour=0, minute=0, second=0, microsecond=0)
        (live_web_sessions, active_devices, daily_sessions, distinct_devices, distinct_users,
         tour_started_count, tour_completed_count, rollup) = await asyncio.gather(
            self.db[COLLECTION_RUNTIME_WEB_PRESENCE].count_documents({"expires_at": {"$gt": now}}),
            self.sessions_col.distinct("device_id", {"status": "active", "last_seen_at": {"$gte": inactivity_threshold}}),
            self.sessions_col.count_documents({"started_at": {"$gte": start_of_today}}),
            self.sessions_col.distinct("device_id"),
            self.sessions_col.distinct("user_id", {"user_id": {"$ne": None}}),
            self.tour_sessions_col.count_documents({}),
            self.tour_sessions_col.count_documents({"status": "completed"}),
            self._listen_rollup(),
        )
        unique_devices_count = len(distinct_devices)
        unique_accounts_count = len(distinct_users)
        tour_completion_rate = (
            round((tour_completed_count / tour_started_count) * 100.0, 1)
            if tour_started_count > 0 else 0.0
        )

        totals = rollup.get(None, {})
        listen_started = totals.get("started", 0)
        listen_completed = totals.get("completed", 0)
        total_ms = totals.get("ms", 0)

        listen_completion_rate = (
            round((listen_completed / listen_started) * 100.0, 1)
            if listen_started > 0 else 0.0
        )
        avg_listening_sec = (
            round((total_ms / 1000.0) / listen_started, 1)
            if listen_started > 0 else 0.0
        )
        total_listening_minutes = round(total_ms / (1000.0 * 60.0), 1)

        # 7. Orders & Ticket Sales Revenue
        orders_col = self.db[COLLECTION_ORDERS]
        revenue_pipeline = [
            {"$match": {"status": "paid"}},
            {"$group": {"_id": {"$ifNull": ["$tour_id", "tour_standard"]},
                        "title": {"$first": "$tour_title_snapshot"}, "paid_orders": {"$sum": 1},
                        "revenue_vnd": {"$sum": "$amount_vnd"}}},
            {"$sort": {"revenue_vnd": -1, "_id": 1}},
        ]
        lang_pipeline = [
            {"$match": {"event_type": {"$in": ["narration_started", "audio_play"]},
                        "locale": {"$ne": None}, "playback_id": {"$ne": None}}},
            {"$group": {"_id": "$playback_id", "locale": {"$first": "$locale"}}},
            {"$group": {"_id": "$locale", "count": {"$sum": 1}}},
        ]
        runtime_lang_pipeline = [{"$group": {"_id": "$locale", "count": {"$sum": "$listen_started_count"}}}]
        (revenue, total_orders_count, pending_orders_count, total_registered_users, total_guest_sessions,
         total_pois, total_tours, total_qr_scans, lang_agg, runtime_langs) = await asyncio.gather(
            self.aggregate_to_list(orders_col, revenue_pipeline, length=None),
            orders_col.count_documents({}),
            orders_col.count_documents({"status": {"$in": ["pending", "pending_payment"]}}),
            self.db[COLLECTION_ADMIN_USERS].count_documents({"role": "user"}),
            self.db[COLLECTION_GUEST_SESSIONS].count_documents({}),
            self.db[COLLECTION_POI].count_documents({"deleted_at": None}),
            self.db[COLLECTION_TOURS].count_documents({"deleted_at": None}),
            self.collection.count_documents({"event_type": {"$in": ["qr_scanned", "qr_scan"]}}),
            self.aggregate_to_list(self.collection, lang_pipeline, length=None),
            self.aggregate_to_list(self.runtime_audio_col, runtime_lang_pipeline, length=None),
        )
        revenue_by_tour = [{"tour_id": row["_id"], "title": row["title"] or row["_id"],
                            "paid_orders": row["paid_orders"], "revenue_vnd": row["revenue_vnd"]} for row in revenue]
        total_revenue_vnd = sum(row["revenue_vnd"] for row in revenue)
        paid_orders_count = sum(row["paid_orders"] for row in revenue)
        languages = {}
        for item in lang_agg + runtime_langs:
            code = item["_id"]
            if code:
                languages[code] = languages.get(code, 0) + item["count"]
        popular_languages = [{"code": code, "count": count} for code, count in
                             sorted(languages.items(), key=lambda item: (-item[1], item[0]))[:6]]

        return {
            "live_web_sessions": live_web_sessions,
            "active_visitor_sessions_now": len(active_devices),
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
            "total_listened_seconds": round(total_ms / 1000, 1),
            "total_listen_hours": round(total_ms / (1000 * 3600), 2),
            "total_active_pois": total_pois,
            "total_pois_count": total_pois,
            "total_tours_count": total_tours,
            "total_qr_scans": total_qr_scans,
            "total_revenue_vnd": total_revenue_vnd,
            "total_orders_count": total_orders_count,
            "paid_orders_count": paid_orders_count,
            "pending_orders_count": pending_orders_count,
            "total_registered_users": total_registered_users,
            "total_guest_sessions": total_guest_sessions,
            "revenue_by_tour": revenue_by_tour,
            "popular_languages": popular_languages,
            "total_audio_plays": listen_started,
            "data_freshness_watermark": now.isoformat(),
            "updated_at": now.isoformat(),
            "timezone": "Asia/Ho_Chi_Minh"
        }

    async def get_owner_summary(self, owner_id: str) -> Dict[str, Any]:
        """Aggregate stats for POIs belonging to a specific owner (IDOR protection)."""
        owner_pois_cursor = self.db[COLLECTION_POI].find({"owner_id": owner_id, "deleted_at": None})
        owner_pois = await owner_pois_cursor.to_list(length=100)
        owner_poi_ids = [str(p["_id"]) for p in owner_pois]

        rollup = await self._listen_rollup("$poi_id", {"poi_id": {"$in": owner_poi_ids}}, include_devices=True) if owner_poi_ids else {}
        top_pois = self._rank_poi_metrics(owner_pois, rollup)
        total_plays = sum(item["started"] for item in rollup.values())
        completed = sum(item["completed"] for item in rollup.values())
        total_ms = sum(item["ms"] for item in rollup.values())

        return {
            "owner_id": owner_id,
            "total_pois": len(owner_pois),
            "total_pois_count": len(owner_pois),
            "audio_plays": total_plays,
            "listen_started_count": total_plays,
            "listen_completed_count": completed,
            "listen_completion_rate_percent": round(completed / total_plays * 100, 1) if total_plays else 0.0,
            "total_listened_seconds": round(total_ms / 1000, 1),
            "total_listen_hours": round(total_ms / (1000 * 3600), 2),
            "top_pois": [
                {
                    **item,
                    "plays": item["listen_started_count"],
                    "minutes": item["total_listen_minutes"],
                }
                for item in top_pois[:5]
            ]
        }

    async def get_admin_top_pois(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns all POIs ranked by listen_started_count with device count and completion rates."""
        pois, metrics = await asyncio.gather(
            self.db[COLLECTION_POI].find({"deleted_at": None}).to_list(None),
            self._listen_rollup("$poi_id", include_devices=True),
        )
        return self._rank_poi_metrics(pois, metrics)[:limit]

    @staticmethod
    def _rank_poi_metrics(pois, metrics):
        result: List[Dict[str, Any]] = []
        for p in pois:
            pid = str(p["_id"])
            name = p.get("name", pid)
            cat = p.get("category", "sightseeing")
            m = metrics.get(pid, {})
            started = m.get("started", 0)
            completed = m.get("completed", 0)
            total_sec = round(m.get("ms", 0) / 1000.0, 1)
            comp_rate = round((completed / started * 100.0), 1) if started > 0 else 0.0
            avg_duration = round(total_sec / started, 1) if started > 0 else 0.0

            result.append({
                "poi_id": pid,
                "name": name,
                "poi_name": name,
                "category": cat,
                "listen_started_count": started,
                "listen_completed_count": completed,
                "unique_devices": len(m.get("devices", ())),
                "total_listened_seconds": total_sec,
                "completion_rate_percent": comp_rate,
                "avg_listen_duration_seconds": avg_duration,
                "total_listen_minutes": round(total_sec / 60.0, 1)
            })

        # Sort by listen_started_count descending, then by name
        result.sort(key=lambda item: (-item["listen_started_count"], -item["listen_completed_count"], item["name"], str(item["poi_id"])))
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
        agg_res = await self.aggregate_to_list(self.tour_sessions_col, pipeline, length=20)

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
