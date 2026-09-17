# Bảng Ma trận Truy vết Toàn diện: Quyền truy cập, Nghe thử & Thanh toán (Access, Trial & Payment Traceability Matrix)

Tài liệu này liên kết chặt chẽ giữa: **Quy tắc nghiệp vụ (`BR-*`)**, **Màn hình giao diện**, **API Endpoint**, **Service & Repository**, **MongoDB Collection & Ràng buộc**, **Kiểm thử nghiệm thu (`test_entitlement_access_payment.py`)**, và **Mã nguồn Sơ đồ thiết kế (Use Case, Sequence, Activity, ERD)**.

---

## 1. Danh mục Quy tắc Nghiệp vụ (Business Rules Index)

- **`BR-ACCESS-01`**: Mọi request truy cập nội dung media phải được cấp quyền qua server, không tin cậy cờ client.
- **`BR-ACCESS-02`**: Khách ẩn danh được cấp định danh ngẫu nhiên, lưu hash bí mật, có thời hạn và có thể claim sau khi đăng nhập.
- **`BR-ACCESS-03`**: Sau khi claim phiên khách, quota/tiến trình được hợp nhất một cách idempotent; không cấp thêm lượt mới.
- **`BR-ACCESS-04`**: Đăng xuất xóa sạch token và cache cục bộ, không tự sinh quota mới cho phiên cũ.
- **`BR-ACCESS-05`**: Quyền tải offline pack chỉ cấp cho tài khoản đã có Entitlement kích hoạt hợp lệ.
- **`BR-ACCESS-06`**: Giấy phép offline có thời hạn xác minh 7 ngày, tự động gia hạn khi có mạng.
- **`BR-ACCESS-07`**: Đăng xuất hoặc chuyển tài khoản sẽ khóa/xóa cache offline của người dùng cũ.
- **`BR-TRIAL-01`**: Quota nghe thử tối đa 1 lần phát hoàn chỉnh 1 POI trong 1 ngôn ngữ trên toàn bộ ứng dụng (`trial_policy_version=1`).
- **`BR-TRIAL-02`**: Nghe thử yêu cầu người dùng xác nhận chủ động; GPS không được tự động tiêu lượt.
- **`BR-TRIAL-03`**: Quá trình đặt trước (reserve) quota và phát hành grant được thực thi atomic; chống race condition.
- **`BR-TRIAL-04`**: Lỗi trước khi truyền dữ liệu media không bị mất quota; lỗi sau khi truyền chỉ cho phép retry cùng grant trong thời hạn.
- **`BR-TRIAL-05`**: Pause, resume, HTTP range request của cùng 1 grant không tính thêm lượt nghe thử.
- **`BR-PAY-01`**: Một đơn hàng chỉ mua một tour (`1 order = 1 tour`); không cho phép mua lại tour đã sở hữu.
- **`BR-PAY-02`**: Giá tour được snapshot từ cơ sở dữ liệu tại thời điểm tạo đơn bằng số nguyên VND; không nhận giá từ client.
- **`BR-PAY-03`**: Mọi Webhook / IPN phải được xác thực chữ ký số hợp lệ từ Provider (VNPAY / payOS).
- **`BR-PAY-04`**: Giao dịch phải khớp chính xác số tiền, loại tiền tệ VND và mã tham chiếu đơn hàng.
- **`BR-PAY-05`**: Xử lý sự kiện thanh toán đảm bảo tính idempotent; không hạ cấp đơn đã `paid` và không cấp trùng entitlement.
- **`BR-PAY-06`**: Cập nhật trạng thái đơn hàng và cấp quyền TourEntitlement trong cùng một MongoDB Transaction.
- **`BR-PAY-07`**: Sai lệch tiền tệ, thiếu tiền, thừa tiền hoặc quá hạn chuyển trạng thái đơn sang `requires_review` để Admin đối soát thủ công.
- **`BR-PAY-08`**: Người dùng hủy hoặc hết hạn thanh toán không làm mất quyền thử lại với attempt mới.

---

## 2. Bảng Ma trận Liên kết Chi tiết (Traceability Matrix)

