# C06 — Duyệt Đăng Ký Chủ Quán

## 1. Thông Tin Nhận Diện

- **Use Case ID:** C06
- **Use Case Name:** Duyệt đăng ký chủ quán
- **Module / System Boundary:** Phân hệ Web Quản trị (Web Admin) & Backend API
- **Primary Actor:** Quản trị viên (Admin / Super Admin có quyền `user:approve` hoặc `content:moderate`)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_auth_rbac.py::test_owner_registration_flow`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Quản trị viên xem xét hồ sơ đăng ký kinh doanh quán ăn do người dùng gửi lên. Admin phê duyệt hồ sơ, hệ thống tự động thăng hạng quyền tài khoản thành chủ quán chính thức (`is_poi_owner_verified=True`) và gửi thông báo xác nhận.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Admin mở tab "Hồ sơ đăng ký chủ quán" trong mục Kiểm duyệt và chọn hồ sơ đang `pending`.
- **Preconditions:** Admin đã đăng nhập với quyền hợp lệ.
- **Assumptions:** Hồ sơ đăng ký đã có trong collection `poi_owner_registrations`.
- **Success Postconditions:** Hồ sơ chuyển trạng thái `status='approved'`; tài khoản chủ quán được cập nhật `is_poi_owner_verified=True`; thông báo xác nhận được lưu vào `owner_notifications`.
- **Minimum Guarantees:** Từ chối duyệt không làm mất tài khoản gốc của người dùng; hai admin duyệt cùng lúc không gây xung đột (quy tắc `BR-REVIEW-01`).
- **Business Rules Liên Quan:** `BR-AUTH-01`, `BR-OWNER-01`, `BR-REVIEW-01`, `BR-VERSION-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **C06.B1** | Mở danh sách hồ sơ đăng ký | Gọi `GET /api/v1/admin/moderation/registrations`, hiển thị các hồ sơ `pending` | BR-AUTH-01 |
| **C06.B2** | Chọn xem một hồ sơ chủ quán | Xem tên cơ sở kinh doanh, email, họ tên, ngày đăng ký | — |
| **C06.B3** | Chọn "Phê Duyệt", nhập ghi chú | Form hiển thị xác nhận | A1 |
| **C06.B4** | Bấm "Xác Nhận" | Gửi `POST /api/v1/admin/moderation/registrations/{id}` với `decision='approved'` | BR-REVIEW-01, E1 |
| **C06.B5** | — | Backend cập nhật atomic: `poi_owner_registrations.status='approved'`, `admin_users.is_poi_owner_verified=True`, tạo `owner_notifications` | BR-OWNER-01 |
| **C06.B6** | Xem kết quả | Hồ sơ được đánh dấu đã duyệt, hiển thị thông báo thành công | — |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **C06.A1 — Từ chối đăng ký chủ quán**:
  - **Điểm rẽ:** Tại bước `C06.B3`, Admin chọn "Từ Chối" và nhập lý do (ví dụ: thông tin quán không xác thực).
  - **Hành vi:** Backend cập nhật `status='rejected'`, tài khoản người dùng vẫn giữ nguyên `is_poi_owner_verified=False` và nhận được thông báo giải thích lý do.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **C06.E1 — Xung đột phiên bản kiểm duyệt**:
  - **Điểm phát sinh:** Tại bước `C06.B4` khi hồ sơ đã được duyệt hoặc từ chối trước đó bởi một admin khác.
  - **Phản hồi:** Trả HTTP 400 "Registration already reviewed", làm mới giao diện.

---

## 6. Extension Points

- Không có extension point được mô hình hóa riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD10, AD10.
- **Màn hình UI:** `apps/web-admin/src/pages/Moderation.tsx`.
- **API Endpoint:** `POST /api/v1/admin/moderation/registrations/{id}`.
- **Service & Repository:** `app/services/moderation_service.py`, Collection: `poi_owner_registrations`, `admin_users`, `owner_notifications`.
- **Bằng chứng kiểm thử:** `backend/tests/test_auth_rbac.py::test_owner_registration_flow` (Passed).
