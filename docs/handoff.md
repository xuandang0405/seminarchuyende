# Project Handoff & Developer Guide

Tài liệu bàn giao dự án, hướng dẫn sinh viên cách cài đặt, chạy ứng dụng từ đầu, sửa đổi mã nguồn và diễn tập bảo vệ đề tài Seminar.

---

## 1. Hướng dẫn Khởi động Nhanh từ Máy Mới

### Bước 1: Yêu cầu Môi trường
- **Python**: 3.12.x
- **Node.js**: 20.x hoặc 24.x & npm
- **MongoDB**: MongoDB Atlas Cluster hoặc MongoDB Community Server cục bộ có replica set
- **Thiết bị**: Máy ảo Android Studio hoặc điện thoại Android/iOS thật

### Bước 2: Khởi động Backend
```bash
cd backend
# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy server FastAPI
python run.py
```
- Swagger UI / OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Toàn bộ Schema OpenAPI: `backend/openapi.json`

### Bước 3: Khởi động Web Admin & Owner Portal
```bash
cd apps/web-admin
npm install
npm run dev
```
- Giao diện quản trị sẽ mở tại: `http://localhost:5173`.
- Build kiểm tra production: `npm run build`

### Bước 4: Khởi động Ứng dụng Di động Mobile
```bash
cd mobile
npm install
npx expo start
```
- Nhấn phím `a` để mở trên Android Emulator.
- Để chạy trên điện thoại thật: kết nối chung mạng Wifi/LAN và cập nhật địa chỉ IP máy tính trong `mobile/src/services/api.js` (hoặc biến `EXPO_PUBLIC_API_URL`).

### Bước 5: Chạy Bằng Docker Compose (Tùy chọn)
```bash
docker-compose up -d --build
```
Dựng tự động MongoDB Replica Set (`rs0`), Redis cache và Backend API.

---

## 2. Tài khoản Demo Khởi tạo Sẵn trong Hệ thống

| Tên người dùng / Email | Mật khẩu | Vai trò (Role) | Chức năng kiểm tra |
|---|---|---|---|
| `superadmin@tourvoice.vn` | `Admin@123456` | `super_admin` | Toàn quyền hệ thống, quản lý vai trò, audit logs |
| `admin@tourvoice.vn` | `Admin@123456` | `admin` | Quản trị POI, duyệt đăng ký, duyệt submission, TTS |
| `owner.verified@quan4.vn` | `Owner@123456` | `poi_owner` (Đã duyệt) | Soạn draft, gửi submission, quản lý menu, xem thống kê |
| `owner.pending@quan4.vn` | `Owner@123456` | `poi_owner` (Chờ duyệt)| Kiểm tra màn hình chờ xét duyệt hồ sơ |
| `tourist@test.vn` | `User@123456` | `user` | Tài khoản khách du lịch bình thường |

---

## 3. Bản Đồ Tra Cứu "Sửa Chức Năng Ở Đâu" Cho Sinh Viên

Khi giảng viên hoặc nhóm muốn thay đổi tham số hoặc luồng nghiệp vụ, sửa tại các file chính xác sau:

| Nghiệp vụ / Tham số muốn sửa | Vị trí file cần sửa | Giải thích |
|---|---|---|
| **Bán kính GPS, Debounce, Cooldown** | `mobile/src/services/GeofenceEngine.js` | Hằng số `debounceMs` (3s), `cooldownMs` (5 phút), `accuracyThresholdMeters` (35m) và tỷ lệ Hysteresis `triggerRadius * 1.5` |
| **Ưu tiên phát audio (Priority / Interruption)** | `mobile/src/services/NarrationController.js` | Quy tắc Manual/QR ưu tiên hơn GPS; GPS không ngắt Manual play; xử lý nút Stop chống re-trigger |
| **Địa chỉ API backend của mobile** | `mobile/src/services/api.js` | Sửa `API_BASE_URL` cho Android emulator (`10.0.2.2`), iOS (`localhost`) hoặc IP LAN máy thật |
| **Giọng đọc TTS (Edge-TTS)** | `backend/app/services/tts_service.py` | Cấu hình giọng tiếng Việt (`vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural`), tiếng Anh (`en-US-JennyNeural`), tiếng Pháp (`fr-FR-DeniseNeural`) |
| **Điều kiện công bố POI (Readiness Gate)** | `backend/app/services/poi_admin_service.py` | Hàm `toggle_activation`: yêu cầu bắt buộc phải có bản dịch tiếng Anh và audio hợp lệ mới cho phép `is_active=True` |
| **Quyền hạn & Danh mục 32 Permissions** | `backend/app/core/permissions.py` | Ma trận quyền cho 4 role (`super_admin`, `admin`, `poi_owner`, `user`) |
| **Kiểm tra quyền sở hữu IDOR của Owner** | `backend/app/services/owner_service.py` | Kiểm tra `poi.owner_id == actor_id`, không cho phép sửa trộm POI của chủ quán khác |
| **Thời gian phiên đăng nhập & Token Rotation** | `backend/app/services/auth_service.py` | Cơ chế gia hạn refresh token và thu hồi token family khi phát hiện reuse attack |
| **Dữ liệu Seed ban đầu (POI, Tour, QR)** | `backend/app/db/seed.py` | 10 địa điểm Quận 4 (Bến Nhà Rồng, Chợ Xóm Chiếu, Phố Ốc Vĩnh Khánh, Cầu Mống...), tọa độ GeoJSON, thực đơn món ăn |
| **Chính sách thu thập thống kê (Consent F08)** | `mobile/src/services/AnalyticsOutbox.js` | Bật/tắt lưu trữ outbox và truyền nhận sự kiện thống kê |

