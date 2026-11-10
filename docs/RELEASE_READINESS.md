# Kiểm tra phát hành TourVoice

## Đối chiếu nguồn

Tham chiếu nghiệp vụ là system-presentation-standalone.html và ảnh yêu cầu đồ án được cung cấp. Theo thay đổi phạm vi ngày 10/11/2026, bản hiện tại chỉ giữ React Web App, router/service/repository và API/worker giao tiếp bằng MongoDB. Xem WEB_APP_SCOPE.md.

Tài liệu mô tả kiến trúc không thay thế bằng chứng chạy thật. Chưa coi bản đồ PMTiles, giao dịch ngân hàng thật hoặc kiểm thử nền trên thiết bị là hoàn tất chỉ vì xuất hiện trong sơ đồ thiết kế.

## Những nhóm lỗi đã sửa

| Nhóm | Hành vi sau sửa | Bằng chứng chính |
|---|---|---|
| Thanh toán | Bắt buộc đăng nhập; lấy giá từ catalog; một đơn cấp một quyền tour; không tin unit_price từ client | test_release_regressions.py, test_payments.py |
| Đơn hàng | Chỉ người sở hữu hoặc admin đọc được; bộ lọc đơn của du khách không gây TypeError | test_release_logic.py |
| Mô phỏng | Chỉ development/test và PAYMENT_MODE=mock | test_release_regressions.py |
| Webhook | Kiểm tra chữ ký trước chống trùng; khớp reference chính xác và số tiền; transaction cấp quyền và ghi thanh toán | test_entitlement_access_payment.py, verify_mongo.py |
| Đối soát | Gọi API payOS/VNPAY thay vì xem trạng thái local để kết luận đã trả tiền | adapter providers; cần merchant credentials để kiểm tra live |
| Bí mật và DB | Nhận alias cấu hình cũ; từ chối secret mẫu, DB mất kết nối và DB standalone ở production | config.validate_runtime, database.py |
| Đăng nhập | Web token ở bộ nhớ và cookie HttpOnly; tự làm mới token; CSRF cho cookie mutation | auth tests; smoke-browser.mjs |
| Quên mật khẩu | Gửi SMTP, không trả debug token ở production; production bắt buộc cấu hình SMTP | test_release_regressions.py |
| Mật khẩu dài | Hash toàn bộ mật khẩu; không cắt âm thầm tại 72 byte của bcrypt | test_release_logic.py |
| Chủ quán | Phải xác minh; chỉ sửa nội dung thuộc mình; payload không được chèn owner_id/is_active; vẫn đọc thông báo duyệt | moderation/menu tests, release logic tests |
| Duyệt nội dung | Quyết định, POI, localization, audio task và thông báo cùng transaction; kiểm tra lại POI chưa xóa và vẫn đúng owner | verify_mongo.py: lỗi ghi thông báo rollback toàn bộ; ba yêu cầu duyệt đồng thời chỉ một thành công |
| Lưu POI | Tạo/sửa POI, bản nội dung nguồn và enqueue worker dùng cùng session/transaction | poi_admin_service.py, verify_mongo.py |
| Tạo tuyến | Không phân giải POI bản nháp qua API routing công khai | routing_service.py |
| Công bố POI | Tạo bản nháp; sửa nguồn làm mất readiness; cần bản tiếng Anh đúng source_version và file audio có thật | test_poi_full_slice.py, release tests |
| Dịch và TTS | Dùng văn bản đang lưu; bỏ ghi đè bằng nội dung mẫu; không công bố kết quả cũ; không bịa URL/thời lượng | translation_service.py, test_release_logic.py |
| Worker | Tách tiến trình; lease/heartbeat/retry/backoff; progress; tạm dừng/tiếp tục/hủy; không báo hoàn tất khi mới queued | localization_worker.py, LocalizationJobs.tsx |
| Media | Audio private; không có static bypass; missing file trả lỗi; HTTP Range hợp lệ | release tests; entitlement acceptance tests |
| GPS | Engine GPS của Web App; accuracyM/accuracy, debounce 3 giây, cooldown 5 phút, ưu tiên/khoảng cách, suppression | shared/tests/geofence.test.mjs |
| Bộ phát | Một nguồn tại một thời điểm; bỏ kết quả cũ khi dừng/đổi ngôn ngữ | useTouristNarration.ts; browser MP3 playback |
| Offline | Tải file thật, checksum/size, staged commit, giấy phép Ed25519 7 ngày gắn tài khoản, kiểm tra trước phát | test_scenario_19, browser offline test |
| Analytics | Mặc định từ chối; device token thật; kiểm tra consent ở server; outbox ACK không ghi đè sự kiện mới | analytics tests, outbox services |
| Quản trị web | Tách trang người dùng/admin; phục hồi auth chung; bỏ đăng nhập admin mẫu; đúng redirect | browser smoke test |
| PWA | Bundle Leaflet; phục vụ SW/manifest/index/icon; precache app; chỉ cache runtime public data | browser offline reload test |
| Triển khai | Image chứa web build; Nginx trỏ backend container; worker và Mongo replica set; service lỗi làm deploy thất bại | Docker build, container health/smoke |
| CI/CD | Workflow kiểm thử và build trước; deploy thủ công qua production environment và SSH host đã cấu hình | .github/workflows/verify.yml |

