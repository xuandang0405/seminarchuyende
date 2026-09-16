# Data Dictionary: MongoDB & SQLite

Tài liệu này định nghĩa từ điển dữ liệu chuẩn của hệ thống: 28 collections MongoDB (Backend) và 9 bảng SQLite (Mobile Client).

---

## 1. MongoDB Collections (28 Collections)

### 1.1 Nhóm Nội dung & Địa điểm
1. **`POI`**: Lưu địa điểm thuyết minh.
   - `_id`: String (UUID)
   - `owner_id`: String / null (Admin_users ID nếu là quán của chủ quán)
   - `name`: String
   - `description`: String
   - `category`: String (`historical`, `food`, `culture`, `sightseeing`)
   - `address`: String
   - `location`: GeoJSON Point `{ type: "Point", coordinates: [lng, lat] }` (Chỉ mục `2dsphere`)
   - `images`: Array[String] (URL hoặc storage keys)
   - `trigger_radius`: Number (Bán kính tính bằng mét, default: 30.0)
   - `audio_priority`: Number (Độ ưu tiên phát khi có nhiều POI, default: 1)
   - `audio_status`: String (`none`, `ready`, `generating`)
   - `is_active`: Boolean (Trạng thái công khai thực tế sau khi qua readiness gate)
   - `activation_requested`: Boolean (Mong muốn công bố của quản trị viên)
   - `version`: Number (Optimistic lock)
   - `content_version`: Number (Phiên bản nội dung ảnh hưởng bản dịch/audio)
   - `source_lang`: String (Ngôn ngữ gốc)
   - `created_at`: Datetime
   - `updated_at`: Datetime
   - `deleted_at`: Datetime / null (Xóa mềm)

2. **`poi_localizations`**: Lưu bản dịch và thông tin audio đa ngôn ngữ của POI.
   - `_id`: String (UUID)
   - `poi_id`: String (Tham chiếu `POI._id`)
   - `lang`: String (Mã ngôn ngữ: `vi`, `en`, `fr`, `zh`, `ja`)
   - `name`: String
   - `description`: String
   - `audio_url`: String / null
   - `audio_storage_key`: String / null
   - `audio_content_hash`: String / null
   - `audio_duration_ms`: Number (default: 0)
   - `translation_status`: String (`draft`, `ready`, `needs_update`)
   - `audio_status`: String (`none`, `queued`, `generating`, `ready`, `failed`)
   - `audio_source`: String (`uploaded`, `tts_generated`, `on_demand`)
   - `version`: Number
   - `source_version`: Number
   - `active_task_id`: String / null
   - `last_error`: String / null
   - `updated_at`: Datetime

3. **`MenuItem`**: Món ăn hoặc đặc sản của địa điểm.
   - `_id`: String (UUID)
   - `poi_id`: String (Tham chiếu `POI._id`)
   - `name`: String
   - `description`: String
   - `price`: Number (Số nguyên không âm, ví dụ VNĐ)
   - `currency`: String (default: "VND")
   - `image_url`: String / null
   - `is_active`: Boolean
   - `version`: Number
   - `created_at`: Datetime
   - `updated_at`: Datetime
   - `deleted_at`: Datetime / null

4. **`content_dataset_versions`**: Quản lý phiên bản snapshot phục vụ đồng bộ.
   - `_id`: String (Mã scope, vd: "district_4")
   - `dataset_version`: String (Hash hoặc timestamp ISO)
   - `updated_at`: Datetime

5. **`tours`**: Tuyến tham quan gồm nhiều địa điểm có thứ tự.
   - `_id`: String (UUID)
   - `name`: String
   - `description`: String
   - `localizations`: Object
   - `poi_ids`: Array[String] (Có thứ tự)
   - `is_active`: Boolean
   - `version`: Number
   - `created_by`: String
   - `created_at`: Datetime
   - `updated_at`: Datetime
   - `deleted_at`: Datetime / null

6. **`qr_codes`**: Mã QR gắn với POI.
   - `_id`: String (UUID)
   - `code`: String (Unique)
   - `poi_id`: String
   - `is_active`: Boolean
   - `version`: Number
   - `created_by`: String
   - `created_at`: Datetime
   - `updated_at`: Datetime
   - `expires_at`: Datetime / null

---

### 1.2 Nhóm Tài khoản, Quyền & Chủ quán
7. **`roles`**: Vai trò người dùng.
   - `_id`: String (UUID)
   - `name`: String (Unique: `super_admin`, `admin`, `poi_owner`, `user`)
   - `permissions`: Array[String]
   - `priority`: Number (0: super_admin, 1: admin, 10: poi_owner, 100: user)

8. **`admin_users`**: Tài khoản quản trị và chủ quán.
   - `_id`: String (UUID)
   - `email`: String (Unique, lowercase)
   - `full_name`: String
   - `password_hash`: String
   - `role`: String (Tham chiếu `roles.name`)
   - `is_active`: Boolean
   - `is_verified`: Boolean
   - `is_poi_owner_verified`: Boolean
   - `auth_version`: Number (default: 1)
   - `pii_encrypted`: String / null
   - `created_at`: Datetime
   - `updated_at`: Datetime

