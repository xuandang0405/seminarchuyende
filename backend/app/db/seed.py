"""Idempotent seed data for TourVoice District 4.

Includes:
- 4 Standard Roles (super_admin, admin, poi_owner, user)
- Seed users with hashed passwords
- 10 Realistic District 4 POIs with GeoJSON coordinates
- Multi-language localizations (vi, en, fr)
- Sample menu items
- 2 Tours with ordered POIs
- Sample QR codes
"""

import logging
import uuid
from datetime import datetime, timezone
from pymongo.asynchronous.database import AsyncDatabase

from app.core.security import get_password_hash
from app.core.permissions import ROLES_DEFINITION
from app.db.collections import (
    COLLECTION_ROLES,
    COLLECTION_ADMIN_USERS,
    COLLECTION_POI_OWNER_REGISTRATIONS,
    COLLECTION_POI,
    COLLECTION_POI_LOCALIZATIONS,
    COLLECTION_MENU_ITEM,
    COLLECTION_TOURS,
    COLLECTION_QR_CODES,
    COLLECTION_CONTENT_DATASET_VERSIONS,
)

logger = logging.getLogger("uvicorn")


async def seed_database(db: AsyncDatabase):
    logger.info("Seeding database with initial idempotent data...")
    now = datetime.now(timezone.utc)

    # =========================================================================
    # 1. SEED ROLES
    # =========================================================================
    for role_key, role_data in ROLES_DEFINITION.items():
        existing_role = await db[COLLECTION_ROLES].find_one({"name": role_data["name"]})
        if not existing_role:
            await db[COLLECTION_ROLES].insert_one({
                "_id": f"role_{role_data['name']}",
                "name": role_data["name"],
                "priority": role_data["priority"],
                "permissions": role_data["permissions"],
            })
            logger.info(f"Seeded role: {role_data['name']}")
        else:
            # Update permissions if changed
            await db[COLLECTION_ROLES].update_one(
                {"name": role_data["name"]},
                {"$set": {
                    "permissions": role_data["permissions"],
                    "priority": role_data["priority"]
                }}
            )

    # =========================================================================
    # 2. SEED USERS
    # =========================================================================
    default_pwd_hash = get_password_hash("Admin@123456")
    owner_pwd_hash = get_password_hash("Owner@123456")
    user_pwd_hash = get_password_hash("User@123456")

    seed_users = [
        {
            "_id": "user_super_admin_01",
            "email": "superadmin@tourvoice.vn",
            "full_name": "Nguyễn Văn Super",
            "password_hash": default_pwd_hash,
            "role": "super_admin",
            "is_active": True,
            "is_verified": True,
            "is_poi_owner_verified": False,
            "auth_version": 1,
            "pii_encrypted": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": "user_admin_01",
            "email": "admin@tourvoice.vn",
            "full_name": "Trần Thị Admin",
            "password_hash": default_pwd_hash,
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "is_poi_owner_verified": False,
            "auth_version": 1,
            "pii_encrypted": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": "user_owner_verified_01",
            "email": "owner.verified@quan4.vn",
            "full_name": "Lê Văn Chủ Quán (Verified)",
            "password_hash": owner_pwd_hash,
            "role": "poi_owner",
            "is_active": True,
            "is_verified": True,
            "is_poi_owner_verified": True,
            "auth_version": 1,
            "pii_encrypted": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": "user_owner_pending_01",
            "email": "owner.pending@quan4.vn",
            "full_name": "Phạm Văn Chờ Duyệt (Pending)",
            "password_hash": owner_pwd_hash,
            "role": "poi_owner",
            "is_active": True,
            "is_verified": True,
            "is_poi_owner_verified": False,
            "auth_version": 1,
            "pii_encrypted": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": "user_tourist_01",
            "email": "tourist@test.vn",
            "full_name": "John Doe Tourist",
            "password_hash": user_pwd_hash,
            "role": "user",
            "is_active": True,
            "is_verified": True,
            "is_poi_owner_verified": False,
            "auth_version": 1,
            "pii_encrypted": None,
            "created_at": now,
            "updated_at": now,
        }
    ]

    for u in seed_users:
        existing = await db[COLLECTION_ADMIN_USERS].find_one({"email": u["email"]})
        if not existing:
            await db[COLLECTION_ADMIN_USERS].insert_one(u)
            logger.info(f"Seeded user: {u['email']}")

    # Pending registration for user_owner_pending_01
    pending_reg = await db[COLLECTION_POI_OWNER_REGISTRATIONS].find_one({"user_id": "user_owner_pending_01"})
    if not pending_reg:
        await db[COLLECTION_POI_OWNER_REGISTRATIONS].insert_one({
            "_id": "reg_owner_pending_01",
            "user_id": "user_owner_pending_01",
            "business_name": "Quán Ốc Vũ Vĩnh Khánh",
            "status": "pending",
            "admin_note": None,
            "reviewed_by": None,
            "submitted_at": now,
            "reviewed_at": None,
            "version": 1,
        })

    # =========================================================================
    # 3. SEED 10 POIs IN DISTRICT 4 (QUẬN 4, TP. HỒ CHÍ MINH)
    # Coordinates in GeoJSON: [longitude, latitude]
    # =========================================================================
    pois_data = [
        {
            "_id": "poi_ben_nha_rong",
            "name": "Bến Nhà Rồng - Bảo tàng Hồ Chí Minh",
            "description": "Di tích lịch sử văn hóa nổi tiếng nơi Bác Hồ ra đi tìm đường cứu nước năm 1911.",
            "category": "historical",
            "address": "Số 01 Nguyễn Tất Thành, Phường 12, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.70678, 10.76815]},
            "trigger_radius": 50.0,
            "audio_priority": 10,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/ben_nha_rong.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Bến Nhà Rồng - Bảo tàng Hồ Chí Minh",
                    "description": "Di tích lịch sử tiêu biểu của Quận 4 và TP.HCM, kiến trúc kết hợp Á - Âu bên bờ sông Sài Gòn.",
                },
                "en": {
                    "name": "Dragon Wharf - Ho Chi Minh Museum",
                    "description": "Historic landmark where President Ho Chi Minh departed in 1911 to seek a path for national liberation.",
                },
                "fr": {
                    "name": "Quai du Dragon - Musée Ho Chi Minh",
                    "description": "Site historique emblématique du 4e arrondissement au bord de la rivière Saigon.",
                }
            }
        },
        {
            "_id": "poi_pho_oc_vinh_khanh",
            "name": "Phố Ẩm Thực Vĩnh Khánh",
            "description": "Thiên đường ẩm thực đường phố và hải sản ốc đêm náo nhiệt bậc nhất Sài Gòn.",
            "category": "food",
            "address": "Đường Vĩnh Khánh, Phường 8, 9, 10, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.70012, 10.76045]},
            "trigger_radius": 40.0,
            "audio_priority": 8,
            "is_active": True,
            "activation_requested": True,
            "owner_id": "user_owner_verified_01",
            "images": ["/storage/images/pho_oc_vinh_khanh.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Phố Ẩm Thực Vĩnh Khánh",
                    "description": "Khu phố ẩm thực đêm sôi động với hàng chục quán ốc, hải sản tươi sống và món ngon truyền thống.",
                },
                "en": {
                    "name": "Vinh Khanh Seafood & Street Food Street",
                    "description": "Bustling night street famous for fresh seafood, snails, and authentic Saigon nightlife.",
                },
                "fr": {
                    "name": "Rue Gastronomique Vinh Khanh",
                    "description": "Rue animée réputée pour ses fruits de mer et sa cuisine de rue nocturne.",
                }
            }
        },
        {
            "_id": "poi_cau_mong",
            "name": "Cầu Mống",
            "description": "Cây cầu bộ hành cổ kính nối Quận 1 và Quận 4, xây dựng thời Pháp thuộc từ cuối thế kỷ 19.",
            "category": "sightseeing",
            "address": "Bến Vân Đồn, Phường 12, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.70420, 10.76890]},
            "trigger_radius": 35.0,
            "audio_priority": 7,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/cau_mong.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Cầu Mống",
                    "description": "Một trong những cây cầu cổ nhất Sài Gòn với kiến trúc vòm thép màu xanh ngọc đặc trưng bắc qua kênh Bến Nghé.",
                },
                "en": {
                    "name": "Mong Bridge (Rainbow Bridge)",
                    "description": "One of the oldest historical bridges in Saigon with iconic green steel arch architecture.",
                }
            }
        },
        {
            "_id": "poi_nha_tho_xom_chieu",
            "name": "Nhà Thờ Xóm Chiếu",
            "description": "Nhà thờ Công giáo lâu đời mang đậm dấu ấn kiến trúc cổ kính giữa lòng Quận 4.",
            "category": "culture",
            "address": "92 Lê Quốc Hưng, Phường 12, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.70250, 10.76380]},
            "trigger_radius": 30.0,
            "audio_priority": 6,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/nha_tho_xom_chieu.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Nhà Thờ Xóm Chiếu",
                    "description": "Giáo xứ truyền thống gắn liền với lịch sử hình thành vùng đất Xóm Chiếu Quận 4.",
                },
                "en": {
                    "name": "Xom Chieu Church",
                    "description": "Historic Catholic church rooted in the rich cultural heritage of District 4.",
                }
            }
        },
        {
            "_id": "poi_cho_xom_chieu",
            "name": "Chợ Xóm Chiếu",
            "description": "Khu chợ truyền thống sầm uất với khu ăn vặt nổi tiếng bậc nhất Sài Gòn.",
            "category": "food",
            "address": "Đường Lê Quốc Hưng, Phường 12, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.70310, 10.76290]},
            "trigger_radius": 35.0,
            "audio_priority": 7,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/cho_xom_chieu.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Chợ Xóm Chiếu (Chợ 200)",
                    "description": "Thiên đường ẩm thực bình dân với các món phá lấu, súp cua, ốc và chè truyền thống.",
                },
                "en": {
                    "name": "Xom Chieu Traditional Market",
                    "description": "Vibrant local market renowned for diverse and authentic Vietnamese street food stalls.",
                }
            }
        },
        {
            "_id": "poi_chua_giac_nguyen",
            "name": "Chùa Giác Nguyên",
            "description": "Ngôi chùa cổ thanh tịnh với bề dày hơn 70 năm lịch sử văn hóa tâm linh.",
            "category": "culture",
            "address": "129F/88 Lạc Long Quân, Phường 3, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.69780, 10.75540]},
            "trigger_radius": 30.0,
            "audio_priority": 5,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/chua_giac_nguyen.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Chùa Giác Nguyên",
                    "description": "Điểm sinh hoạt Phật giáo trang nghiêm, lưu giữ nét đẹp văn hóa tâm linh của người dân địa phương.",
                },
                "en": {
                    "name": "Giac Nguyen Pagoda",
                    "description": "Serene Buddhist pagoda offering spiritual tranquility and cultural heritage.",
                }
            }
        },
        {
            "_id": "poi_dinh_vinh_hoi",
            "name": "Đình Vĩnh Hội",
            "description": "Di tích kiến trúc nghệ thuật đình làng Nam Bộ cổ kính trên bán đảo Quận 4.",
            "category": "historical",
            "address": "Bến Vân Đồn, Phường 6, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.69420, 10.76010]},
            "trigger_radius": 30.0,
            "audio_priority": 5,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/dinh_vinh_hoi.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Đình Vĩnh Hội",
                    "description": "Di tích thờ Thành Hoàng làng, ghi dấu phong tục tập quán lâu đời của cư dân Nam Bộ.",
                },
                "en": {
                    "name": "Vinh Hoi Communal House",
                    "description": "Traditional Southern Vietnamese communal house dedicated to village guardian spirits.",
                }
            }
        },
        {
            "_id": "poi_cong_vien_khanh_hoi",
            "name": "Công Viên Khánh Hội",
            "description": "Lá phổi xanh lớn nhất Quận 4 với không gian rợp bóng cây, hồ nước và khu vui chơi.",
            "category": "sightseeing",
            "address": "Đường Hoàng Diệu, Phường 5, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.69950, 10.75820]},
            "trigger_radius": 45.0,
            "audio_priority": 6,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/cong_vien_khanh_hoi.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Công Viên Khánh Hội",
                    "description": "Không gian sinh hoạt cộng đồng thoáng đãng, điểm thư giãn và dạo mát lý tưởng.",
                },
                "en": {
                    "name": "Khanh Hoi Public Park",
                    "description": "The largest green park in District 4, perfect for walking, relaxing, and outdoor activities.",
                }
            }
        },
        {
            "_id": "poi_pha_lau_di_nui",
            "name": "Phá Lấu Bò Dì Nủi",
            "description": "Quán phá lấu bò gia truyền nức tiếng Sài Gòn hơn 20 năm.",
            "category": "food",
            "address": "243/30 Tôn Đản, Phường 15, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.70510, 10.75920]},
            "trigger_radius": 25.0,
            "audio_priority": 7,
            "is_active": True,
            "activation_requested": True,
            "owner_id": "user_owner_verified_01",
            "images": ["/storage/images/pha_lau_di_nui.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Phá Lấu Bò Dì Nủi Tôn Đản",
                    "description": "Nồi phá lấu nước cốt dừa béo ngậy ăn kèm bánh mì giòn tan và nước chấm tắc ớt chua ngọt.",
                },
                "en": {
                    "name": "Aunt Nui Beef Offal Stew (Pha Lau)",
                    "description": "Iconic Saigon street food featuring tender spiced beef stew in rich coconut broth.",
                }
            }
        },
        {
            "_id": "poi_cang_sai_gon",
            "name": "Cảng Sài Gòn - Khu Di Sản Hàng Hải",
            "description": "Cảng biển thương mại sầm uất gắn liền với lịch sử giao thương quốc tế của hòn ngọc Viễn Đông.",
            "category": "historical",
            "address": "Nguyễn Tất Thành, Phường 18, Quận 4, TP.HCM",
            "location": {"type": "Point", "coordinates": [106.71100, 10.76100]},
            "trigger_radius": 60.0,
            "audio_priority": 6,
            "is_active": True,
            "activation_requested": True,
            "owner_id": None,
            "images": ["/storage/images/cang_sai_gon.jpg"],
            "version": 1,
            "content_version": 1,
            "source_lang": "vi",
            "localizations": {
                "vi": {
                    "name": "Cảng Sài Gòn - Khu Di Sản Hàng Hải",
                    "description": "Khu cảng lịch sử bên dòng sông Sài Gòn, chứng nhân cho sự chuyển mình kinh tế của thành phố.",
                },
                "en": {
                    "name": "Saigon Port - Maritime Heritage Zone",
                    "description": "Historic commercial port that played a pivotal role in the international trade of Saigon.",
                }
            }
        },
    ]

    for p in pois_data:
        locs = p.pop("localizations")
        p["created_at"] = now
        p["updated_at"] = now
        p["deleted_at"] = None

        # Upsert POI
        await db[COLLECTION_POI].update_one(
            {"_id": p["_id"]},
            {"$set": p},
            upsert=True
        )

        # Upsert Localizations
        for lang_code, loc_val in locs.items():
            loc_doc = {
                "_id": f"{p['_id']}_{lang_code}",
                "poi_id": p["_id"],
                "lang": lang_code,
                "name": loc_val["name"],
                "description": loc_val["description"],
                "audio_url": f"/storage/audio/{p['_id']}_{lang_code}.mp3",
                "audio_storage_key": f"audio/{p['_id']}_{lang_code}.mp3",
                "audio_content_hash": "sample_hash_ok",
                "audio_duration_ms": 45000,
                "translation_status": "ready",
                "audio_status": "ready",
                "audio_source": "tts_generated",
                "version": 1,
                "source_version": 1,
                "active_task_id": None,
                "last_error": None,
                "updated_at": now,
            }
            await db[COLLECTION_POI_LOCALIZATIONS].update_one(
                {"poi_id": p["_id"], "lang": lang_code},
                {"$set": loc_doc},
                upsert=True
            )

    # =========================================================================
    # 4. SEED MENU ITEMS
    # =========================================================================
    menu_items = [
        {
            "_id": "menu_oc_01",
            "poi_id": "poi_pho_oc_vinh_khanh",
            "name": "Ốc Hương Xào Trứng Muối",
            "description": "Ốc hương biển tươi sống sốt trứng muối béo thơm ăn kèm bánh mì.",
            "price": 120000,
            "currency": "VND",
            "image_url": "/storage/images/oc_huong.jpg",
            "is_active": True,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "_id": "menu_oc_02",
            "poi_id": "poi_pho_oc_vinh_khanh",
            "name": "Càng Ghẹ Rang Muối Kéo Chỉ",
            "description": "Càng ghẹ chắc thịt cay nồng muối ớt kéo chỉ đặc sản Vĩnh Khánh.",
            "price": 150000,
            "currency": "VND",
            "image_url": "/storage/images/cang_ghe.jpg",
            "is_active": True,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "_id": "menu_phalau_01",
            "poi_id": "poi_pha_lau_di_nui",
            "name": "Phá Lấu Chén Thập Cẩm",
            "description": "Phá lấu lòng bò mềm béo nước dừa kèm bánh mì nóng giòn.",
            "price": 35000,
            "currency": "VND",
            "image_url": "/storage/images/pha_lau_chen.jpg",
            "is_active": True,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    ]
    for m in menu_items:
        await db[COLLECTION_MENU_ITEM].update_one(
            {"_id": m["_id"]},
            {"$set": m},
            upsert=True
        )

    # =========================================================================
    # 5. SEED 2 TOURS
    # =========================================================================
    tours_data = [
        {
            "_id": "tour_quan_4_lich_su",
            "code": "TOUR-Q4-HERITAGE",
            "name": "Hành Trình Di Sản Bến Cảng Quận 4",
            "description": "Khám phá các di tích lịch sử và văn hóa tiêu biểu gắn liền với sự hình thành của TP.HCM.",
            "localizations": {
                "en": {
                    "name": "Heritage & Historic Harbor of District 4",
                    "description": "Explore historical landmarks and cultural relics along the Saigon River."
                }
            },
            "poi_ids": ["poi_ben_nha_rong", "poi_cau_mong", "poi_dinh_vinh_hoi", "poi_cang_sai_gon"],
            "is_active": True,
            "version": 1,
            "created_by": "user_admin_01",
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "_id": "tour_quan_4_am_thuc",
            "code": "TOUR-Q4-FOOD",
            "name": "Food Tour - Đêm Ẩm Thực Đường Phố Quận 4",
            "description": "Trải nghiệm hương vị hải sản Vĩnh Khánh và ẩm thực đường phố trứ danh.",
            "localizations": {
                "en": {
                    "name": "District 4 Night Street Food Trail",
                    "description": "Taste the legendary seafood and traditional street snacks of Saigon night."
                }
            },
            "poi_ids": ["poi_pho_oc_vinh_khanh", "poi_cho_xom_chieu", "poi_pha_lau_di_nui"],
            "is_active": True,
            "version": 1,
            "created_by": "user_admin_01",
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    ]
    for t in tours_data:
        await db[COLLECTION_TOURS].update_one(
            {"_id": t["_id"]},
            {"$set": t},
            upsert=True
        )

    # =========================================================================
    # 6. SEED QR CODES
    # =========================================================================
    qr_data = [
        {
            "_id": "qr_ben_nha_rong_01",
            "code": "Q4-BNR-01",
            "poi_id": "poi_ben_nha_rong",
            "is_active": True,
            "version": 1,
            "created_by": "user_admin_01",
            "created_at": now,
            "updated_at": now,
            "expires_at": None,
        },
        {
            "_id": "qr_vinh_khanh_01",
            "code": "Q4-VKH-01",
            "poi_id": "poi_pho_oc_vinh_khanh",
            "is_active": True,
            "version": 1,
            "created_by": "user_admin_01",
            "created_at": now,
            "updated_at": now,
            "expires_at": None,
        },
        {
            "_id": "qr_cau_mong_01",
            "code": "Q4-CMG-01",
            "poi_id": "poi_cau_mong",
            "is_active": True,
            "version": 1,
            "created_by": "user_admin_01",
            "created_at": now,
            "updated_at": now,
            "expires_at": None,
        }
    ]
    for q in qr_data:
        await db[COLLECTION_QR_CODES].update_one(
            {"_id": q["_id"]},
            {"$set": q},
            upsert=True
        )

    # =========================================================================
    # 7. CONTENT DATASET VERSION
    # =========================================================================
    await db[COLLECTION_CONTENT_DATASET_VERSIONS].update_one(
        {"_id": "district_4"},
        {"$set": {
            "dataset_version": "v1.0.0-" + now.strftime("%Y%m%d%H%M"),
            "updated_at": now
        }},
        upsert=True
    )

    logger.info("Database seeding completed successfully!")
