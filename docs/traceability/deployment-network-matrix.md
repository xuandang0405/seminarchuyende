# Ma Trận Truy Xuất Mạng & Triển Khai (Deployment & Network Traceability Matrix)

Tài liệu này ánh xạ chi tiết luồng xử lý từ Thao tác Người dùng -> URL Phân giải -> Định tuyến Reverse Proxy Nginx -> Endpoint FastAPI -> Chính sách CORS/Bảo mật -> Cấu hình Môi trường -> Lệnh Kiểm thử -> Mã nguồn Sơ đồ.

---

## 1. Bảng Ánh Xạ Luồng Mạng & Triển Khai (Network & Deployment Matrix)

| Thao Tác Client | Resolved Client URL | Nginx Route (`proxy_pass`) | Backend FastAPI Endpoint | Chính Sách CORS & Auth | Biến Môi Trường Liên Quan | Lệnh Smoke Test Tự Động | Sơ Đồ Thiết Kế (.puml) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Đăng nhập Web Admin / CMS** | `/api/v1/auth/login` *(Same-Origin)* | `location /api/` -> `http://127.0.0.1:8000;` | `POST /api/v1/auth/login` | **Same-Origin**: Không phát sinh CORS. Hỗ trợ HttpOnly cookie + Bearer token. | `PUBLIC_WEB_URL`<br>`JWT_SECRET` | `curl -i -X POST .../api/v1/auth/login` | [SD-DEPLOY-01](file:///d:/seminar/seminarchuyende/docs/diagrams/sequences/SD-DEPLOY-01-web-login.puml)<br>[AD-DEPLOY-03](file:///d:/seminar/seminarchuyende/docs/diagrams/activities/AD-DEPLOY-03-request-flow.puml) |
| **CORS Preflight (Khác Origin)** | `https://api.quan4.vn/api/v1/auth/login` | `location /api/` -> `http://127.0.0.1:8000;` | `OPTIONS /api/v1/auth/login` | `CORSMiddleware` kiểm tra `CORS_ALLOWED_ORIGINS`. Trả về allow headers, không gọi database. | `CORS_ALLOWED_ORIGINS` | `curl -i -X OPTIONS .../api/v1/auth/login` | [SD-DEPLOY-02](file:///d:/seminar/seminarchuyende/docs/diagrams/sequences/SD-DEPLOY-02-cors-preflight.puml) |
| **Đăng nhập Mobile App** | `https://tour.quan4.vn/api/v1/auth/login` | `location /api/` -> `http://127.0.0.1:8000;` | `POST /api/v1/auth/login` | Native HTTPS request. Không phụ thuộc browser CORS. Rate-limit & JWT. | `EXPO_PUBLIC_API_BASE_URL` | `node mobile/tests/navigation.test.js` | [SD-DEPLOY-03](file:///d:/seminar/seminarchuyende/docs/diagrams/sequences/SD-DEPLOY-03-mobile-login.puml) |
| **Lấy cấu hình Bản đồ Q4** | `/api/v1/map/config` *(Same-Origin)* | `location /api/` -> `http://127.0.0.1:8000;` | `GET /api/v1/map/config` | Public endpoint (Không yêu cầu đăng nhập). Trả về tâm, bounds Q4, tile URL. | `MAP_TILE_STYLE_URL`<br>`MAP_BOUNDS_*` | `curl -s .../api/v1/map/config` | [AD-DEPLOY-01](file:///d:/seminar/seminarchuyende/docs/diagrams/activities/AD-DEPLOY-01-resolve-api-config.puml) |
| **Định tuyến Turn-by-turn OSRM** | `/api/v1/routes/preview` *(Same-Origin)* | `location /api/` -> `http://127.0.0.1:8000;` | `POST /api/v1/routes/preview` | Cache-first (`route_cache`). Fallback OSRM. Chuẩn SI (mét, giây). | `ROUTING_PROVIDER_URL`<br>`ROUTING_CACHE_TTL_HOURS` | `pytest tests/test_map_api.py` | [AD-DEPLOY-03](file:///d:/seminar/seminarchuyende/docs/diagrams/activities/AD-DEPLOY-03-request-flow.puml) |
| **Phát Thuyết Minh Âm Thanh** | `/storage/audio/{file}.mp3` | `location /storage/` -> `http://127.0.0.1:8000;` | Static Files `/storage` | Trả về file âm thanh với cache 7 ngày. Không chứa localhost:8000. | `MEDIA_STORAGE_DIR` | `curl -I .../storage/audio/...` | [deployment-architecture](file:///d:/seminar/seminarchuyende/docs/diagrams/deployment-architecture.puml) |
| **Thanh Toán Đơn Hàng VietQR** | `/api/v1/orders/{id}/payment-attempts` | `location /api/` -> `http://127.0.0.1:8000;` | `POST .../payment-attempts` | Tạo checkout URL với `PUBLIC_WEB_URL` (không hardcode localhost). | `PAYOS_*`<br>`PUBLIC_WEB_URL` | `pytest tests/test_payments.py` | [AD-DEPLOY-03](file:///d:/seminar/seminarchuyende/docs/diagrams/activities/AD-DEPLOY-03-request-flow.puml) |
| **Kiểm tra Sức khỏe Hệ thống** | `/api/v1/health` | `location /api/` -> `http://127.0.0.1:8000;` | `GET /api/v1/health` | Public Healthcheck không lộ secret. | `MONGODB_URL` | `curl -i .../api/v1/health` | [AD-DEPLOY-02](file:///d:/seminar/seminarchuyende/docs/diagrams/activities/AD-DEPLOY-02-deploy-rollback.puml) |

---

## 2. Quy Chuẩn Không Chứa Localhost Trong Mã Nguồn Client (Anti-Regression Rule)

| Vị Trí Trước Đây | Lỗi Cũ | Sửa Chữa Đã Hoàn Thành | Kiểm Tra Tự Động (Guard) |
| :--- | :--- | :--- | :--- |
| `frontend/admin/admin.js:1` | `const API_BASE = "http://localhost:8000/api/v1";` | `const API_BASE = resolveAdminApiBase();` (default: `/api/v1`) | `scripts/assert-no-client-localhost.mjs` |
| `frontend/client/app.js:997` | `http://localhost:8000${grantData.stream_url}` | Relative path stream URL tự động nhận origin của trang | `scripts/assert-no-client-localhost.mjs` |
| `apps/web-admin/src/config/runtime.ts` | Chưa có resolver tập trung | Module duy nhất `runtime.ts` validate & reject loopback | `scripts/assert-no-client-localhost.mjs` |
| `mobile/src/services/api.js` | Hardcoded `http://localhost:8000/api/v1` | `MOBILE_API_BASE_URL` qua `runtime.js` đọc env profile | `node mobile/tests/geofence.test.js` |
| `backend/app/services/payment_providers/` | Hardcoded `http://localhost:8000/client/...` | Dùng `settings.PUBLIC_WEB_URL` | `pytest tests/test_deployment_config.py` |
