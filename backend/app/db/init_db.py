import asyncio
import logging
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.security import get_password_hash

logger = logging.getLogger("uvicorn")

COLLECTIONS = [
    "admin_users",
    "languages",
    "pois",
    "poi_contents",
    "audio_assets",
    "tours",
    "qr_codes",
    "content_jobs",
    "tour_packages",
    "visit_sessions",
    "playbacks",
    "playback_events",
    "location_samples",
]


async def init_database():
    """Initializes MongoDB collections, indexes, and initial seed data."""
    client = AsyncIOMotorClient(settings.mongodb_connection_string)
    db = client[settings.DATABASE_NAME]

    existing_collections = await db.list_collection_names()
    logger.info(f"Existing collections in '{settings.DATABASE_NAME}': {existing_collections}")

    for coll_name in COLLECTIONS:
        if coll_name not in existing_collections:
            try:
                await db.create_collection(coll_name)
                logger.info(f"Created collection '{coll_name}'.")
            except Exception as e:
                logger.warning(f"Could not create collection '{coll_name}': {e}")

    # ================= INDEXES =================
    try:
        # admin_users
        await db["admin_users"].create_index([("email", 1)], unique=True, name="uq_admin_email")

        # pois
        await db["pois"].create_index([("code", 1)], unique=True, name="uq_poi_code")
        await db["pois"].create_index([("location", "2dsphere")], name="idx_poi_location_2dsphere")

        # poi_contents
        await db["poi_contents"].create_index(
            [("poi_id", 1), ("language_code", 1), ("version", 1)],
            unique=True,
            name="uq_poi_content_version"
        )
        await db["poi_contents"].create_index([("source_content_id", 1)], name="idx_poi_source_content")

        # audio_assets
        await db["audio_assets"].create_index([("storage_key", 1)], unique=True, name="uq_audio_storage_key")
        await db["audio_assets"].create_index([("poi_content_id", 1)], name="idx_audio_poi_content")

        # tours
        await db["tours"].create_index([("code", 1)], unique=True, name="uq_tour_code")
        await db["tours"].create_index([("stops.poi_id", 1)], name="idx_tour_stops_poi")

        # qr_codes
        await db["qr_codes"].create_index([("poi_id", 1)], name="idx_qr_poi")

        # content_jobs
        await db["content_jobs"].create_index([("idempotency_key", 1)], unique=True, name="uq_job_idempotency")
        await db["content_jobs"].create_index([("status", 1), ("created_at", 1)], name="idx_job_status_created")
        await db["content_jobs"].create_index([("input_content_id", 1)], name="idx_job_input_content")

        # tour_packages
        await db["tour_packages"].create_index(
            [("tour_id", 1), ("language_code", 1), ("source_revision", 1)],
            unique=True,
            name="uq_tour_package"
        )

        # visit_sessions
        await db["visit_sessions"].create_index([("tour_id", 1), ("started_at", 1)], name="idx_session_tour")

        # playbacks
        await db["playbacks"].create_index([("session_id", 1), ("started_at", 1)], name="idx_pb_session")
        await db["playbacks"].create_index([("audio_asset_id", 1), ("started_at", 1)], name="idx_pb_audio")
        await db["playbacks"].create_index([("qr_code_id", 1)], name="idx_pb_qr")

        # playback_events
        await db["playback_events"].create_index(
            [("playback_id", 1), ("seq_no", 1)],
            unique=True,
            name="uq_playback_event_seq"
        )

        # location_samples
        await db["location_samples"].create_index([("session_id", 1), ("recorded_at", 1)], name="idx_loc_session")
        await db["location_samples"].create_index([("location", "2dsphere")], name="idx_loc_2dsphere")

        logger.info("Successfully configured all MongoDB indexes.")
    except Exception as e:
        logger.warning(f"Note on index creation: {e}")

    # ================= SEED INITIAL MASTER DATA =================
    now = datetime.now(timezone.utc)

    # 1. Languages
    default_languages = [
        {"_id": "vi", "name": "Tiếng Việt", "native_name": "Tiếng Việt", "is_enabled": True, "created_at": now, "updated_at": now},
        {"_id": "en", "name": "English", "native_name": "English", "is_enabled": True, "created_at": now, "updated_at": now},
        {"_id": "zh", "name": "Chinese", "native_name": "中文", "is_enabled": True, "created_at": now, "updated_at": now},
        {"_id": "ja", "name": "Japanese", "native_name": "日本語", "is_enabled": True, "created_at": now, "updated_at": now},
        {"_id": "ko", "name": "Korean", "native_name": "한국어", "is_enabled": True, "created_at": now, "updated_at": now},
        {"_id": "fr", "name": "French", "native_name": "Français", "is_enabled": True, "created_at": now, "updated_at": now},
    ]
    for lang in default_languages:
        await db["languages"].update_one(
            {"_id": lang["_id"]},
            {"$setOnInsert": lang},
            upsert=True
        )

    # 2. Default Super Admin
    admin = await db["admin_users"].find_one({"email": settings.SUPERADMIN_EMAIL})
    admin_id = str(uuid.uuid4())
    if not admin:
        admin_doc = {
            "_id": admin_id,
            "email": settings.SUPERADMIN_EMAIL,
            "full_name": "TourVoice Super Administrator",
            "password_hash": get_password_hash(settings.SUPERADMIN_PASSWORD),
            "role": "super_admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        await db["admin_users"].insert_one(admin_doc)
        logger.info(f"Created default Super Admin user: {settings.SUPERADMIN_EMAIL}")
    else:
        admin_id = admin["_id"]

    # 3. Seed Sample POIs for District 4 (Quận 4, TP.HCM)
    sample_pois = [
        {
            "code": "Q4-BEN-NHA-RONG",
            "category": "attraction",
            "address": "01 Nguyễn Tất Thành, Phường 12, Quận 4, TP. Hồ Chí Minh",
            "location": {"type": "Point", "coordinates": [106.70678, 10.76814]},
            "radius_enter_m": 40,
            "radius_exit_m": 80,
            "cooldown_seconds": 120,
            "priority": 10,
            "status": "active",
            "revision": 1,
            "image_key": "https://images.unsplash.com/photo-1583417319070-4a69db38a482?w=800",
            "vi_title": "Bến Nhà Rồng - Bảo Tàng Hồ Chí Minh",
            "vi_desc": "Nơi người thanh niên Nguyễn Tất Thành ra đi tìm đường cứu nước năm 1911.",
            "vi_narration": "Chào mừng bạn đến với Bến Nhà Rồng, một trong những biểu tượng lịch sử thiêng liêng bên dòng sông Sài Gòn. Được xây dựng từ năm 1863 theo kiến trúc Pháp với đôi rồng ngự trên nóc, nơi đây vào ngày 5 tháng 6 năm 1911, người thanh niên yêu nước Nguyễn Tất Thành đã bước lên con tàu Amiral Latouche-Tréville ra đi tìm đường cứu nước.",
            "en_title": "Nha Rong Harbor - Ho Chi Minh Museum",
            "en_desc": "The historic harbor where President Ho Chi Minh departed in 1911.",
            "en_narration": "Welcome to Nha Rong Harbor, an iconic historical landmark situated alongside the Saigon River. Constructed in 1863 with classic French architecture crowned by rooftop dragon sculptures, this was the exact place where Nguyen Tat Thanh set sail on June 5, 1911 on his quest for national independence."
        },
        {
            "code": "Q4-PHO-OC-VINH-KHANH",
            "category": "food",
            "address": "Đường Vĩnh Khánh, Phường 9, Quận 4, TP. Hồ Chí Minh",
            "location": {"type": "Point", "coordinates": [106.70012, 10.75882]},
            "radius_enter_m": 35,
            "radius_exit_m": 70,
            "cooldown_seconds": 90,
            "priority": 8,
            "status": "active",
            "revision": 1,
            "image_key": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800",
            "vi_title": "Phố Ẩm Thực Vĩnh Khánh",
            "vi_desc": "Khu phố ẩm thực đêm trứ danh Quận 4 với hàng chục quán ốc và hải sản tươi sống.",
            "vi_narration": "Bạn đang đứng tại Phố ẩm thực Vĩnh Khánh, thiên đường ăn đêm sầm uất bậc nhất Sài Gòn. Khi hoàng hôn buông xuống, cả con phố rực sáng ánh đèn và dậy mùi thơm nức mũi của ốc hương nướng mỡ hành, ốc móng tay xào rau muống và càng ghẹ rang muối ớt đậm đà.",
            "en_title": "Vinh Khanh Seafood & Street Food Street",
            "en_desc": "The most vibrant night food street in District 4 famous for fresh snails and seafood.",
            "en_narration": "You are standing at Vinh Khanh Street, one of the liveliest culinary streets in Saigon. As dusk falls, the street springs to life with aroma from grilled scallops, garlic butter snails, and spicy tamarind crabs."
        },
        {
            "code": "Q4-CHO-XOM-CHIEU",
            "category": "food",
            "address": "Đường Lê Quốc Hưng, Phường 12, Quận 4, TP. Hồ Chí Minh",
            "location": {"type": "Point", "coordinates": [106.70425, 10.76135]},
            "radius_enter_m": 30,
            "radius_exit_m": 65,
            "cooldown_seconds": 90,
            "priority": 7,
            "status": "active",
            "revision": 1,
            "image_key": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
            "vi_title": "Chợ Xóm Chiếu - 'Kinh Đô Ăn Vặt' Quận 4",
            "vi_desc": "Khu chợ truyền thống lâu đời với các món mì hến, phá lấu bò và chè trứ danh.",
            "vi_narration": "Chào mừng bạn đến với Chợ Xóm Chiếu, nơi được mệnh danh là 'kinh đô ăn vặt' của Quận 4. Tại đây, bạn nhất định phải thử món phá lấu bò cốt dừa béo ngậy kèm bánh mì giòn tan, hay tô mì hến cay nồng xé lưỡi chuẩn vị miền Trung.",
            "en_title": "Xom Chieu Market - Street Snack Capital",
            "en_desc": "Historic local market famous for pha lau, clams noodles, and traditional desserts.",
            "en_narration": "Welcome to Xom Chieu Market, fondly crowned the street snack capital of District 4. Don't miss savoring hot coconut beef stew (pha lau) dipped with crusty baguettes or spicy baby clam noodles."
        },
        {
            "code": "Q4-CAU-MONG",
            "category": "attraction",
            "address": "Cầu Mống, Bến Vân Đồn, Quận 4, TP. Hồ Chí Minh",
            "location": {"type": "Point", "coordinates": [106.70488, 10.76895]},
            "radius_enter_m": 25,
            "radius_exit_m": 55,
            "cooldown_seconds": 120,
            "priority": 6,
            "status": "active",
            "revision": 1,
            "image_key": "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?w=800",
            "vi_title": "Cầu Mống Cổ Kính",
            "vi_desc": "Cây cầu đi bộ màu xanh ngọc bích hơn 130 năm tuổi bắc qua rạch Bến Nghé.",
            "vi_narration": "Cầu Mống được công ty vận tải hàng hải Pháp xây dựng từ năm 1893 với thiết kế vòm thép cong cong màu xanh ngọc. Đây là điểm ngắm hoàng hôn và chụp ảnh lãng mạn yêu thích của giới trẻ nối liền Quận 1 và Quận 4.",
            "en_title": "Historic Mong Bridge (Rainbow Bridge)",
            "en_desc": "A charming turquoise pedestrian bridge built in 1893 connecting District 1 and District 4.",
            "en_narration": "Constructed in 1893 by French engineers, Mong Bridge features an elegant turquoise steel arch spanning the Ben Nghe canal. It offers one of the best romantic sunset views connecting District 1 and District 4."
        }
    ]

    seeded_poi_ids = []
    for sp in sample_pois:
        existing = await db["pois"].find_one({"code": sp["code"]})
        if not existing:
            poi_id = str(uuid.uuid4())
            # Create POI doc
            poi_doc = {
                "_id": poi_id,
                "code": sp["code"],
                "category": sp["category"],
                "address": sp["address"],
                "location": sp["location"],
                "radius_enter_m": sp["radius_enter_m"],
                "radius_exit_m": sp["radius_exit_m"],
                "cooldown_seconds": sp["cooldown_seconds"],
                "priority": sp["priority"],
                "status": sp["status"],
                "revision": 1,
                "published_contents": {},
                "image_key": sp["image_key"],
                "created_by": admin_id,
                "created_at": now,
                "updated_at": now
            }
            await db["pois"].insert_one(poi_doc)
            seeded_poi_ids.append((poi_id, sp))

            # Create Vietnamese content
            vi_content_id = str(uuid.uuid4())
            vi_content = {
                "_id": vi_content_id,
                "poi_id": poi_id,
                "language_code": "vi",
                "version": 1,
                "title": sp["vi_title"],
                "description": sp["vi_desc"],
                "narration_text": sp["vi_narration"],
                "review_status": "approved",
                "source_content_id": None,
                "reviewed_at": now,
                "created_by": admin_id,
                "created_at": now,
                "updated_at": now
            }
            await db["poi_contents"].insert_one(vi_content)

            # Create English content
            en_content_id = str(uuid.uuid4())
            en_content = {
                "_id": en_content_id,
                "poi_id": poi_id,
                "language_code": "en",
                "version": 1,
                "title": sp["en_title"],
                "description": sp["en_desc"],
                "narration_text": sp["en_narration"],
                "review_status": "approved",
                "source_content_id": vi_content_id,
                "reviewed_at": now,
                "created_by": admin_id,
                "created_at": now,
                "updated_at": now
            }
            await db["poi_contents"].insert_one(en_content)

            # Update published_contents in POI
            await db["pois"].update_one(
                {"_id": poi_id},
                {
                    "$set": {
                        "published_contents": {
                            "vi": {
                                "content_id": vi_content_id,
                                "audio_asset_id": str(uuid.uuid4()),
                                "published_at": now,
                                "published_by": admin_id
                            },
                            "en": {
                                "content_id": en_content_id,
                                "audio_asset_id": str(uuid.uuid4()),
                                "published_at": now,
                                "published_by": admin_id
                            }
                        }
                    }
                }
            )

            # Generate QR code for this POI
            qr_doc = {
                "_id": str(uuid.uuid4()),
                "poi_id": poi_id,
                "label": f"Mã QR chính - {sp['vi_title']}",
                "is_active": True,
                "created_at": now,
                "updated_at": now
            }
            await db["qr_codes"].insert_one(qr_doc)
            logger.info(f"Seeded POI: {sp['vi_title']} ({poi_id})")

    # 4. Seed Default Tour
    existing_tour = await db["tours"].find_one({"code": "TOUR-Q4-DISCOVERY"})
    if not existing_tour and len(seeded_poi_ids) >= 3:
        tour_id = str(uuid.uuid4())
        tour_doc = {
            "_id": tour_id,
            "code": "TOUR-Q4-DISCOVERY",
            "estimated_duration_minutes": 120,
            "status": "published",
            "content_revision": 1,
            "translations": {
                "vi": {
                    "title": "Tour Khám Phá Lịch Sử & Ẩm Thực Quận 4",
                    "description": "Hành trình đi bộ từ Bến Nhà Rồng đến các ngõ ngách ẩm thực nổi tiếng Vĩnh Khánh và Chợ Xóm Chiếu."
                },
                "en": {
                    "title": "District 4 Heritage & Culinary Discovery Tour",
                    "description": "A curated walking journey from Nha Rong Harbor to legendary street food enclaves of Vinh Khanh and Xom Chieu."
                }
            },
            "stops": [
                {"poi_id": seeded_poi_ids[0][0], "stop_order": 1},
                {"poi_id": seeded_poi_ids[3][0], "stop_order": 2} if len(seeded_poi_ids) > 3 else {"poi_id": seeded_poi_ids[1][0], "stop_order": 2},
                {"poi_id": seeded_poi_ids[1][0], "stop_order": 3} if len(seeded_poi_ids) > 3 else {"poi_id": seeded_poi_ids[2][0], "stop_order": 3},
            ],
            "created_by": admin_id,
            "created_at": now,
            "updated_at": now
        }
        await db["tours"].insert_one(tour_doc)
        logger.info(f"Seeded Default Tour: {tour_doc['code']}")

    client.close()
    logger.info("Database initialization completed successfully.")


if __name__ == "__main__":
    asyncio.run(init_database())
