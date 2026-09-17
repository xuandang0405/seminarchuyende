# Project Handoff & Developer Guide
# Hệ thống Thuyết minh Du lịch Tự động Đa ngôn ngữ Quận 4

Tài liệu bàn giao dự án toàn diện, hướng dẫn nhóm 4 sinh viên cách cài đặt, chạy ứng dụng từ đầu, kiến trúc phân tầng, quản trị mã nguồn, kiểm thử tự động và kịch bản diễn tập chấm điểm Seminar / bảo vệ đồ án tốt nghiệp trong 10 tuần.

---

## 1. Kiến Trúc Hệ Thống & Nguyên Tắc Thiết Kế

Hệ thống được thiết kế theo đúng kiến trúc phân tầng chuẩn doanh nghiệp:
- **Web Du khách (Tourist Portal)**: Vanilla HTML5/CSS3/JavaScript hiện đại, giao diện dark mode sang trọng, responsive, tích hợp bản đồ Leaflet, Web Audio Player, giỏ hàng/thanh toán checkout.
- **Web Quản trị (Web Admin & Owner Portal)**: React.js (Vite) + TailwindCSS, quản lý POI, duyệt hồ sơ, TTS AI, quản lý giá tour (`pricing`), xem danh sách đơn hàng và nút **Đối soát giao dịch**.
- **Ứng dụng Di động (Mobile App)**: React Native (Expo), tích hợp bản đồ Geofence GPS tự động, quét mã QR POI, quản lý phiên khách/tài khoản trong Secure Storage, bộ đệm nghe ngoại tuyến và kiểm tra giấy phép 7 ngày.
- **Backend API**: FastAPI (Python 3.12+) tuân thủ triệt để mô hình phân lớp **Routers → Services → Repositories → MongoDB**.
  - Không nhét nghiệp vụ vào Routers.
  - Sử dụng MongoDB Multi-document Transactions cho các thao tác tài chính và cấp quyền.
  - Tích hợp cổng thanh toán qua mô hình Adapter `PaymentProvider` (`vnpay.py`, `payos.py`, `mock_provider.py`).
- **Cơ sở dữ liệu**: MongoDB (Replica Set). Giữ nguyên toàn bộ collection gốc (`POI`, `MenuItem`, `admin_users`, `roles`, `tours`...) và bổ sung 7 collection phục vụ kiểm soát truy cập và thanh toán.

---

## 2. Hướng Dẫn Khởi Động Nhanh Từ Máy Mới

### Bước 1: Yêu cầu Môi trường
- **Python**: 3.12.x trở lên
- **Node.js**: 20.x hoặc 24.x & npm
- **MongoDB**: MongoDB Server cục bộ (bật Replica Set) hoặc Docker Compose đi kèm
- **Thiết bị**: Máy ảo Android Studio / iOS Simulator hoặc điện thoại thật cài Expo Go

### Bước 2: Cấu hình Biến Môi trường Backend
Sao chép mẫu cấu hình và chỉnh sửa:
```bash
cd backend
cp .env.example .env
```
*Mặc định `PAYMENT_MODE=mock` được bật sẵn để chạy thử nghiệm cục bộ không cần tiền thật.*

### Bước 3: Khởi động MongoDB Replica Set
MongoDB 4.0+ bắt buộc Replica Set để hỗ trợ transactions. Chạy nhanh bằng Docker:
```bash
docker-compose up -d mongo
```
Hoặc cấu hình mongod cục bộ với tham số `--replSet rs0` và chạy lệnh `rs.initiate()` trong `mongosh`.

### Bước 4: Khởi động Backend FastAPI
```bash
cd backend
pip install -r requirements.txt
python run.py
```
- Máy chủ API chạy tại: `http://localhost:8000`
- Tài liệu tương tác Swagger UI: `http://localhost:8000/docs`
- Cổng du khách Web Client: `http://localhost:8000/client/index.html`