---

## 4. Kịch Bản Diễn Tập Demo Chấm Điểm Seminar (8 - 12 Phút)

### Phút 1 - 2: Giới thiệu Kiến Trúc & Đăng Nhập Phân Quyền
1. Mở Web Admin tại `http://localhost:5173/login`.
2. Đăng nhập bằng `superadmin@tourvoice.vn`: chỉ ra thanh Sidebar có đầy đủ Quản trị, Kiểm duyệt, Audit Logs, Tours, QR.
3. Đăng xuất và đăng nhập bằng `owner.verified@quan4.vn`: chứng minh thanh điều hướng tự động thu gọn chỉ còn "Quán Của Tôi", ngăn chặn leo thang đặc quyền (RBAC).

### Phút 3 - 4: Chủ Quán Soạn Thực Đơn & Gửi Đề Xuất
1. Trong vai trò chủ quán Ốc Oanh, thêm món "Ốc hương rang muối tuyết" vào thực đơn.
2. Gửi đề xuất cập nhật mô tả địa điểm. Hệ thống lưu thành `poi_submissions` trạng thái `pending`.
3. Kiểm tra phía public: POI trên mobile vẫn giữ nguyên nội dung cũ chưa đổi (bảo vệ tính toàn vẹn thông tin du lịch).

### Phút 5 - 6: Admin Kiểm Duyệt & Kích Hoạt Readiness Gate
1. Đăng nhập tài khoản `admin@tourvoice.vn` vào mục **Kiểm Duyệt**.
2. Duyệt submission của chủ quán kèm ghi chú "Nội dung hợp lệ".
3. Mở chi tiết POI: Nhấn "Tạo Thuyết Minh Bằng AI (Edge-TTS)" cho bản dịch tiếng Anh và tiếng Việt.
4. Bật công tắc "Công bố công khai": Hệ thống kiểm tra **Readiness Gate** (đủ bản dịch và audio tiếng Anh), chuyển sang trạng thái đã công bố.

### Phút 7 - 9: Khách Du Lịch Trải Nghiệm Trên Mobile
1. Mở ứng dụng Mobile: Bản đồ Quận 4 hiện các điểm ghim POI, vòng bán kính Geofence và đường viền lộ trình tour màu cam.
2. Chuyển đổi ngôn ngữ sang **English**: Tên địa điểm và mô tả lập tức chuyển sang tiếng Anh.
3. Nhấp vào POI "Bến Nhà Rồng": Mở Modal chi tiết xem ảnh, địa chỉ, lịch sử và thực đơn món ăn.
4. Nhấn nút "Nghe Thuyết Minh Âm Thanh": Thanh `AudioPlayerBar` phía dưới bắt đầu phát thuyết minh âm thanh thật qua mạng.
5. Thử nghiệm Quét QR: Mở màn hình quét QR, hướng vào mã QR của POI: hệ thống tức thì nhận diện và phát audio tương ứng.

### Phút 10 - 11: Chế Độ Ngoại Tuyến (Offline Mode)
1. Mở mục **Offline**: Nhấn "Tải Gói Dữ Liệu Quận 4 Về Máy".
2. Thanh tiến trình hiển thị 4 bước (tải metadata -> tải tour -> kiểm tra toàn vẹn -> lưu trữ nội bộ).
3. Bật chế độ máy bay (Airplane Mode) trên điện thoại / ngắt mạng:
   - Ứng dụng vẫn mở được bản đồ các điểm đã lưu.
   - Vẫn xem được danh sách và nội dung thuyết minh từ cache bộ nhớ máy.

### Phút 12: Thống Kê & Báo Cáo
1. Quay lại Web Admin mục **Bảng Điều Khiển**:
   - Hiển thị số lượt nghe thực tế vừa phát (`audio_plays`).
   - Thời gian nghe thực tế trung bình (`average_duration`).
   - Top các địa điểm được du khách lắng nghe nhiều nhất.
2. Mở mục **Nhật Ký Hệ Thống (Audit Logs)**: xem toàn bộ thao tác phê duyệt và thay đổi cấu hình đã được ghi nhận an toàn với mốc thời gian ISO 8601.

---

## 5. Danh Sách Lệnh Kiểm Thử Tự Động Để Báo Cáo

Khi giảng viên yêu cầu chứng minh mã nguồn đã được kiểm thử:

1. **Chạy toàn bộ 17 integration tests của Backend**:
   ```bash
   cd backend
   python -m pytest -v
   ```
   Kết quả: `17 passed in ~14s` (Auth, RBAC, Concurrency, Readiness Gate, Moderation, IDOR, Analytics).

2. **Chạy 6 unit tests của Geofence Engine Mobile**:
   ```bash
   cd mobile
   node --test tests/geofence.test.js
   ```
   Kết quả: `6 passed` (Haversine, Inaccurate accuracy filter, 3s Debounce, 5m Cooldown, Priority sorting, Stop suppression).

3. **Kiểm tra build production của Web Admin**:
   ```bash
   cd apps/web-admin
   npm run build
   ```
   Kết quả: `✓ built in 2.69s` (0 TypeScript / bundling errors).