9. **`auth_sessions`**: Phiên làm việc của tài khoản.
   - `_id`: String (UUID)
   - `user_id`: String
   - `refresh_token_hash`: String
   - `token_family_id`: String
   - `auth_version`: Number
   - `created_at`: Datetime
   - `last_used_at`: Datetime
   - `expires_at`: Datetime (TTL index)
   - `revoked_at`: Datetime / null

10. **`poi_owner_registrations`**: Đơn đăng ký làm chủ quán.
    - `_id`: String (UUID)
    - `user_id`: String
    - `business_name`: String
    - `status`: String (`pending`, `approved`, `rejected`)
    - `admin_note`: String / null
    - `reviewed_by`: String / null
    - `submitted_at`: Datetime
    - `reviewed_at`: Datetime / null
    - `version`: Number

11. **`poi_submissions`**: Đề xuất tạo hoặc sửa POI của chủ quán.
    - `_id`: String (UUID)
    - `owner_id`: String
    - `poi_id`: String / null (Null nếu tạo mới, có ID nếu sửa)
    - `action`: String (`create`, `update`)
    - `payload`: Object (Chứa thông tin POI/Menu đề xuất)
    - `status`: String (`pending`, `approved`, `rejected`)
    - `admin_note`: String / null
    - `reviewed_by`: String / null
    - `created_at`: Datetime
    - `reviewed_at`: Datetime / null
    - `version`: Number
    - `request_key`: String / null

12. **`owner_notifications`**: Thông báo trong ứng dụng cho chủ quán.
    - `_id`: String (UUID)
    - `owner_id`: String
    - `submission_id`: String / null
    - `registration_id`: String / null
    - `type`: String (`registration_result`, `submission_result`, `system`)
    - `message`: String
    - `is_read`: Boolean (default: false)
    - `created_at`: Datetime

13. **`audit_logs`**: Nhật ký hoạt động quản trị.
    - `_id`: String (UUID)
    - `user_id`: String
    - `action`: String
    - `resource_type`: String
    - `resource_id`: String
    - `metadata`: Object
    - `timestamp`: Datetime

---

### 1.3 Nhóm Tác vụ Nền, Audio, Dịch thuật & AI
14. **`audio_tasks`**: Tác vụ tạo bản dịch và TTS.
    - `_id`: String (UUID)
    - `requested_by`: String
    - `items`: Array[Object] (`[{ poi_id, lang, input_hash, status, error, input_version }]`)
    - `status`: String (`queued`, `running`, `succeeded`, `failed`, `cancelled`)
    - `progress`: Object `{ total: int, completed: int, failed: int }`
    - `attempts`: Number
    - `max_attempts`: Number
    - `lease_owner`: String / null
    - `lease_until`: Datetime / null
    - `cancel_requested`: Boolean
    - `error_message`: String / null
    - `heartbeat_at`: Datetime / null
    - `created_at`: Datetime
    - `updated_at`: Datetime
    - `expires_at`: Datetime (TTL Index sau khi hoàn tất)

15. **`ai_usage_limits`**: Giới hạn số lượt gọi AI theo ngày.
    - `_id`: String (UUID)
    - `user_id`: String
    - `date`: String ("YYYY-MM-DD")
    - `count`: Number (Tăng nguyên tử)

16. **`localization_rate_limits`**: Giới hạn tốc độ gọi API dịch/TTS.
    - `_id`: String (UUID)
    - `key`: String
    - `window_start`: Datetime
    - `count`: Number
    - `expires_at`: Datetime (TTL Index)

17. **`ui_translation_bundles`**: Gói chuỗi giao diện đa ngôn ngữ.
    - `_id`: String (UUID)
    - `namespace`: String
    - `locale`: String
    - `source_hash`: String
    - `status`: String
    - `messages`: Object
    - `updated_at`: Datetime

18. **`idempotency_keys`**: Lưu kết quả request mutation chống trùng lặp.
    - `_id`: String (UUID)
    - `scope`: String
    - `actor_id`: String
    - `key`: String
    - `request_hash`: String
    - `response_status`: Number
    - `response_body`: Object
    - `resource_id`: String / null
    - `created_at`: Datetime
    - `expires_at`: Datetime (TTL Index 24h)

19. **`offline_pack_manifests`**: Manifest đóng gói dữ liệu offline.
    - `_id`: String (UUID)
    - `scope`: String
    - `locale`: String
    - `version`: Number
    - `status`: String (`draft`, `published`, `archived`)
    - `poi_ids`: Array[String]
    - `tour_ids`: Array[String]
    - `assets`: Array[Object]
    - `map_pack`: Object
    - `total_bytes`: Number
    - `manifest_hash`: String
    - `created_at`: Datetime
    - `published_at`: Datetime / null

20. **`schema_migrations`**: Nhật ký migrations MongoDB.
    - `_id`: String
    - `checksum`: String
    - `applied_at`: Datetime
    - `description`: String

---