### Bước 5: Khởi động Web Admin & Owner Portal
```bash
cd apps/web-admin
npm install
npm run dev
```
- Giao diện mở tại: `http://localhost:5173`

### Bước 6: Khởi động Ứng dụng Di động Mobile
```bash
cd mobile
npm install
npx expo start
```
- Bấm `a` để mở Android Emulator, hoặc quét mã QR bằng Expo Go trên điện thoại thật.

---

## 3. Danh Mục Tài Khoản Demo Khởi Tạo Sẵn

| Email | Mật khẩu | Vai trò (Role) | Chức năng kiểm tra |
|---|---|---|---|
| `superadmin@tourvoice.vn` | `Admin@123456` | `super_admin` | Quản trị toàn hệ thống, cấu hình phân quyền, audit logs |
| `admin@tourvoice.vn` | `Admin@123456` | `admin` | Quản trị POI, cấu hình giá tour, duyệt hồ sơ, đối soát giao dịch |
| `owner.verified@quan4.vn` | `Owner@123456` | `poi_owner` (Đã duyệt) | Quản lý menu quán, gửi đề xuất cập nhật POI |
| `owner.pending@quan4.vn` | `Owner@123456` | `poi_owner` (Chờ duyệt)| Màn hình chờ duyệt hồ sơ của chủ quán |
| `tourist@test.vn` | `User@123456` | `user` | Tài khoản du khách đã mua tour demo |
| `tourist.new@test.vn` | `User@123456` | `user` | Tài khoản du khách mới (chưa mua tour, còn 1 lượt nghe thử) |

---

## 4. Bản Đồ Tra Cứu "Sửa Chức Năng Ở Đâu" Cho Sinh Viên

| Nghiệp vụ / Tham số muốn sửa | Vị trí file mã nguồn | Hướng dẫn chi tiết |
|---|---|---|
| **Chính sách Nghe thử (Trial Policy)** | `backend/app/services/trial_service.py` | Hằng số `TRIAL_POLICY_VERSION = 1`, `MAX_FREE_PLAYS = 1`. Kiểm tra điều kiện `subject_type`, `state` ("available" -> "reserved" -> "consumed"). |
| **Kiểm soát Truy cập & Paywall Backend** | `backend/app/services/access_service.py` | Hàm `evaluate_access`: kiểm tra quyền sở hữu tour, quota nghe thử, cấp mã token phát hành `playback_grants`. |
| **Cổng Thanh toán (VNPAY, payOS, Mock)** | `backend/app/services/payment_providers/` | `vnpay.py`: Hosted checkout URL, mã hóa HMAC-SHA512, đơn vị VND x 100.<br>`payos.py`: Dynamic VietQR API, xác thực webhook HMAC-SHA256.<br>`mock_provider.py`: Trả về QR và URL giả lập cho môi trường dev. |
| **Xử lý Đơn hàng & Đối soát** | `backend/app/services/payment_service.py` | Hàm `handle_provider_callback` và `reconcile_order`: kiểm tra chữ ký, đối chiếu số tiền, xử lý MongoDB transaction atomic, chuyển trạng thái `paid` hoặc `requires_review`. |
| **Gói Offline & Giấy phép 7 Ngày** | `backend/app/services/offline_package_service.py` | Hàm `generate_pack_and_license`: tạo chữ ký HMAC cho license offline, cấu hình thời hạn `expires_at = NOW() + 7 days`. |
| **Giao diện Web Du khách** | `backend/app/static/client/index.html`<br>`backend/app/static/client/app.js` | Quản lý Welcome Modal, lưu session khách/user trong localStorage, gọi grant API, kích hoạt Paywall Modal, Checkout Modal, VietQR popup, danh sách "Tour của tôi". |
| **Giao diện Web Admin (Giá & Đơn hàng)** | `apps/web-admin/src/pages/` | `OrdersPage.jsx`: Danh sách đơn hàng, trạng thái, nút "Đối soát giao dịch".<br>`TourListPage.jsx`: Modal cấu hình giá tour (`price_amount`, `is_purchasable`). |
| **Bộ điều khiển Thuyết minh Mobile** | `mobile/src/services/NarrationController.js` | Hàm `playNarration`: gọi `api.requestPlaybackGrant`, bắt sự kiện `TRIAL_CONSENT_REQUIRED`, bắt sự kiện `PAYWALL_REQUIRED`, đính kèm `grant_token` khi stream. |
| **Màn hình Chào Mobile (Welcome Screen)** | `mobile/src/components/AuthWelcomeModal.js` | Modal chọn "Tiếp tục với tư cách Khách", "Đăng nhập", "Đăng ký", lưu token an toàn trong `AsyncStorage` / Secure Storage. |
| **Quản lý Tải Offline Mobile** | `mobile/src/screens/OfflineScreen.js` | Kiểm tra quyền `has_entitlement` trước khi cho phép tải, lưu license và kiểm tra hết hạn 7 ngày. |