| Quy tắc | Chức năng / Luồng | Màn hình | API Endpoint | Service / Layer | MongoDB / Ràng buộc | Mã Test Kiểm chứng | Use Case | Sequence | Activity |
|---|---|---|---|---|---|---|---|---|---|
| **BR-ACCESS-02** | Khởi tạo phiên khách | Welcome Screen (Web / Mobile) | `POST /api/v1/guest-sessions` | `GuestService.create_guest_session` | `guest_sessions` (unique `credential_hash`) | `test_guest_explore_and_trial_poi` | UC-PAY-01 | SD21 | AD17 |
| **BR-ACCESS-03** | Claim phiên khách vào tài khoản | Welcome / Login Modal | `POST /api/v1/guest-sessions/claim` | `GuestService.claim_guest_session` | `guest_sessions.claimed_user_id` | `test_guest_trial_used_then_register_no_new_quota` | UC-PAY-02 | SD21 | AD17 |
| **BR-TRIAL-01** | Kiểm tra quyền truy cập tour | Tour Detail / Audio Player | `GET /api/v1/tours/{id}/access` | `AccessService.evaluate_access` | `trial_usage`, `tour_entitlements` | `test_guest_explore_and_trial_poi` | UC-PAY-03 | SD22 | AD18 |
| **BR-TRIAL-02** | Hỏi ý kiến trước khi nghe thử | Modal Đồng ý Nghe thử | Frontend / Mobile Alert | `AccessService.request_playback` (consent=True) | N/A (Client check + Backend validation) | `test_gps_does_not_consume_trial_silently` | UC-PAY-03 | SD22 | AD18 |
| **BR-TRIAL-03** | Đặt trước quota & cấp grant | Nút Phát / GPS / QR | `POST /api/v1/playback-grants` | `TrialService.reserve_trial` + `PlaybackGrantService` | `trial_usage` (unique subject+version) | `test_concurrent_preview_requests_use_single_quota`, `test_idempotent_grant_request` | UC-PAY-03 | SD22 | AD18 |
| **BR-TRIAL-04** | Hoàn trả quota khi chưa giao media | Audio Streaming | `GET /api/v1/audio/stream/{poi_id}` | `AccessService.deliver_media` | `playback_grants.delivery_state` | `test_error_before_media_delivery_does_not_consume_quota` | UC-PAY-03 | SD22 | AD18 |
| **BR-TRIAL-05** | Range request / Pause / Resume | Audio Player | `GET /api/v1/audio/stream/{poi_id}` | Streaming Range Header Support | `playback_grants` (hợp lệ trong cửa sổ grant) | `test_pause_resume_range_requests_same_grant` | UC-PAY-03 | SD22 | AD18 |
| **BR-ACCESS-01** | Chặn nghe khi hết lượt (Paywall) | Paywall Modal | `POST /api/v1/playback-grants` | `AccessService.request_playback` | `trial_usage.state == 'consumed'` -> `403` | `test_replay_new_poi_blocked_after_trial` | UC-PAY-03 | SD22 | AD18 |
| **BR-PAY-01** | Tạo đơn mua tour | Checkout Modal | `POST /api/v1/orders` | `OrderService.create_order` | `orders` (unique `user_id, idempotency_key`) | `test_guest_cannot_create_order`, `test_already_owned_tour_prevents_duplicate_purchase` | UC-PAY-04 | SD23 | AD19 |
| **BR-PAY-02** | Khởi tạo cổng thanh toán (Visa/QR) | Checkout / VietQR Modal | `POST /api/v1/orders/{id}/payment-attempts` | `PaymentService.create_payment_attempt` | `payment_attempts` (unique `provider_reference`) | `test_tampered_price_or_user_rejected` | UC-PAY-04 | SD23 | AD19 |
| **BR-PAY-03** | Nhận Webhook / IPN VNPAY & payOS | Webhook Gateway | `GET /api/v1/payments/vnpay/callback`, `POST /payos/ipn` | `PaymentService.handle_provider_callback` | `payment_events` (unique `provider, event_key`) | `test_fake_callback_signature_rejected` | UC-PAY-05 | SD24 | AD20 |
| **BR-PAY-04** | Kiểm tra sai lệch số tiền / ngoại tệ | Backend / Admin Review | `PaymentService.process_settlement` | `PaymentService.process_settlement` | `orders.status == 'requires_review'` | `test_amount_mismatch_or_underpayment_moves_to_review` | UC-PAY-05 | SD24 | AD20 |
| **BR-PAY-05** | Xử lý sự kiện trùng / Idempotent | Webhook Gateway | `PaymentService.handle_provider_callback` | `PaymentService.handle_provider_callback` | `payment_events`, `orders.status` | `test_valid_callback_grants_single_entitlement_and_idempotent` | UC-PAY-05 | SD24 | AD20 |
| **BR-PAY-06** | Mở khóa Full Tour (Entitlement) | Màn hình Chờ / Tour đã mua | `GET /api/v1/me/tours`, `GET /orders/{id}` | `EntitlementService.grant_entitlement` | `tour_entitlements` (unique `user_id, tour_id`) | `test_crash_recovery_or_transaction_consistency` | UC-PAY-06 | SD24, SD25 | AD19, AD20 |
| **BR-PAY-07** | Admin xem & đối soát giao dịch | Web Admin - Đơn hàng | `POST /api/v1/orders/{id}/reconcile` | `PaymentService.reconcile_order` | `orders`, `payment_attempts` | `test_reconciliation_flow_for_pending_orders` | UC-PAY-07 | SD24 | AD20 |
| **BR-ACCESS-05** | Tải gói Offline kèm giấy phép ký | Offline Manager (Mobile) | `POST /api/v1/tours/{id}/offline-pack` | `OfflinePackageService.generate_pack_and_license` | `tour_entitlements` (bắt buộc `status="active"`) | `test_full_offline_pack_requires_entitlement` | UC-PAY-08 | SD26 | AD21 |
| **BR-ACCESS-06** | Kiểm tra hạn giấy phép offline (7 ngày) | Mobile Offline Player | `NarrationController.playOffline` | Local License Signature & Expiry Check | SQLite / Secure Storage Client | `test_full_offline_pack_requires_entitlement` | UC-PAY-08 | SD26 | AD21 |
| **BR-ACCESS-07** | Đăng xuất dọn sạch phiên & cache | Cài đặt / Đăng xuất | Client Session Manager | `POST /api/v1/auth/logout` | Token Blacklist & Device Secure Storage | `test_auth_isolation_and_idor_protection` | UC-PAY-01 | SD21 | AD21 |

