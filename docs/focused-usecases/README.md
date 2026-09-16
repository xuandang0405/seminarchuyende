# Bộ Đặc Tả Focused Use Cases — Hệ thống Thuyết minh Du lịch Đa ngôn ngữ

Tài liệu này đóng vai trò mục lục và hướng dẫn cách đọc bộ hồ sơ đặc tả chi tiết các Use Case theo tiêu chuẩn **Focused Use Cases**.

---

## 1. Mục Đích Áp Dụng

Mô hình Focused Use Cases giúp làm rõ:
- Tác nhân thực tế (**Primary Actor** & **Supporting Actors**) và ranh giới hệ thống (**System Boundary**).
- Chuỗi sự kiện cơ bản (**Basic Course of Events**) dạng bảng: **Actor Action** vs **System Response**.
- Các nhánh thay thế (**Alternative Paths**) và nhánh ngoại lệ (**Exception Paths**) với mã bước duy nhất.
- Hậu điều kiện thành công (**Success Postconditions**) và đảm bảo tối thiểu (**Minimum Guarantees**).
- Liên kết với **Business Rules (`BR-*`)**, sơ đồ Sequence (`SD*`), Activity (`AD*`), REST API endpoints, Database collections và Test cases.

---

## 2. Quy Ước Mã Nhận Diện (ID Conventions)

- **Use Case ID**: Giữ nguyên danh mục 65 mã nghiệp vụ đã thống nhất:
  - `T01` – `T13`: Khách du lịch, tìm kiếm, bản đồ và nghe thuyết minh.
  - `N01` – `N02`: Subflows điều phối âm thanh dùng chung và chuẩn bị audio.
  - `F01` – `F08`: Ngoại tuyến (Offline), đồng bộ và đồng ý thống kê.
  - `U01` – `U03`: Tài khoản, xác thực, đổi mật khẩu.
  - `O01` – `O10`: Cổng thông tin chủ quán, đăng ký, soạn thảo và thực đơn.
  - `C01` – `C16`: Quản trị nội dung, kiểm duyệt, TTS, tour và mã QR.
  - `S01` – `S13`: Quản trị hệ thống, phân quyền và bảng điều khiển thống kê.
- **Step ID**: `[UC_ID].B[Số]` cho luồng chính (Ví dụ: `T11.B1`, `T11.B2`).
- **Alternative Path ID**: `[UC_ID].A[Số]` (Ví dụ: `T11.A1` cho nhánh Offline).
- **Exception Path ID**: `[UC_ID].E[Số]` (Ví dụ: `T11.E1` cho nhánh từ chối quyền Camera).
- **Business Rule ID**: `BR-[NHÓM]-[Số]` (Ví dụ: `BR-AUTH-01`, `BR-GEO-01`, `BR-POI-01`).

---

## 3. Danh Mục Các Hồ Sơ Use Case Chi Tiết

| File đặc tả | Tên Use Case | Actor chính | SD / AD liên quan | Trạng thái Code / Test |
|---|---|---|---|---|
| [`T11-scan-qr.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/T11-scan-qr.md) | Quét QR để nghe thuyết minh | Khách du lịch | SD05, AD05, AD16 | Đã code & kiểm thử |
| [`C07-review-submission.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/C07-review-submission.md) | Xét duyệt nội dung chủ quán gửi | Admin | SD10, AD10 | Đã code & kiểm thử |
| [`U01-login.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/U01-login.md) | Đăng nhập cổng quản trị hoặc chủ quán | Admin / Owner | SD02, AD02 | Đã code & kiểm thử |
| [`C01-C02-manage-poi.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/C01-C02-manage-poi.md) | Thêm, sửa và kiểm soát công bố POI | Admin | SD03, AD03 | Đã code & kiểm thử |
| [`C06-review-registration.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/C06-review-registration.md) | Duyệt hồ sơ đăng ký chủ quán | Admin | SD10, AD10 | Đã code & kiểm thử |
| [`O01-register-owner.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/O01-register-owner.md) | Đăng ký làm chủ quán kinh doanh | Chủ quán | SD08, AD08 | Đã code & kiểm thử |
| [`O05-submit-poi-content.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/O05-submit-poi-content.md) | Gửi nội dung quán chờ xét duyệt | Chủ quán | SD09, AD09 | Đã code & kiểm thử |
| [`T08-T09-T10-audio-narration.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/T08-T09-T10-audio-narration.md) | Thuyết minh âm thanh (Bấm tay, GPS tự động, Điều khiển) | Khách du lịch | SD04, AD04, AD16 | Đã code & kiểm thử |
| [`N01-N02-narration-subflows.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/N01-N02-narration-subflows.md) | Subflow điều phối phát và chuẩn bị âm thanh | Hệ thống / Subflow | SD04, SD07, AD16 | Đã code & kiểm thử |
| [`F02-download-offline-pack.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/F02-download-offline-pack.md) | Tải & cập nhật gói dữ liệu ngoại tuyến | Khách du lịch | SD06, AD06 | Đã code & kiểm thử |
| [`F08-manage-analytics-consent.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/F08-manage-analytics-consent.md) | Quản lý đồng ý thu thập thống kê | Khách du lịch | SD11, AD11 | Đã code & kiểm thử |
| [`T12-T13-walking-tours.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/T12-T13-walking-tours.md) | Chọn và tham gia tuyến tour đi bộ | Khách du lịch | SD14, AD14 | Đã code & kiểm thử |
| [`C11-C13-tts-audio-tasks.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/C11-C13-tts-audio-tasks.md) | Tạo audio TTS và điều khiển tác vụ nền | Admin | SD07, AD07 | Đã code & kiểm thử |
| [`C14-ai-description.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/C14-ai-description.md) | Dùng AI gợi ý mô tả bản nháp | Admin / Owner | SD15, AD15 | Đã code & kiểm thử |
| [`S05-S07-analytics-dashboard.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/S05-S07-analytics-dashboard.md) | Bảng điều khiển thống kê du lịch | Admin | SD12, SD13, AD12 | Đã code & kiểm thử |
| [`O10-owner-statistics.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/O10-owner-statistics.md) | Xem thống kê số liệu của riêng quán | Chủ quán | SD13, AD13 | Đã code & kiểm thử |
