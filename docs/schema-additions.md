# Schema Additions & Baseline Extensions

Tài liệu này ghi nhận chi tiết các trường bổ sung vào 22 collections baseline và 6 collections mới theo đúng quy định tại **Section 9 của Master Prompt**.

---

## 1. Trường Bổ sung vào 22 Collections Baseline

### 1.1 `POI`
- `version` (int, default 1): Quản lý concurrency lạc quan (optimistic concurrency control).
- `content_version` (int, default 1): Đánh dấu phiên bản nội dung ảnh hưởng tới thuyết minh/bản dịch. Đổi tọa độ địa lý không làm tăng `content_version` để tránh việc vô hiệu hóa hoặc tạo lại audio không cần thiết.
- `source_lang` (string, default "vi"): Ngôn ngữ gốc tạo POI.
- `deleted_at` (datetime / null): Thời điểm xóa mềm. Public API luôn lọc `deleted_at: null`.

### 1.2 `poi_localizations`
- `version` (int, default 1): Phiên bản bản dịch.
- `source_version` (int, default 1): Phiên bản `content_version` của POI gốc mà bản dịch này phản ánh.
- `translation_status` (string: `draft`, `ready`, `needs_update`).
- `audio_status` (string: `none`, `queued`, `generating`, `ready`, `failed`).
- `audio_source` (string: `uploaded`, `tts_generated`, `on_demand`).
- `audio_storage_key` (string): Đường dẫn lưu trữ file trên disk hoặc object storage.
- `audio_content_hash` (string): Hash SHA-256 nội dung văn bản + ngôn ngữ + voice config (chống tạo trùng audio).
- `audio_duration_ms` (int): Thời lượng audio tính bằng mili giây.
- `active_task_id` (string / null): Task ID đang xử lý audio nếu có.
- `last_error` (string / null): Ghi nhận lỗi gần nhất nếu thất bại.

### 1.3 `admin_users`
- `auth_version` (int, default 1): Tăng lên để vô hiệu hóa toàn bộ token/phiên cũ khi đổi mật khẩu hoặc bị khóa.
- Chuẩn hóa email: Luôn chuyển email sang chữ thường (`email.strip().lower()`) trước khi lưu và tìm kiếm.

### 1.4 `MenuItem`
- `version` (int, default 1): Kiểm soát đồng thời khi cập nhật món ăn.
- `created_at` (datetime): Thời điểm tạo món.
- `updated_at` (datetime): Thời điểm sửa món.
- `deleted_at` (datetime / null): Xóa mềm món ăn.

### 1.5 `poi_owner_registrations` & `poi_submissions`
- `version` (int, default 1): Đảm bảo kiểm duyệt có điều kiện (conditional write) chống race condition giữa 2 Admin duyệt cùng lúc.
- `request_key` (string / null): Khóa idempotent cho thao tác gửi.
- `base_poi_version` (int / null trong submissions): Lưu phiên bản POI gốc khi chủ quán đề xuất sửa đổi.

### 1.6 `audio_tasks`
- `attempts` (int, default 0): Số lần đã thử thực hiện.
- `max_attempts` (int, default 3): Số lần thử tối đa trước khi đánh dấu failed.
- `available_at` (datetime): Thời điểm cho phép nhận tác vụ tiếp theo (backoff retry).
- `lease_owner` (string / null): ID của worker đang giữ quyền xử lý tác vụ.
- `lease_until` (datetime / null): Thời hạn giữ quyền lease. Hết hạn, worker khác có thể nhận lại.
- `cancel_requested` (boolean, default false): Cờ yêu cầu hủy khi task đang chạy.
- `dispatch_state` (string: `pending`, `dispatched`, `completed`).
- `items`: Mảng nhúng, mỗi item có: `poi_id`, `lang`, `input_hash`, `status`, `error`, `result_url`, `input_version`.

### 1.7 `analytics_devices` & `analytics_sessions`
- `consent_version` (int): Phiên bản chính sách đồng ý analytics.
- `consent_scopes` (array[string]): Các phạm vi được đồng ý (vd: `["events", "route_sampling"]`).
- `consent_revoked_at` (datetime / null): Thời điểm rút lại đồng ý.
- `analytics_sessions.tour_id` (string / null): ID tour nếu đang thực hiện tour.

