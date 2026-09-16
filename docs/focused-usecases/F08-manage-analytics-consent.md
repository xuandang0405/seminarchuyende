# F08 — Quản Lý Đồng Ý Thu Thập Thống Kê (Analytics Consent)

## 1. Thông Tin Nhận Diện

- **Use Case ID:** F08
- **Use Case Name:** Quản lý đồng ý thu thập thống kê
- **Module / System Boundary:** Phân hệ Riêng Tư & Thống Kê (Privacy & Analytics Module)
- **Primary Actor:** Khách du lịch (Tourist)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_analytics.py::test_analytics_consent_and_batch_ingestion`, `mobile/src/services/AnalyticsOutbox.js`)
- **Scope:** [H/G]; user-goal
- **Summary / Goal:** Du khách có toàn quyền chủ động bật hoặc tắt sự cho phép thu thập dữ liệu thống kê ẩn danh (lượt nghe audio, thời gian nghe, lộ trình tour). Khi du khách từ chối hoặc thu hồi sự đồng ý, ứng dụng lập tức ngừng ghi nhận sự kiện mới và dọn dẹp hàng đợi outbox chưa gửi, đồng thời du khách vẫn sử dụng 100% tính năng bản đồ và thuyết minh bình thường.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Du khách mở mục "Cài Đặt" (Settings) trên bản đồ mobile và gạt công tắc "Đồng Ý Thu Thập Thống Kê".
- **Preconditions:** Ứng dụng mobile đang chạy.
- **Assumptions:** Không cần tài khoản đăng nhập để thiết lập quyền riêng tư.
- **Success Postconditions:** Trạng thái consent được lưu vào bộ nhớ máy (`tourvoice_analytics_consent`); `AnalyticsOutbox` cập nhật hành vi tương ứng.
- **Minimum Guarantees:** Từ chối thu thập thống kê không được phép cản trở du khách sử dụng bản đồ, nghe audio, quét QR hay đi tour (`BR-CONSENT-01`).
- **Business Rules Liên Quan:** `BR-CONSENT-01`, `BR-EVENT-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **F08.B1** | Bấm biểu tượng ⚙️ (Cài Đặt) trên bản đồ | Mở `SettingsModal`, đọc trạng thái consent hiện tại từ AsyncStorage | — |
| **F08.B2** | Xem giải thích mục đích thu thập dữ liệu | Giao diện nêu rõ: Thu thập ẩn danh nhằm nâng cao chất lượng dịch vụ du lịch Quận 4 | — |
| **F08.B3** | Gạt công tắc tắt hoặc bật consent | Cập nhật `analyticsOutbox.setConsent(enabled)` | BR-CONSENT-01, A1 |
| **F08.B4** | Đóng cửa sổ cài đặt | Lưu lựa chọn vào bộ nhớ thiết bị, tiếp tục tham quan | — |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **F08.A1 — Thu hồi sự đồng ý (Revoke Consent)**:
  - **Điểm rẽ:** Tại bước `F08.B3` khi du khách chuyển trạng thái từ Bật sang Tắt.
  - **Hành vi:** `AnalyticsOutbox` xóa sạch toàn bộ hàng đợi sự kiện chưa gửi trong `tourvoice_analytics_outbox`; các thao tác nghe và di chuyển sau đó hoàn toàn không được ghi nhận vào outbox.

---

## 5. Exception Paths

- Không có ngoại lệ gây lỗi.

---

## 6. Extension Points

- Không có extension point riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD11 (Ghi nhận analytics), AD11 (Activity analytics).
- **Màn hình UI:** `mobile/src/components/SettingsModal.js`.
- **Services:** `mobile/src/services/AnalyticsOutbox.js`.
- **Bằng chứng kiểm thử:** `backend/tests/test_analytics.py::test_analytics_consent_and_batch_ingestion` (Passed).
