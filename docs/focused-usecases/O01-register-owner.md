# O01 — Đăng Ký Làm Chủ Quán

## 1. Thông Tin Nhận Diện

- **Use Case ID:** O01
- **Use Case Name:** Đăng ký làm chủ quán
- **Module / System Boundary:** Phân hệ Cổng Thông Tin Chủ Quán & Backend API
- **Primary Actor:** Người dùng / Chủ quán mới (Owner Candidate)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_auth_rbac.py::test_owner_registration_flow`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Chủ quán mới truy cập form đăng ký, nhập email, mật khẩu, họ tên và tên cơ sở kinh doanh tại Quận 4. Hệ thống tạo tài khoản chủ quán ở trạng thái chờ xác minh (`pending`) và gửi hồ sơ vào hàng đợi xét duyệt của Admin.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Người dùng bấm vào liên kết "Đăng ký tài khoản chủ quán mới" trên trang đăng nhập Web Admin.
- **Preconditions:** Email đăng ký chưa tồn tại trong hệ thống.
- **Assumptions:** Người dùng có cơ sở kinh doanh thực tế trên địa bàn Quận 4.
- **Success Postconditions:** Tạo mới bản ghi trong `admin_users` với role `poi_owner`, `is_poi_owner_verified=False`; tạo bản ghi hồ sơ trong `poi_owner_registrations` với `status='pending'`.
- **Minimum Guarantees:** Đăng ký trùng email lập tức bị từ chối; không tự động cấp quyền sở hữu và công bố POI trước khi được duyệt (`BR-OWNER-01`).
- **Business Rules Liên Quan:** `BR-AUTH-01`, `BR-OWNER-01`, `BR-IDEM-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **O01.B1** | Bấm "Đăng ký chủ quán mới" | Hiển thị form: Email, Mật khẩu, Họ tên, Tên quán / Cơ sở kinh doanh | — |
| **O01.B2** | Nhập đầy đủ thông tin | Form kiểm tra định dạng email và độ mạnh mật khẩu | E1 |
| **O01.B3** | Bấm nút "Gửi Hồ Sơ Đăng Ký" | Gửi `POST /api/v1/admin/auth/register-owner` | BR-IDEM-01 |
| **O01.B4** | — | Backend chuẩn hóa email, kiểm tra trùng lặp email | E2 |
| **O01.B5** | — | Băm mật khẩu, tạo user với role `poi_owner`, tạo hồ sơ trong `poi_owner_registrations` | BR-AUTH-01 |
| **O01.B6** | Nhận kết quả phản hồi | Hiển thị thông báo "Đăng ký thành công! Hồ sơ của bạn đang chờ quản trị viên phê duyệt" | — |

---

## 4. Alternative Paths

- Không có nhánh thay thế.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **O01.E1 — Dữ liệu form không hợp lệ**:
  - **Điểm phát sinh:** Tại bước `O01.B2` khi email không đúng cú pháp hoặc mật khẩu ngắn hơn 6 ký tự.
  - **Phản hồi:** Hiển thị lỗi ngay dưới trường nhập liệu.
- **O01.E2 — Email đã được đăng ký trước đó**:
  - **Điểm phát sinh:** Tại bước `O01.B4` khi email đã tồn tại trong `admin_users`.
  - **Phản hồi:** Trả mã lỗi HTTP 400: "Email already registered".

---

## 6. Extension Points

- Không có extension point được mô hình hóa riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD08, AD08.
- **Màn hình UI:** `apps/web-admin/src/pages/Login.tsx` (Tab Đăng Ký).
- **API Endpoint:** `POST /api/v1/admin/auth/register-owner`.
- **Service & Repository:** `app/services/auth_service.py`, `app/repositories/auth_repo.py`, Collection: `admin_users`, `poi_owner_registrations`.
- **Bằng chứng kiểm thử:** `backend/tests/test_auth_rbac.py::test_owner_registration_flow` (Passed).