---

## 5. Danh Mục Quy Tắc Nghiệp Vụ Đã Triển Khai (Business Rules)

Hệ thống đã triển khai đầy đủ và kiểm thử nghiệm thu 100% các quy tắc:
- `BR-ACCESS-01` đến `BR-ACCESS-07`: Kiểm soát quyền truy cập nội dung media, bảo mật định danh khách ngẫu nhiên, claim idempotent, cô lập dữ liệu IDOR, bản quyền offline 7 ngày.
- `BR-TRIAL-01` đến `BR-TRIAL-05`: Quota 1 lượt phát hoàn chỉnh 1 POI trong 1 ngôn ngữ trên toàn app, yêu cầu người dùng xác nhận chủ động, GPS không được tự ý tiêu lượt, atomic reservation, hỗ trợ pause/resume cùng grant.
- `BR-PAY-01` đến `BR-PAY-08`: Một đơn mua một tour, snapshot giá VND từ database, xác thực chữ ký Webhook VNPAY & payOS, đối soát số tiền và tiền tệ, xử lý idempotent, MongoDB multi-document transaction, chuyển trạng thái `requires_review` khi có bất thường.

---

## 6. Kịch Bản Diễn Tập Chấm Điểm Seminar (10 - 15 Phút)

Giảng viên và hội đồng có thể trực tiếp trải nghiệm hoặc sinh viên thực hiện theo các bước sau:

### Bước 1: Mở Trải Nghiệm Khách Ẩn Danh (Guest Flow)
1. Mở trình duyệt vào `http://localhost:8000/client/index.html` (hoặc mở ứng dụng Mobile).
2. Màn hình Chào mừng (Welcome Modal) hiện lên với 3 lựa chọn: **Đăng nhập**, **Đăng ký**, hoặc **Tiếp tục với tư cách Khách**.
3. Bấm **"Tiếp tục với tư cách Khách"**: Hệ thống tạo phiên khách ngẫu nhiên, lưu `guest_id` và token an toàn, hiển thị trạng thái "Khách ẩn danh (Lượt nghe thử: 1/1)".
4. Khám phá bản đồ Quận 4, danh sách tour ẩm thực, xem thông tin chi tiết các POI, thực đơn món ăn và hình ảnh hoàn toàn công khai.

### Bước 2: Nghe Thử Miễn Phí (Trial Playback)
1. Chọn POI "Bến Nhà Rồng" và bấm nút **"Nghe Thuyết Minh"** (hoặc di chuyển vào Geofence GPS).
2. Hộp thoại xác nhận hiện ra: *"Bạn có 1 lượt nghe thử miễn phí. Bạn có muốn sử dụng cho Bến Nhà Rồng không?"*.
3. Bấm **"Đồng ý nghe thử"**: Backend thực thi atomic reservation, cấp `playback_grant` và phát âm thanh thuyết minh.
4. Thử nghiệm Pause và Resume: Audio tiếp tục phát bình thường không bị tính thêm lượt.
5. Thanh trạng thái cập nhật: *"Lượt nghe thử: 0/1 (Đã dùng)"*.