## Kết quả xác minh

- Backend Python 3.12, dependency lock cài mới: 117 test qua; 5 cảnh báo deprecation của httpx trong test cũ.
- Web: TypeScript và Vite production build thành công; PWA bundle sinh đầy đủ.
- MongoDB 7 replica set riêng: tạo index hai lần; 5 checkout đồng thời cùng idempotency key cho ra một đơn; 5 callback trùng cấp đúng một entitlement; transaction lỗi rollback.
- Chromium ở viewport 390 × 844: header không tràn, guest resume, giá server, quyền tour, download offline, offline reload, phát MP3 blob thật, admin redirect và danh sách POI đều qua.
- Build image Linux hoàn chỉnh đã qua; health container kết nối MongoDB thật.

Các số trên là kết quả trong môi trường phát triển/kiểm thử, không phải số liệu tải hay cam kết hiệu năng production.

## Cần cấu hình trước khi phát hành

1. SECRET_KEY ngẫu nhiên ít nhất 32 ký tự; production không dùng DEBUG, mock DB hay mock payment.
2. OFFLINE_LICENSE_PRIVATE_KEY là seed Ed25519 32 byte mã hóa base64, khác SECRET_KEY. Pin public key ở VITE_LICENSE_PUBLIC_KEY khi phát hành client; đổi signing key cần quy trình cập nhật key.
3. SMTP_HOST, SMTP_FROM và cấu hình xác thực/TLS của hộp thư thật. Chưa thử gửi thư tới người dùng thật.
4. payOS/VNPAY credentials, return URL, webhook/IPN URL công khai HTTPS. Chưa chạy giao dịch tiền thật.
5. Google OAuth client/secret và redirect URI nếu bật đăng nhập Google; Gemini key/model nếu bật trợ lý AI. AI thiếu cấu hình trả lỗi rõ, không bịa nội dung/dịch hoặc tọa độ.
6. Web GPS cần HTTPS và quyền vị trí; kiểm tra thực địa trên trình duyệt điện thoại.
7. HTTPS reverse proxy phía ngoài cổng 8080 của Docker production; bản compose không tự cấp chứng chỉ TLS.
8. GitHub production environment, DEPLOY_HOST/USER/SSH_KEY/KNOWN_HOSTS và máy chủ chuẩn bị sẵn /opt/tourvoice, compose/env; registry login nếu image private.

Ví dụ tạo một giá trị ngẫu nhiên để tự điền vào env:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

## Giới hạn còn lại

