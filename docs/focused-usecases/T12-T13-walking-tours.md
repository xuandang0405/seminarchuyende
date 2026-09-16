# T12 & T13 — Xem, Chọn & Tham Gia Tuyến Tour Đi Bộ

## 1. Thông Tin Nhận Diện

- **Use Case ID:** T12 (Xem và chọn tour), T13 (Bắt đầu hoặc kết thúc tour)
- **Use Case Name:** Xem, chọn và tham gia tuyến tour đi bộ
- **Module / System Boundary:** Phân hệ Tour Ứng dụng Di động & Backend API
- **Primary Actor:** Khách du lịch (Tourist)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_api.py::test_tours_listing`, `TourSessionService.js`, `TourModal.js`)
- **Scope:** [G]; user-goal
- **Summary / Goal:** Du khách xem danh sách các tuyến tour đi bộ khám phá di tích lịch sử và ẩm thực đêm Quận 4, chọn một tuyến để hiển thị đường chỉ dẫn (Polyline) trên bản đồ và bắt đầu chuyến đi. Hệ thống theo dõi thứ tự các điểm dừng cục bộ và cho phép kết thúc tour bất cứ lúc nào.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Du khách bấm nút "Tour" trên bản đồ mobile để mở danh sách tuyến tham quan.
- **Preconditions:** Dữ liệu tour đã được tạo trong collection `tours`.
- **Assumptions:** Không yêu cầu đăng nhập.
- **Success Postconditions:** Tuyến tour được kích hoạt; đường nối các điểm dừng hiển thị trên bản đồ; trạng thái tiến trình lưu trong `TourSessionService`.
- **Minimum Guarantees:** Khách từ chối consent thống kê vẫn tham gia tour bình thường (`BR-CONSENT-01`, `BR-TOUR-01`).
- **Business Rules Liên Quan:** `BR-TOUR-01`, `BR-CONSENT-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **T12.B1** | Bấm nút "Tour" trên bản đồ | Mở `TourModal`, gọi `GET /api/v1/tours` hiển thị danh sách các tuyến | — |
| **T12.B2** | Xem thông tin chi tiết tuyến | Xem tên tour, mô tả và số lượng điểm dừng (ví dụ: 5 điểm dừng) | — |
| **T12.B3** | Bấm "Bắt Đầu Tuyến Này" (T13) | `TourSessionService` khởi tạo phiên tour cục bộ, đóng modal | BR-TOUR-01 |
| **T12.B4** | — | Bản đồ hiển thị đường dẫn Polyline màu cam nối các điểm dừng theo thứ tự | — |
| **T12.B5** | Di chuyển tham quan qua các điểm | Khi đến gần từng điểm, GPS tự động kích hoạt bài thuyết minh tương ứng | T09, BR-GEO-01 |
| **T12.B6** | Bấm "Kết Thúc Tuyến Đang Đi" (T13) | Xóa phiên tour đang hoạt động, xóa đường dẫn trên bản đồ | A1 |

---

## 4. Alternative Paths

- **T12.A1 — Chuyển sang tour khác**:
  - **Điểm rẽ:** Tại bước `T12.B3` khi đang có tour khác hoạt động.
  - **Hành vi:** Kết thúc tour cũ và chuyển ngay sang lộ trình của tour mới.

---

## 5. Exception Paths

- Không có lỗi gây chặn trải nghiệm.

---

## 6. Extension Points

- Không có extension point riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD14 (Tham gia tour), AD14 (Activity tour).
- **Màn hình UI:** `mobile/src/components/TourModal.js`, `mobile/src/screens/MapScreen.js`.
- **API Endpoint:** `GET /api/v1/tours`, `GET /api/v1/tours/{id}`.
- **Service & Repository:** `app/services/tour_service.py`, `app/repositories/tour_repo.py`, Collection: `tours`.
- **Bằng chứng kiểm thử:** `backend/tests/test_api.py::test_tours_listing` (Passed).
