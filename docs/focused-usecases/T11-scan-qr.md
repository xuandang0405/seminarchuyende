# T11 — Quét QR Để Nghe Thuyết Minh

## 1. Thông Tin Nhận Diện

- **Use Case ID:** T11
- **Use Case Name:** Quét QR để nghe thuyết minh
- **Module / System Boundary:** Phân hệ Ứng dụng Di động Khách du lịch (Mobile) & Backend API
- **Primary Actor:** Khách du lịch (Tourist)
- **Supporting Actors:** Camera thiết bị, Dịch vụ Giải mã QR Backend (`api.resolveQR`)
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (Backend integration test + Mobile CameraView & QR resolver)
- **Scope:** [G]; user-goal
- **Summary / Goal:** Khách du lịch sử dụng camera điện thoại quét mã QR được gắn tại địa điểm tham quan hoặc di tích để ứng dụng tự động nhận diện và phát kịch bản thuyết minh âm thanh tương ứng mà không cần bật định vị GPS.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Du khách bấm vào nút "Quét QR" trên màn hình bản đồ mobile.
- **Preconditions:** Ứng dụng đã khởi tạo thành công và đang ở chế độ sẵn sàng. Không yêu cầu tài khoản đăng nhập, không yêu cầu GPS và không yêu cầu đồng ý thu thập thống kê.
- **Assumptions:** Thiết bị có camera hoạt động được.
- **Success Postconditions:** Mã QR được giải mã thành công; POI được xác nhận hợp lệ; Trình phát đơn `NarrationController` bắt đầu phát âm thanh thuyết minh đúng ngôn ngữ hiện hành của khách.
- **Minimum Guarantees:** Mã QR sai hoặc hết hạn không bao giờ kích hoạt URL bên ngoài; lỗi quét không làm hỏng dữ liệu bộ nhớ máy; không tự ý gửi dữ liệu thống kê nếu chưa có sự đồng ý của khách (Consent F08).
- **Business Rules Liên Quan:** `BR-QR-01`, `BR-QR-02`, `BR-POI-01`, `BR-AUDIO-01`, `BR-AUDIO-02`, `BR-CONSENT-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **T11.B1** | Bấm nút "Quét QR" trên giao diện chính | Ứng dụng kiểm tra và yêu cầu quyền Camera (nếu chưa cấp), mở màn hình `QRScanScreen` với khung ngắm | E1 |
| **T11.B2** | Hướng camera vào mã QR dán tại địa điểm | CameraView quét mã, trích xuất chuỗi mã QR, kiểm tra định dạng hỗ trợ | BR-QR-01, E2 |
| **T11.B3** | — | Ứng dụng tạo yêu cầu tra cứu mã kèm ngôn ngữ hiển thị hiện hành, kiểm tra kết nối mạng | A1 |
| **T11.B4** | — | Hệ thống gửi `GET /api/v1/qr/{code}` lên máy chủ. Backend tra cứu collection `qr_codes`, kiểm tra `is_active=True`, thời hạn và POI liên kết | BR-POI-01, E3, E4 |
| **T11.B5** | — | Nhận thông tin POI hợp lệ; chuyển yêu cầu sang `NarrationController.requestNarration(poi, "qr", currentLang)` | BR-AUDIO-01, A2 |
| **T11.B6** | — | `NarrationController` phân giải nguồn âm thanh (`AudioSourceResolver`), tải audio stream từ server hoặc cache | BR-AUDIO-02, BR-AUDIO-03, E5 |
| **T11.B7** | Lắng nghe thuyết minh và điều khiển player | Audio bắt đầu phát thành công, hiển thị thanh `AudioPlayerBar` với nhãn "MÃ QR"; đóng màn hình quét trở về bản đồ | BR-CONSENT-01 |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **T11.A1 — Chế độ Ngoại tuyến (Offline QR Resolution)**:
  - **Điểm rẽ:** Tại bước `T11.B3` khi thiết bị không có kết nối Internet / 4G.
  - **Các bước con:**
    1. Ứng dụng tra cứu mã QR trong bảng snapshot ngoại tuyến (`qr_snapshots` trong AsyncStorage/SQLite) theo quy tắc `BR-QR-02`.
    2. Nếu tìm thấy mapping hợp lệ của POI đã tải trong gói offline, lấy thông tin POI và file âm thanh cục bộ.
  - **Điểm quay lại:** Nhập lại bước `T11.B5` để phát audio từ bộ nhớ máy. Nếu mã không có trong gói offline, thông báo du khách cần kết nối mạng.
- **T11.A2 — Đang có bài thuyết minh khác đang phát (Preemption)**:
  - **Điểm rẽ:** Tại bước `T11.B5` khi `NarrationController` đang phát một bài thuyết minh trước đó.
  - **Các bước con:**
    1. Theo quy tắc ưu tiên `BR-AUDIO-01`, thao tác quét QR của người dùng có quyền ưu tiên cao hơn và được phép ngắt bài đang phát.
    2. `NarrationController` chốt số liệu thời gian nghe của bài cũ, hủy luồng phát cũ và lập tức tải bài mới từ QR.
  - **Điểm quay lại:** Tiếp tục bước `T11.B6`.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **T11.E1 — Từ chối quyền truy cập Camera**:
  - **Điểm phát sinh:** Tại bước `T11.B1` khi người dùng không cấp quyền Camera.
  - **Phản hồi:** Hiển thị thông báo "Cần cấp quyền Camera để quét mã QR" kèm nút "Quay Lại Bản Đồ". Không gửi request audio.
- **T11.E2 — Mã QR sai định dạng hoặc không hợp lệ**:
  - **Điểm phát sinh:** Tại bước `T11.B2` khi mã quét được không thuộc cú pháp hệ thống.
  - **Phản hồi:** Hiển thị cảnh báo "Mã QR không đúng định dạng", cung cấp nút "Chạm để quét lại" hoặc nút quay lại.
- **T11.E3 — Mã QR đã bị vô hiệu hóa hoặc POI bị tắt**:
  - **Điểm phát sinh:** Tại bước `T11.B4` khi API trả về mã `is_active=False` hoặc POI chưa công bố.
  - **Phản hồi:** Hiển thị thông báo "Mã QR này hiện không khả dụng hoặc địa điểm đang tạm ngưng phục vụ".
- **T11.E4 — Lỗi kết nối máy chủ khi tra cứu online**:
  - **Điểm phát sinh:** Tại bước `T11.B4` khi mạng chập chờn hoặc timeout.
  - **Phản hồi:** Thông báo "Không thể kết nối máy chủ", cho phép bấm thử lại mà không làm crash ứng dụng.
- **T11.E5 — Không tìm thấy tệp âm thanh thuyết minh**:
  - **Điểm phát sinh:** Tại bước `T11.B6` khi POI chưa có audio phù hợp.
  - **Phản hồi:** Chuyển sang hiển thị phụ đề văn bản mô tả trên màn hình kèm thông báo âm thanh đang chuẩn bị.

---

## 6. Extension Points

- Không có extension point được mô hình hóa riêng (N01 được gọi theo quan hệ `<<include>>`).

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD05 (Quét QR), AD05 (Activity QR), AD16 (Narration dùng chung).
- **Màn hình UI:** `mobile/src/screens/QRScanScreen.js`, `mobile/src/components/AudioPlayerBar.js`.
- **API Endpoint:** `GET /api/v1/qr/{code}` (Router: `backend/app/api/v1/endpoints/qr.py`).
- **Service & Repository:** `app/services/qr_service.py`, `app/repositories/qr_repo.py`, Collection: `qr_codes`.
- **Bằng chứng kiểm thử:**
  - Backend integration test: `backend/tests/test_api.py::test_qr_resolution_standard` (Passed).
  - Mobile audio unit test: `mobile/tests/geofence.test.js` (Passed).
- **Acceptance Criteria:**
  - *Given:* Mã QR `Q4-BNR-01` của Bến Nhà Rồng đang active.
  - *When:* Khách mở camera quét mã.
  - *Then:* Server phản hồi `valid=True`, mã POI `poi_ben_nha_rong` và trình phát bắt đầu phát bài thuyết minh Bến Nhà Rồng.