### 1.8 `analytics_poi_daily_metrics` & `analytics_aggregation_jobs`
- `listens_count` (int, default 0): Số lượt nghe có `listened_ms > 0` làm mẫu số tính thời gian nghe trung bình.
- `generation` (int) & `processed_generation` (int): Ngăn worker cũ ghi đè đợt tổng hợp mới hơn.

---

## 2. 6 Collections Bổ sung Có Phạm vi Xác định

### 2.1 `tours`
- **Mục đích**: Hỗ trợ use case T12, T13, C15 (quản lý tour và thứ tự các điểm dừng thuyết minh).
- **Cấu trúc**:
  - `_id`: String (UUID).
  - `name`: String.
  - `description`: String.
  - `localizations`: Object `{ lang: { name: str, description: str } }`.
  - `poi_ids`: Array[String] - Danh sách ID POI theo thứ tự lộ trình.
  - `is_active`: Boolean (chỉ hiển thị tour khi `is_active: true`).
  - `version`: Int.
  - `created_by`: String (Admin User ID).
  - `created_at`: Datetime.
  - `updated_at`: Datetime.
  - `deleted_at`: Datetime / null.

### 2.2 `qr_codes`
- **Mục đích**: Hỗ trợ use case T11, C16 (quét QR code tại địa điểm để nghe thuyết minh trực tiếp không cần bật GPS).
- **Cấu trúc**:
  - `_id`: String (UUID).
  - `code`: String (Unique, mã chuỗi opaque, không chứa thông tin bí mật).
  - `poi_id`: String (Tham chiếu `POI._id`).
  - `is_active`: Boolean.
  - `version`: Int.
  - `created_by`: String (Admin User ID).
  - `created_at`: Datetime.
  - `updated_at`: Datetime.
  - `expires_at`: Datetime / null.

### 2.3 `auth_sessions`
- **Mục đích**: Quản lý phiên đăng nhập Server-side cho Admin và Owner (U01, U02, U03), bảo mật Refresh Token Rotation.
- **Cấu trúc**:
  - `_id`: String (UUID session ID).
  - `user_id`: String (Tham chiếu `admin_users._id`).
  - `refresh_token_hash`: String (Hash SHA-256 của refresh token).
  - `token_family_id`: String (UUID đại diện chuỗi phiên, phát hiện token reuse).
  - `auth_version`: Int (Khớp với `admin_users.auth_version`).
  - `created_at`: Datetime.
  - `last_used_at`: Datetime.
  - `expires_at`: Datetime (TTL Index).
  - `revoked_at`: Datetime / null.

### 2.4 `idempotency_keys`
- **Mục đích**: Đảm bảo an toàn cho các mutation trọng yếu (C01, C02, O05, SD03), chống double submit.
- **Cấu trúc**:
  - `_id`: String (UUID).
  - `scope`: String (Tên endpoint / action).
  - `actor_id`: String (User ID hoặc Client Fingerprint).
  - `key`: String (Giá trị header `Idempotency-Key`).
  - `request_hash`: String (Hash SHA-256 của request payload).
  - `response_status`: Int.
  - `response_body`: Object (Đã lọc bỏ thông tin nhạy cảm).
  - `resource_id`: String / null.
  - `created_at`: Datetime.
  - `expires_at`: Datetime (TTL Index 24h).
  - **Unique Index**: `[scope, actor_id, key]`.

### 2.5 `offline_pack_manifests`
- **Mục đích**: Hỗ trợ F01, F02, F03, F04, F05, F06 (quản lý gói dữ liệu và bản đồ offline bất biến).
- **Cấu trúc**:
  - `_id`: String (UUID).
  - `scope`: String (vd: "district_4").
  - `locale`: String (vd: "vi", "en").
  - `version`: Int.
  - `status`: String (`draft`, `published`, `archived`).
  - `poi_ids`: Array[String].
  - `tour_ids`: Array[String].
  - `assets`: Array of Objects: `[{ key, type, url, size_bytes, hash }]`.
  - `map_pack`: Object `{ type, url, size_bytes, hash, min_zoom, max_zoom }`.
  - `total_bytes`: Number.
  - `manifest_hash`: String.
  - `created_at`: Datetime.
  - `published_at`: Datetime / null.

### 2.6 `schema_migrations`
- **Mục đích**: Quản lý lịch sử chạy migrations và đảm bảo tính idempotent khi deploy database.
- **Cấu trúc**:
  - `_id`: String (Tên mã migration, vd: `001_baseline_collections`, `002_extension_indexes`).
  - `checksum`: String.
  - `applied_at`: Datetime.
  - `description`: String.