### Bước 3: Chặn Paywall Khi Hết Lượt (Paywall Trigger)
1. Thử bấm nghe lại POI đó hoặc chọn POI khác (ví dụ "Chợ Xóm Chiếu"):
2. Hệ thống tức thì chặn lại và hiển thị **Paywall Modal**:
   - Thông báo: *"Bạn đã sử dụng hết 1 lượt nghe thử miễn phí."*
   - Hiển thị thông tin Tour: "Tour Khám Phá Ẩm Thực & Lịch Sử Quận 4".
   - Giá tour niêm yết: **59.000 đ** (Quyền nghe không giới hạn vĩnh viễn, tải offline 7 ngày).
   - Nút hành động: **"Mua Ngay"**.

### Bước 4: Đăng Ký Tài Khoản & Hợp Nhất Dữ Liệu (Account Upgrade)
1. Bấm **"Mua Ngay"**: Hệ thống yêu cầu đăng nhập tài khoản để gắn quyền sở hữu tour.
2. Bấm **"Đăng ký tài khoản mới"**: Nhập họ tên, email mới (ví dụ `student@tourguide.vn`) và mật khẩu.
3. Đăng ký thành công: Hệ thống tự động đăng nhập và gọi `POST /api/v1/guest-sessions/claim` để hợp nhất quota cũ của khách vào tài khoản. Lượt nghe thử vẫn giữ trạng thái đã dùng (không được cấp thêm lượt gian lận).
4. Hệ thống giữ nguyên ngữ cảnh và tự động chuyển ngay vào màn hình **Tóm tắt Đơn hàng (Checkout)**.

### Bước 5: Thanh Toán Tour (Checkout & Payment Gateway)
1. Trên màn hình Checkout, chọn phương thức thanh toán:
   - **Thẻ Visa / Thẻ Quốc tế (VNPAY)**: Chuyển hướng sang cổng hosted checkout của VNPAY.
   - **QR Chuyển khoản (VietQR payOS)**: Hiển thị mã QR động, thông tin ngân hàng và mã nội dung chuyển khoản độc nhất.
   - **Mô phỏng Sandbox (Mock)**: Dành cho demo cục bộ.
2. Bấm **"Thanh toán ngay"**: Hệ thống tạo Order trạng thái `pending_payment` với snapshot giá 59.000 VND từ database.
3. Khi quét thanh toán thành công (hoặc bấm nút "Mô phỏng thanh toán thành công"):
   - Backend nhận webhook / đối soát giao dịch.
   - Xác thực chữ ký điện tử.
   - Thực thi **MongoDB Transaction**: Cập nhật PaymentAttempt = `succeeded`, Order = `paid`, và tạo `TourEntitlement` trạng thái `active`.
4. Màn hình Client nhận được tín hiệu thành công, hiển thị pháo hoa chúc mừng và thông báo: *"Bạn đã sở hữu tour thành công!"*.

### Bước 6: Thưởng Thức Full Tour & Nghe Không Giới Hạn
1. Bấm nút **"Bắt đầu nghe ngay"**: Toàn bộ các POI trong tour đã được mở khóa hoàn toàn.
2. Phát bất kỳ POI nào (Bến Nhà Rồng, Chợ Xóm Chiếu, Phố Ốc Vĩnh Khánh...): Âm thanh phát mượt mà, không bị chặn hay tiêu tốn quota.
3. Mở mục **"Tour của tôi"**: Hiển thị danh sách các tour đã mua kèm ngày cấp quyền.

### Bước 7: Trải Nghiệm Đa Thiết Bị (Cross-Device Entitlement)
1. Mở một trình duyệt ẩn danh khác hoặc mở ứng dụng React Native trên điện thoại.
2. Đăng nhập bằng đúng tài khoản `student@tourguide.vn` vừa mua.
3. Ngay lập tức, tài khoản đã có quyền sở hữu tour trên thiết bị mới mà không cần mua lại!