### 1.4 Nhóm Analytics & Quan sát Hệ thống
21. **`analytics_devices`**: Thiết bị du khách (mã giả danh).
    - `_id`: String (UUID pseudonymous)
    - `consent_at`: Datetime
    - `consent_version`: Number
    - `consent_scopes`: Array[String]
    - `consent_revoked_at`: Datetime / null
    - `created_at`: Datetime
    - `last_seen_at`: Datetime

22. **`analytics_sessions`**: Phiên tham quan của thiết bị.
    - `_id`: String (UUID)
    - `device_id`: String
    - `language`: String
    - `started_at`: Datetime
    - `ended_at`: Datetime / null
    - `tour_id`: String / null

23. **`analytics_events`**: Các sự kiện du khách gửi lên.
    - `_id`: String (Event ID ổn định khi retry)
    - `session_id`: String
    - `poi_id`: String / null
    - `event_type`: String (`poi_view`, `audio_start`, `audio_progress`, `audio_end`, `tour_start`, `tour_end`, `search`)
    - `occurred_at`: Datetime
    - `received_at`: Datetime
    - `properties`: Object

24. **`analytics_poi_daily_metrics`**: Thống kê nghe từng POI theo ngày.
    - `_id`: String (Compound key: `${poi_id}_${metric_date}_${env}`)
    - `poi_id`: String
    - `metric_date`: String ("YYYY-MM-DD")
    - `env`: String
    - `audio_plays`: Number
    - `listened_ms`: Number
    - `listens_count`: Number
    - `updated_at`: Datetime

25. **`analytics_daily_metrics`**: Thống kê tổng hợp toàn hệ thống theo ngày.
    - `_id`: String (`${metric_date}_${env}`)
    - `metric_date`: String ("YYYY-MM-DD")
    - `env`: String
    - `metrics`: Object
    - `updated_at`: Datetime

26. **`analytics_hourly_metrics`**: Thống kê tổng hợp theo giờ.
    - `_id`: String (`${metric_date}_${metric_hour}_${env}`)
    - `metric_date`: String
    - `metric_hour`: Number (0-23)
    - `env`: String
    - `metrics`: Object
    - `updated_at`: Datetime

27. **`analytics_aggregation_jobs`**: Theo dõi tiến trình tổng hợp số liệu.
    - `_id`: String (`${metric_date}_${env}`)
    - `metric_date`: String
    - `env`: String
    - `status`: String (`pending`, `running`, `completed`, `failed`)
    - `attempts`: Number
    - `lease_owner`: String / null
    - `lease_until`: Datetime / null
    - `generation`: Number
    - `processed_generation`: Number
    - `updated_at`: Datetime

28. **`runtime_location_hourly`**: Mật độ vị trí runtime theo cell bản đồ và giờ.
    - `_id`: String (`${time_hour}_${cell_id}`)
    - `time_hour`: Datetime
    - `cell_id`: String (Mã ô địa lý / geohash)
    - `location`: Object `{ lat: float, lng: float }`
    - `sample_count`: Number
    - `expires_at`: Datetime (TTL Index)

---

## 2. SQLite Tables trên Mobile Client (9 Bảng Local)

| Tên Bảng Local | Mục đích lưu trữ | Các trường chính |
|---|---|---|
| `app_settings` | Cấu hình ứng dụng, ngôn ngữ, consent | `key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER` |
| `offline_packs` | Danh sách gói offline đã tải | `id TEXT PRIMARY KEY, locale TEXT, version INTEGER, status TEXT, progress REAL, total_bytes INTEGER, manifest_hash TEXT, activated_at INTEGER` |
| `poi_snapshots` | Dữ liệu POI phục vụ offline | `id TEXT PRIMARY KEY, name TEXT, description TEXT, category TEXT, address TEXT, latitude REAL, longitude REAL, trigger_radius REAL, audio_priority INTEGER, images_json TEXT, version INTEGER, is_active INTEGER` |
| `localization_snapshots`| Bản dịch và audio metadata offline | `poi_id TEXT, lang TEXT, name TEXT, description TEXT, audio_local_path TEXT, audio_duration_ms INTEGER, version INTEGER, PRIMARY KEY(poi_id, lang)` |
| `media_assets` | Quản lý file MP3/ảnh đã lưu vào đĩa | `asset_key TEXT PRIMARY KEY, pack_id TEXT, file_path TEXT, byte_size INTEGER, checksum TEXT, downloaded_at INTEGER` |
| `qr_snapshots` | Bảng ánh xạ mã QR cục bộ | `code TEXT PRIMARY KEY, poi_id TEXT, version INTEGER, expires_at INTEGER` |
| `tour_snapshots` | Danh sách tour offline | `id TEXT PRIMARY KEY, name TEXT, description TEXT, poi_ids_json TEXT, version INTEGER, is_active INTEGER` |
| `playback_history` | Lịch sử nghe và cooldown GPS | `poi_id TEXT PRIMARY KEY, last_played_at INTEGER, play_count INTEGER, completed_duration_ms INTEGER` |
| `analytics_outbox` | Hàng chờ gửi sự kiện analytics | `id TEXT PRIMARY KEY, payload_json TEXT, created_at INTEGER, attempts INTEGER, next_retry_at INTEGER` |
