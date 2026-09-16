# Architecture Decisions Record (ADR) & Scope Reconciliation

Tài liệu này ghi nhận các quyết định kỹ thuật, sự khác biệt giữa các nguồn tài liệu ban đầu và các giải pháp chuẩn hóa cho dự án **Hệ thống Thuyết minh Du lịch Tự động Đa ngôn ngữ**.

---

## 1. Xử lý Khác biệt giữa các Tài liệu Nguồn

### 1.1 Khác biệt PWA vs React Native Native
- **Nguồn ban đầu (`system-presentation-standalone.html`)**: Mô tả ứng dụng dưới dạng Progressive Web App (PWA) dùng IndexedDB, Cache API, Service Worker, Web Audio API, `window.speechSynthesis`.
- **Quyết định chốt**: Ứng dụng du khách là **React Native Native (Expo)** thật, không bọc web vào WebView.
  - IndexedDB chuyển thành **SQLite** (`expo-sqlite`) lưu trữ metadata, quan hệ và hàng chờ outbox.
  - Cache API chuyển thành **Native File Storage** (`expo-file-system`) lưu trữ file audio MP3 và ảnh.
  - `window.speechSynthesis` chuyển thành adapter TTS native (`expo-speech` / remote Edge-TTS).
  - Không giả định Service Worker hay Web Cache hoạt động trên React Native.

### 1.2 Khác biệt Driver MongoDB (Motor vs PyMongo Async)
- **Hiện trạng cũ trong repo**: Một số file nguyên mẫu dùng thư viện `motor`.
- **Quyết định chốt**: Theo tài liệu MongoDB và quy định của đề tài, loại bỏ hoàn toàn Motor, sử dụng **PyMongo Async / AsyncMongoClient** (`from pymongo import AsyncMongoClient`). PyMongo 4.18+ tích hợp sẵn driver async trực tiếp, hỗ trợ đầy đủ các thao tác async/await với replica set và transactions.

### 1.3 Khác biệt Schema 13 Collections cũ vs 22 Baseline ERD
- **File cũ (`init_mongodb.js`)**: Tạo 13 collections (`pois`, `poi_contents`, `audio_assets`...).
- **Quyết định chốt**: Tuân thủ nghiêm ngặt **22 collections baseline trong Section 25 của Master Prompt** (`POI`, `poi_localizations`, `MenuItem`, `roles`, `admin_users`, `poi_owner_registrations`, `poi_submissions`, `owner_notifications`, `audit_logs`, `audio_tasks`, `ai_usage_limits`, `localization_rate_limits`, `ui_translation_bundles`, 7 collections `analytics_*`, `runtime_location_hourly`).
- Các collections thiếu từ sơ đồ gốc (`tours`, `qr_codes`, `auth_sessions`, `idempotency_keys`, `offline_pack_manifests`, `schema_migrations`) được bổ sung theo **Section 9.2 (Phần mở rộng schema được phép)** và được ghi nhận đầy đủ trong `docs/schema-additions.md`.

### 1.4 Giới hạn Nền tảng Di động (Background Limitations)
- Không coi local TTS luôn hoạt động offline (phải có giọng và ngôn ngữ đã được tải trên OS thiết bị).
- Không coi geofencing hoặc phát audio nền luôn chạy khi OS đã force-stop ứng dụng.
- Phân tách rõ ràng 3 hành vi:
  1. Lấy vị trí khi app ở background.
  2. Tiếp tục audio đang phát khi màn hình khóa.
  3. Bắt đầu audio mới từ sự kiện GPS khi app ở background.

---

## 2. Kiến trúc Hệ thống

- **Mô hình**: **Modular Monolith + Async Worker**.
- **Backend 3 lớp**:
  - `Router`: Nhận request HTTP, validate qua Pydantic v2 schemas, gọi Service, ánh xạ domain error sang HTTP status. Router tuyệt đối không gọi `db.collection`.
  - `Service`: Kiểm tra quyền, ownership, idempotency, version conflict, điều phối repository và external adapters.
  - `Repository`: Đọc/ghi, aggregate, atomic updates với MongoDB.
- **Xác thực & Phiên làm việc**:
  - Access token JWT ngắn hạn trong memory.
  - Refresh token session được băm và lưu tại collection `auth_sessions` trên server, có cơ chế token family rotation.
- **RBAC**:
  - 4 roles cố định: `super_admin` (priority 0), `admin` (priority 1), `poi_owner` (priority 10), `user` (priority 100).
  - 32 permissions nền tảng từ HTML catalog.

---

## 3. Chỉ mục Sửa đổi Nhanh (Where to change what)

| Nhu cầu nghiệp vụ | File / Thư mục cần sửa |
|---|---|
| Bán kính kích hoạt GPS, debounce, cooldown | `apps/mobile/src/services/GeofenceEngine.ts` hoặc config `backend/app/core/config.py` |
| Thứ tự fallback ngôn ngữ (target → en → vi) | `apps/mobile/src/services/AudioSourceResolver.ts` & `backend/app/services/localization_service.py` |
| Quyền của vai trò (Roles / Permissions) | `backend/app/core/permissions.py` & seed trong `backend/app/db/seed.py` |
| Provider tạo giọng nói TTS (Edge-TTS, OpenAI, Azure) | `backend/app/integrations/tts_adapter.py` |
| Provider gợi ý nội dung AI (Gemini, Claude) | `backend/app/integrations/ai_adapter.py` |
| Tên collection và cấu hình index MongoDB | `backend/app/db/collections.py` & `backend/app/db/indexes.py` |