### Bước 8: Tải Gói Ngoại Tuyến (Offline Mode & License 7 Ngày)
1. Trên ứng dụng Mobile, mở mục **"Tải Tour Ngoại Tuyến"**.
2. Hệ thống kiểm tra Entitlement: Hợp lệ -> Tải gói âm thanh và cấp giấy phép có chữ ký số (thời hạn 7 ngày).
3. Bật Chế độ máy bay (Airplane Mode) trên điện thoại:
   - Bấm phát thuyết minh POI: Ứng dụng xác minh chữ ký offline license cục bộ và phát audio từ bộ nhớ máy thành công không cần mạng!

### Bước 9: Quản Trị Viên Đối Soát & Cấu Hình Giá (Admin Dashboard)
1. Đăng nhập Web Admin bằng tài khoản `admin@tourvoice.vn`.
2. Mở mục **Đơn hàng & Thanh toán**:
   - Xem đơn hàng vừa thanh toán của du khách `student@tourguide.vn`.
   - Xem mã tham chiếu giao dịch cổng, số tiền 59.000 VND, trạng thái `paid`.
   - Nút **"Đối soát giao dịch"**: Gọi API trực tiếp sang Provider để xác nhận tính toàn vẹn độc lập.
3. Mở mục **Quản lý Tour**:
   - Nhấn nút "Cấu hình giá": Sửa giá bán tour, bật/tắt quyền mở bán (`is_purchasable`).

---

## 7. Kết Quả Kiểm Thử Nghiệm Thu Tự Động (Automated Test Report)

Toàn bộ hệ thống được bảo vệ bởi bộ kiểm thử tự động gồm **49 bài kiểm thử** (tất cả đều ĐẠT 100%):

```bash
cd backend
pytest -v
```

### Chi tiết các Suite kiểm thử:
1. **`test_entitlement_access_payment.py` (21 tests / 22 kịch bản BR)**:
   - `test_guest_explore_and_trial_poi`: Khách khám phá và nghe thử thành công 1 POI.
   - `test_replay_new_poi_blocked_after_trial`: Chặn nghe lại và chặn POI mới khi hết quota.
   - `test_concurrent_preview_requests_use_single_quota`: Đảm bảo gọi đồng thời chỉ tiêu 1 lượt.
   - `test_idempotent_grant_request`: Idempotent cho cùng request grant.
   - `test_gps_does_not_consume_trial_silently`: GPS không tiêu quota ngầm khi chưa có consent.
   - `test_error_before_media_delivery_does_not_consume_quota`: Lỗi trước cấp media không mất lượt.
   - `test_pause_resume_range_requests_same_grant`: Pause/resume/range request không mất thêm lượt.
   - `test_guest_trial_used_then_register_no_new_quota`: Đăng ký tài khoản sau khi dùng trial không được cấp thêm.
   - `test_guest_cannot_create_order`: Khách không được tạo đơn mua hàng.
   - `test_tampered_price_or_user_rejected`: Chặn client sửa giá hoặc sửa user ID trong đơn.
   - `test_fake_callback_signature_rejected`: Chặn Webhook giả mạo sai chữ ký số.
   - `test_return_url_or_client_claim_does_not_unlock`: Không mở khóa bằng return URL giả mạo.
   - `test_valid_callback_grants_single_entitlement_and_idempotent`: Webhook hợp lệ cấp entitlement idempotent.
   - `test_crash_recovery_or_transaction_consistency`: Nhất quán dữ liệu giao dịch MongoDB.
   - `test_reconciliation_flow_for_pending_orders`: Đối soát đơn pending sang paid.
   - `test_amount_mismatch_or_underpayment_moves_to_review`: Thiếu tiền/sai tiền tệ chuyển sang `requires_review`.
   - `test_already_owned_tour_prevents_duplicate_purchase`: Chặn mua lặp tour đã sở hữu.
   - `test_auth_isolation_and_idor_protection`: Chặn IDOR giữa các người dùng.
   - `test_full_offline_pack_requires_entitlement`: Tải offline pack bắt buộc có entitlement active.
   - `test_admin_and_user_rbac_boundaries`: Phân quyền RBAC chặt chẽ, du khách trả tiền không thành admin.
   - `test_mock_mode_behavior`: Chế độ mock an toàn cho dev/demo.