- Chưa có bộ dữ liệu nền PMTiles/MBTiles được cung cấp. Offline hiện có nội dung, audio và ảnh tự lưu trữ; bản đồ nền và tạo tuyến mới cần mạng.
- tile.openstreetmap.org bị từ chối kết nối trong môi trường trình duyệt kiểm thử. UI thông báo lỗi nền bản đồ và giữ POI/audio; cần kiểm tra nhà cung cấp tile tại mạng triển khai. Không tải hàng loạt tile vào offline pack. Tuân theo https://operations.osmfoundation.org/policies/tiles/ hoặc dùng nhà cung cấp có hợp đồng phù hợp lưu lượng.
- GPS nền đã có registration, opt-in và native permissions, nhưng chưa được kiểm thử thực địa, khi OS kill app hay khi bật tiết kiệm pin. Không cam kết chạy liên tục trong mọi trạng thái OS.
- npm audit còn advisory low/moderate trong chuỗi công cụ build; chưa dùng force để hạ Expo hoặc ép phiên bản không tương thích. Không còn high/critical trong lần audit sau nâng cấp. Cần theo dõi upstream trước lần phát hành rộng.
- Giới hạn AI hiện là số request mỗi người/ngày; không phải kế toán token/chi phí nhà cung cấp.
- Không có phép đo tải đồng thời hoặc độ chính xác dịch thực địa. Không suy ra SLA từ unit test.

## Kiểm tra trình duyệt có thể lặp lại

Chỉ dùng database có tên bắt đầu tourvoice_review_ và APP_ENV=test. verify_browser_seed.py từ chối database ngoài phạm vi này. Cần một MP3 hợp lệ trong backend/storage/audio để làm fixture audio; file này chỉ kiểm tra chức năng phát, không đánh giá chất lượng ngôn ngữ.

Khởi tạo fixture bằng biến môi trường riêng, chạy API ở 127.0.0.1:18081, sau đó chạy:

```powershell
cd apps/web-admin
node scripts/smoke-browser.mjs
```

BROWSER_EXECUTABLE chỉ định đường dẫn Chrome/Chromium. TOURVOICE_TEST_URL đổi địa chỉ API. Tài khoản review-admin@example.org / ReviewPass@2026 chỉ tồn tại trong database kiểm thử do script này tạo.

## Nguồn kỹ thuật đã đối chiếu

- VNPAY querydr: https://sandbox.vnpayment.vn/apis/docs/truy-van-hoan-tien/querydr%26refund.html
- OpenStreetMap tile policy: https://operations.osmfoundation.org/policies/tiles/
- Hợp đồng API của dependency đã cài được kiểm tra qua package/type declarations và build.

## Báo cáo đồ án

[Bao_cao_do_an_TourVoice.docx](Bao_cao_do_an_TourVoice.docx) được lập theo bìa Trangbia.pdf và quy tắc viết do người dùng cung cấp. Bản kết xuất kiểm tra gồm 127 trang, 90 sơ đồ và 2 ảnh giao diện; 65 use case gốc được đối chiếu với 29 nhóm luồng, có thêm E01–E05 cho chức năng phát sinh từ mã thực thi. Mỗi nhóm có activity và sequence, cùng các sơ đồ use case, kiến trúc, DFD, ERD, lớp, trạng thái và CI/CD.

Bìa báo cáo đã được cập nhật đầy đủ thông tin: Nhóm 03, Nhóm lớp 02 (Sáng Thứ 7, tiết 1 → 5), Giảng viên hướng dẫn Th.S Phạm Thi Vương. Mục lục đã bổ sung đủ toàn bộ các đề mục nhánh 1.1, 1.2, 1.4, 2.1, 2.2, 3.1, 5.1, 5.2, 5.4, 6.1 và chèn trang Danh mục bảng (17 bảng). Chức năng chỉ ở mức thiết kế được đánh dấu trong sơ đồ và mô tả; không coi báo cáo là bằng chứng đã chạy payment thật, GPS nền trên thiết bị hay có nền bản đồ offline.