---

## 3. Nhật ký Thay đổi Sơ đồ (Diagram Changelog)

| Ngày | Tác vụ | Loại sơ đồ | Tập tin cập nhật | Mô tả nội dung thay đổi |
|---|---|---|---|---|
| 2026-09-17 | Thêm mới | Use Case (PlantUML) | `docs/diagrams/usecases/access-payment.puml` | 8 use cases mới (`UC-PAY-01` đến `UC-PAY-08`) quản lý truy cập khách, nghe thử, đơn hàng và thanh toán. |
| 2026-09-17 | Thêm mới | Sequence (PlantUML) | `docs/diagrams/sequences/guest-claim.puml` | SD21: Luồng tạo phiên khách ẩn danh và claim hợp nhất khi đăng ký/đăng nhập. |
| 2026-09-17 | Thêm mới | Sequence (PlantUML) | `docs/diagrams/sequences/trial-playback.puml` | SD22: Luồng kiểm tra quota atomic và phát hành playback grant nghe thử. |
| 2026-09-17 | Thêm mới | Sequence (PlantUML) | `docs/diagrams/sequences/checkout.puml` | SD23: Luồng tạo đơn hàng, snapshot giá và khởi tạo phiên thanh toán VNPAY/payOS/MOCK. |
| 2026-09-17 | Thêm mới | Sequence (PlantUML) | `docs/diagrams/sequences/payment-confirmation.puml` | SD24: Luồng xử lý Webhook/IPN, xác thực chữ ký và cập nhật giao dịch atomic. |
| 2026-09-17 | Thêm mới | Sequence (PlantUML) | `docs/diagrams/sequences/paid-access.puml` | SD25: Luồng nghe toàn bộ tour sau khi đã sở hữu entitlement trên Web/Mobile. |
| 2026-09-17 | Thêm mới | Sequence (PlantUML) | `docs/diagrams/sequences/offline-entitlement.puml` | SD26: Luồng cấp gói dữ liệu offline và chữ ký giấy phép 7 ngày. |
| 2026-09-17 | Thêm mới | Activity (PlantUML) | `docs/diagrams/activities/entry-auth.puml` | AD17: Quy trình chào mừng, chọn khách, đăng nhập và giữ ngữ cảnh tour. |
| 2026-09-17 | Thêm mới | Activity (PlantUML) | `docs/diagrams/activities/trial-playback.puml` | AD18: Quy trình kiểm tra quyền, hỏi ý kiến nghe thử và kích hoạt paywall. |
| 2026-09-17 | Thêm mới | Activity (PlantUML) | `docs/diagrams/activities/purchase-tour.puml` | AD19: Quy trình chọn phương thức thanh toán, chuyển hướng cổng và chờ xác nhận. |
| 2026-09-17 | Thêm mới | Activity (PlantUML) | `docs/diagrams/activities/payment-reconciliation.puml` | AD20: Quy trình đối soát giao dịch, phát hiện bất thường và xử lý sự kiện idempotent. |
| 2026-09-17 | Thêm mới | Activity (PlantUML) | `docs/diagrams/activities/offline-access.puml` | AD21: Quy trình xác minh bản quyền offline 7 ngày và tự động gia hạn khi có mạng. |
| 2026-09-17 | Thêm mới | ERD (Eraser & PlantUML) | `docs/diagrams/database/payment-access.eraser`<br>`docs/diagrams/database/payment-access-erd.puml` | Mô hình 7 collection liên kết với `admin_users` và `tours`. |