2. **`test_integration.py` (17 tests)**:
   - Kiểm tra toàn diện Auth, RBAC 4 Roles, Concurrency, Readiness Gate, Moderation, Owner IDOR, Analytics.

3. **`test_login_google_security.py` (5 tests)**:
   - Kiểm tra Token Rotation, Brute Force Protection, Google Login Token Exchange, Session Invalidation.

4. **`test_focused_use_cases.py` (6 tests)**:
   - Kiểm tra hợp nhất ngôn ngữ POI, đa ngôn ngữ, menu món ăn và TTS.

---

## 8. Danh Mục Mã Nguồn Sơ Đồ Thiết Kế (Diagram Source Files)

Mọi thay đổi hành vi nghiệp vụ đều đi kèm mã nguồn sơ đồ hoàn chỉnh trong thư mục `docs/diagrams/`:

- **Sơ đồ Trường hợp Sử dụng (Use Case - PlantUML)**:
  - `docs/diagrams/usecases/access-payment.puml` (Bao gồm UC-PAY-01 đến UC-PAY-08)
- **Sơ đồ Trình tự (Sequence Diagrams - PlantUML)**:
  - `docs/diagrams/sequences/guest-claim.puml` (SD21: Tạo phiên khách & Claim)
  - `docs/diagrams/sequences/trial-playback.puml` (SD22: Quota atomic & Cấp grant)
  - `docs/diagrams/sequences/checkout.puml` (SD23: Tạo đơn & Khởi tạo cổng thanh toán)
  - `docs/diagrams/sequences/payment-confirmation.puml` (SD24: Xác minh Webhook & Giao dịch)
  - `docs/diagrams/sequences/paid-access.puml` (SD25: Quyền nghe full tour đã mua)
  - `docs/diagrams/sequences/offline-entitlement.puml` (SD26: Tải dữ liệu offline & Chữ ký license)
- **Sơ đồ Hoạt động (Activity Diagrams - PlantUML)**:
  - `docs/diagrams/activities/entry-auth.puml` (AD17: Đăng nhập / Đăng ký / Tiếp tục với tư cách khách)
  - `docs/diagrams/activities/trial-playback.puml` (AD18: Hỏi ý kiến nghe thử & Paywall)
  - `docs/diagrams/activities/purchase-tour.puml` (AD19: Luồng mua và thanh toán tour)
  - `docs/diagrams/activities/payment-reconciliation.puml` (AD20: Đối soát giao dịch & Xử lý bất thường)
  - `docs/diagrams/activities/offline-access.puml` (AD21: Bản quyền offline 7 ngày & Tự động gia hạn)
- **Sơ đồ Cơ sở Dữ liệu (ERD)**:
  - `docs/diagrams/database/payment-access.eraser` (Định dạng Eraser)
  - `docs/diagrams/database/payment-access-erd.puml` (Định dạng PlantUML ERD)
- **Ma trận Truy vết & Tích hợp**:
  - `docs/feature-integration-matrix.md`: Ma trận tích hợp toàn bộ màn hình, API và nút bấm.
  - `docs/traceability/access-payment-matrix.md`: Ma trận liên kết Business Rules với Code, Test và Diagram.
  - `docs/business-rules.md`: Bảng chi tiết toàn bộ các quy tắc BR-ACCESS, BR-TRIAL, BR-PAY.
