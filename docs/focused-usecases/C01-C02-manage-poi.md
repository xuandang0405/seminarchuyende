# C01 & C02 — Quản Lý Địa Điểm (Thêm, Sửa & Bật/Tắt Công Bố POI)

## 1. Thông Tin Nhận Diện

- **Use Case ID:** C01, C02, C04
- **Use Case Name:** Thêm mới, chỉnh sửa và bật/tắt công bố địa điểm du lịch
- **Module / System Boundary:** Phân hệ Quản trị Nội dung (Web Admin) & Backend API
- **Primary Actor:** Quản trị viên (Admin / Super Admin có quyền `poi:create`, `poi:update`, `poi:toggle`)
- **Supporting Actors:** Dịch vụ bản đồ Cloud (MapLibre / Leaflet)
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_poi_full_slice.py::test_poi_creation_and_concurrency_control`, `test_publication_readiness_gate`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Quản trị viên tạo mới một điểm tham quan hoặc ẩm thực (POI), cập nhật tọa độ GeoJSON, bán kính trigger, độ ưu tiên âm thanh, và yêu cầu công bố ra ứng dụng mobile khi đã vượt qua cổng kiểm tra Readiness Gate.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Admin bấm "Thêm POI Mới" hoặc chọn biểu tượng chỉnh sửa trên danh sách POI.
- **Preconditions:** Admin đã xác thực với token hợp lệ.
- **Assumptions:** Tọa độ địa lý nằm trong khu vực địa bàn Quận 4, TP.HCM.
- **Success Postconditions:** POI được lưu vào collection `POI`; tăng `content_version` nếu sửa đổi văn bản thuyết minh; nếu bật công bố (`is_active=True`), POI xuất hiện ngay trên API công khai cho mobile.
- **Minimum Guarantees:** Không bao giờ công bố POI ra ứng dụng nếu chưa có bản dịch tiếng Anh và audio hợp lệ (Readiness Gate); sửa tọa độ không làm mất hoặc bắt tạo lại file âm thanh nếu nội dung không đổi.
- **Business Rules Liên Quan:** `BR-POI-01`, `BR-VERSION-01`, `BR-IDEM-01`, `BR-AUTH-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **C01.B1** | Bấm nút "Thêm Địa Điểm Mới" | Hiển thị form nhập liệu: Tên, mô tả, địa chỉ, danh mục, bán kính trigger, tọa độ bản đồ | — |
| **C01.B2** | Nhập thông tin và chọn tọa độ | Form validate dữ liệu, định dạng Point `[longitude, latitude]` | E1 |
| **C01.B3** | Bấm "Lưu Địa Điểm" | Gửi `POST /api/v1/admin/pois` kèm `Idempotency-Key` | BR-IDEM-01, E2 |
| **C01.B4** | — | Backend lưu bản ghi vào collection `POI` với `version=1`, `is_active=False` (bản nháp ban đầu) | BR-POI-01 |
| **C01.B5** | Yêu cầu công bố địa điểm | Bấm chuyển công tắc "Công bố công khai", gửi `POST /api/v1/admin/pois/{id}/toggle-active` | A1, E3 |
| **C01.B6** | — | Backend chạy kiểm tra **Readiness Gate**: xác nhận tồn tại bản dịch tiếng Anh và audio; chuyển `is_active=True` | BR-POI-01 |
| **C01.B7** | Xem danh sách cập nhật | POI hiển thị huy hiệu xanh "Công bố", sẵn sàng phục vụ du khách trên mobile | — |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **C01.A1 — Chưa đủ điều kiện công bố (Readiness Gate Pending)**:
  - **Điểm rẽ:** Tại bước `C01.B6` khi POI chưa có file thuyết minh tiếng Anh hoặc chưa hoàn tất TTS.
  - **Hành vi:** Backend đánh dấu `activation_requested=True` nhưng giữ `is_active=False`. Trả về danh sách lý do: `['Missing English localization or audio']`. Web hiển thị trạng thái "Đang chuẩn bị thuyết minh", không hiển thị công bố giả.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **C01.E1 — Tọa độ ngoài phạm vi hợp lệ**:
  - **Điểm phát sinh:** Tại bước `C01.B2` khi kinh độ/vĩ độ vượt quá giới hạn địa lý [-180, 180], [-90, 90].
  - **Phản hồi:** Form báo lỗi "Tọa độ không hợp lệ".
- **C01.E2 — Xung đột phiên bản khi chỉnh sửa (C02)**:
  - **Điểm phát sinh:** Tại bước `C01.B3` khi sửa POI mà `expected_version` không khớp với version hiện tại trong database.
  - **Phản hồi:** Backend trả HTTP 409 Conflict: "POI has been modified by another admin", yêu cầu tải lại dữ liệu mới nhất.
- **C01.E3 — Thao tác bật tắt công bố bị lỗi mạng**:
  - **Điểm phát sinh:** Tại bước `C01.B5` khi mất kết nối.
  - **Phản hồi:** Hiển thị toast thông báo lỗi, trạng thái công tắc tự động hoàn tác về trạng thái cũ.

---

## 6. Extension Points

- `C14 Dùng AI gợi ý mô tả` có thể extend tại bước `C01.B2` khi admin bấm "AI Gợi ý mô tả".

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD03 (Lưu POI), AD03 (Activity lưu POI).
- **Màn hình UI:** `apps/web-admin/src/pages/POIList.tsx`.
- **API Endpoints:**
  - `POST /api/v1/admin/pois`
  - `PATCH /api/v1/admin/pois/{id}`
  - `POST /api/v1/admin/pois/{id}/toggle-active`
- **Service & Repository:** `app/services/poi_admin_service.py`, `app/repositories/poi_repo.py`, Collection: `POI`, `poi_localizations`.
- **Bằng chứng kiểm thử:**
  - `backend/tests/test_poi_full_slice.py::test_poi_creation_and_concurrency_control` (Passed).
  - `backend/tests/test_poi_full_slice.py::test_publication_readiness_gate` (Passed).
