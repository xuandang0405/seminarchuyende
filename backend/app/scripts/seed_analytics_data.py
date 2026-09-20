"""Script to seed realistic initial analytics and ticket sales data so the admin dashboard is immediately rich and informative."""

import asyncio
from datetime import datetime, timezone, timedelta
import random
import uuid

from app.core.database import get_database, connect_to_mongo
from app.db.collections import (
    COLLECTION_ORDERS,
    COLLECTION_ANALYTICS_EVENTS,
    COLLECTION_ANALYTICS_POI_DAILY_METRICS,
    COLLECTION_ANALYTICS_SESSIONS,
    COLLECTION_ANALYTICS_DEVICES,
    COLLECTION_POI,
    COLLECTION_TOURS,
    COLLECTION_ADMIN_USERS,
)


async def seed_analytics():
    await connect_to_mongo()
    db = get_database()
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # 1. Update existing orders to 'paid' and add new paid orders
    orders_col = db[COLLECTION_ORDERS]
    await orders_col.update_many(
        {"status": "pending_payment"},
        {
            "$set": {
                "status": "paid",
                "amount_vnd": 50000,
                "paid_at": now - timedelta(hours=2),
                "updated_at": now,
            }
        }
    )

    # Insert 3 more realistic completed orders
    sample_tours = await db[COLLECTION_TOURS].find({"deleted_at": None}).to_list(5)
    sample_tour_id = sample_tours[0]["_id"] if sample_tours else "tour_d4_culinary"
    sample_tour_title = sample_tours[0].get("title", "Khám Phá Ẩm Thực & Di Sản Quận 4") if sample_tours else "Tour Ẩm Thực Quận 4"

    extra_orders = [
        {
            "_id": f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            "user_id": "usr_tourist_01",
            "tour_id": sample_tour_id,
            "tour_title_snapshot": sample_tour_title,
            "amount_vnd": 79000,
            "currency": "VND",
            "status": "paid",
            "customer_name": "Trần Minh Khoa",
            "customer_email": "khoa.tran@gmail.com",
            "customer_phone": "0912345678",
            "created_at": now - timedelta(days=1),
            "paid_at": now - timedelta(days=1, minutes=5),
            "updated_at": now - timedelta(days=1, minutes=5),
        },
        {
            "_id": f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            "user_id": "usr_tourist_02",
            "tour_id": sample_tour_id,
            "tour_title_snapshot": sample_tour_title,
            "amount_vnd": 79000,
            "currency": "VND",
            "status": "paid",
            "customer_name": "Lê Thu Thảo",
            "customer_email": "thao.le@yahoo.com",
            "customer_phone": "0988776655",
            "created_at": now - timedelta(hours=5),
            "paid_at": now - timedelta(hours=4, minutes=55),
            "updated_at": now - timedelta(hours=4, minutes=55),
        },
        {
            "_id": f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            "user_id": "usr_tourist_03",
            "tour_id": sample_tour_id,
            "tour_title_snapshot": sample_tour_title,
            "amount_vnd": 50000,
            "currency": "VND",
            "status": "pending_payment",
            "customer_name": "John Smith",
            "customer_email": "john.smith@expats.vn",
            "customer_phone": "0933445566",
            "created_at": now - timedelta(minutes=30),
            "updated_at": now - timedelta(minutes=30),
        }
    ]
    for o in extra_orders:
        await orders_col.update_one({"_id": o["_id"]}, {"$set": o}, upsert=True)

    # 2. Seed realistic active sessions and devices
    devices_col = db[COLLECTION_ANALYTICS_DEVICES]
    sessions_col = db[COLLECTION_ANALYTICS_SESSIONS]
    devices = [f"dev_{uuid.uuid4().hex[:8]}" for _ in range(12)]

    import hashlib
    for i, dev_id in enumerate(devices):
        dev_token_hash = hashlib.sha256(dev_id.encode()).hexdigest()
        await devices_col.update_one(
            {"_id": dev_id},
            {
                "$set": {
                    "token_hash": dev_token_hash,
                    "consent_granted": True,
                    "consent_scopes": ["events", "route_sampling"],
                    "last_seen_at": now - timedelta(minutes=random.randint(1, 12)),
                    "platform": "mobile" if i % 2 == 0 else "web",
                    "updated_at": now
                },
                "$setOnInsert": {"created_at": now - timedelta(days=2)}
            },
            upsert=True
        )

        sess_id = f"sess_{dev_id}"
        await sessions_col.update_one(
            {"_id": sess_id},
            {
                "$set": {
                    "session_id": sess_id,
                    "device_id": dev_id,
                    "status": "active" if i < 5 else "idle",
                    "last_seen_at": now - timedelta(minutes=random.randint(1, 10 if i < 5 else 60)),
                    "started_at": now - timedelta(minutes=random.randint(15, 120)),
                    "locale": random.choice(["vi", "vi", "vi", "en", "ja", "ko"]),
                    "updated_at": now
                }
            },
            upsert=True
        )

    # 3. Seed POI metrics and events
    pois = await db[COLLECTION_POI].find({"deleted_at": None}).to_list(100)
    poi_daily_col = db[COLLECTION_ANALYTICS_POI_DAILY_METRICS]
    events_col = db[COLLECTION_ANALYTICS_EVENTS]

    # Pre-defined realistic weights for district 4 top spots
    poi_weights = {
        "poi_ben_nha_rong": (128, 112, 112 * 95000),
        "poi_pho_oc_vinh_khanh": (98, 86, 86 * 75000),
        "poi_cau_mong": (74, 65, 65 * 60000),
        "poi_cho_xom_chieu": (62, 53, 53 * 70000),
        "poi_pha_lau_di_nui": (55, 48, 48 * 65000),
        "poi_nha_tho_xom_chieu": (42, 38, 38 * 80000),
        "poi_cang_sai_gon": (35, 30, 30 * 90000),
        "poi_chua_giac_nguyen": (28, 25, 25 * 55000),
        "poi_dinh_vinh_hoi": (22, 19, 19 * 50000),
        "poi_cong_vien_khanh_hoi": (18, 16, 16 * 45000),
    }

    for p in pois:
        pid = p["_id"]
        started, completed, ms = poi_weights.get(pid, (random.randint(10, 30), random.randint(8, 25), random.randint(300000, 900000)))
        doc_id = f"{pid}_{today_str}"
        dev_sample = random.sample(devices, k=min(len(devices), random.randint(5, 10)))

        await poi_daily_col.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "poi_id": pid,
                    "metric_date": today_str,
                    "listen_started_count": started,
                    "audio_plays": started,
                    "listen_completed_count": completed,
                    "listened_ms": ms,
                    "unique_device_ids": dev_sample,
                    "updated_at": now
                }
            },
            upsert=True
        )

        # Also insert a few sample telemetry events
        for _ in range(3):
            ev_id = str(uuid.uuid4())
            await events_col.update_one(
                {"_id": ev_id},
                {
                    "$set": {
                        "event_id": ev_id,
                        "event_type": random.choice(["audio_play", "narration_completed", "qr_scanned"]),
                        "poi_id": pid,
                        "locale": random.choice(["vi", "vi", "en", "ja"]),
                        "device_id": random.choice(devices),
                        "server_received_at": now - timedelta(minutes=random.randint(5, 180)),
                        "client_occurred_at": now - timedelta(minutes=random.randint(5, 180))
                    }
                },
                upsert=True
            )

    print("Successfully seeded realistic analytics, paid orders, and POI listening metrics!")


if __name__ == "__main__":
    asyncio.run(seed_analytics())
