# S05 & S07 — Bảng Điều Khiển Thống Kê Du Lịch

## 1. Thông Tin Nhận Diện

- **Use Case ID:** S05 (Xem dashboard thống kê), S06 (Top POI nghe nhiều), S07 (Thời gian nghe trung bình)
- **Use Case Name:** Xem bảng điều khiển thống kê du lịch
- **Module / System Boundary:** Phân hệ Thống Kê & Báo Cáo (Web Admin) & Backend API
- **Primary Actor:** Quản trị viên (Admin / Super Admin có quyền `analytics:view`)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_analytics.py::test_analytics_dashboard`)
- **Scope:** [H/G]; user-goal
- **Summary / Goal:** Quản trị viên xem tổng quan hoạt động du lịch tại Quận 4: tổng số lượt nghe thuyết minh thành công, thời gian nghe trung bình của du khách trên từng địa điểm, bảng xếp hạng các điểm di tích/ẩm thực thu hút nhất và mốc thời gian cập nhật số liệu.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Admin truy cập vào trang chủ Dashboard (`/`).
- **Preconditions:** Admin đã đăng nhập với quyền `analytics:view`.
- **Assumptions:** Sự kiện nghe từ khách đã được đồng bộ qua batch outbox.
- **Success Postconditions:** Hiển thị số liệu tổng hợp chính xác; công thức tính thời gian nghe trung bình chia đúng cho `listens_count` (`BR-METRIC-01`).
- **Minimum Guarantees:** Không bao giờ xảy ra lỗi chia cho 0 (`ZeroDivisionError`) khi hệ thống chưa có lượt nghe nào; không làm lộ dữ liệu cá nhân hay vị trí riêng tư của du khách.
- **Business Rules Liên Quan:** `BR-METRIC-01`, `BR-AGG-01`, `BR-AUTH-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **S05.B1** | Bấm vào "Bảng Điều Khiển" trên menu chính | Gọi `GET /api/v1/analytics/dashboard` | BR-AUTH-01 |
| **S05.B2** | — | Backend truy vấn `analytics_daily_metrics` và `analytics_poi_daily_metrics` | BR-AGG-01 |
| **S05.B3** | — | Tính toán an toàn: `avg_duration_sec = (listened_ms / 1000) / listens_count` nếu `listens_count > 0` ngược lại bằng 0 | BR-METRIC-01 |
| **S05.B4** | Xem các thẻ chỉ số và biểu đồ | Hiển thị: Tổng lượt nghe, Thời gian nghe trung bình, Tổng POI hoạt động và Top 5 địa điểm nổi bật | — |

---

## 4. Alternative Paths

- Không có nhánh thay thế.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **S05.E1 — Dữ liệu kỳ chưa có lượt nghe nào**:
  - **Điểm phát sinh:** Tại bước `S05.B3` khi database mới khởi tạo hoặc chưa có du khách.
  - **Phản hồi:** Trả về `0` cho mọi chỉ số, giao diện hiển thị trạng thái Empty State đẹp mắt, không hiển thị lỗi.

---

## 6. Extension Points

- Không có extension point riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD12 (Worker tổng hợp thống kê), SD13 (Xem thống kê), AD12, AD13.
- **Màn hình UI:** `apps/web-admin/src/pages/Dashboard.tsx`.
- **API Endpoint:** `GET /api/v1/analytics/dashboard`.
- **Service & Repository:** `app/services/analytics_service.py`, `app/repositories/analytics_repo.py`, Collection: `analytics_daily_metrics`, `analytics_poi_daily_metrics`.
- **Bằng chứng kiểm thử:** `backend/tests/test_analytics.py::test_analytics_dashboard` (Passed).
