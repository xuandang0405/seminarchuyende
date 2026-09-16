# U01 — Đăng Nhập Cổng Quản Trị Hoặc Chủ Quán

## 1. Thông Tin Nhận Diện

- **Use Case ID:** U01
- **Use Case Name:** Đăng nhập cổng quản trị hoặc chủ quán
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Người dùng quản trị (Admin / Super Admin) hoặc Chủ quán (POI Owner)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_auth_rbac.py::test_login_success`, `test_login_invalid_password`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng nhập email và mật khẩu để xác thực danh tính. Hệ thống xác minh mật khẩu bằng thuật toán băm an toàn, nạp danh sách quyền và tạo phiên làm việc mới kèm Access Token và Refresh Token Rotation.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Người dùng truy cập đường dẫn `/login` và bấm nút "Đăng nhập".
- **Preconditions:** Tài khoản đã được tạo trong cơ sở dữ liệu `admin_users`.
- **Assumptions:** Kết nối mạng ổn định giữa client và backend.
- **Success Postconditions:** Nhận JWT Access Token ngắn hạn và Refresh Token phiên; lưu phiên vào collection `auth_sessions`; giao diện chuyển hướng đúng màn hình theo vai trò (`/` cho Admin, `/owner` cho Chủ quán).
- **Minimum Guarantees:** Không bao giờ lưu trữ hoặc ghi log mật khẩu dạng plain text; thông báo lỗi đăng nhập chung chung "Email hoặc mật khẩu không chính xác" để tránh kỹ thuật user enumeration; tài khoản bị khóa (`is_active=False`) bị từ chối đăng nhập.
- **Business Rules Liên Quan:** `BR-AUTH-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **U01.B1** | Nhập email và mật khẩu | Form kiểm tra định dạng email và độ dài mật khẩu phía client | E1 |
| **U01.B2** | Bấm nút "Đăng Nhập" | Gửi `POST /api/v1/admin/auth/login` với `{ email, password }` | BR-AUTH-01 |
| **U01.B3** | — | Backend chuẩn hóa email về chữ thường, tra cứu `admin_users`, kiểm tra `is_active=True` | E2, E3 |
| **U01.B4** | — | Xác thực mật khẩu qua `verify_password(password, user.password_hash)` | E4 |
| **U01.B5** | — | Nạp vai trò từ `roles`, sinh JWT Access Token và Refresh Token mới, lưu vào `auth_sessions` | BR-AUTH-01 |
| **U01.B6** | Xem giao diện chuyển hướng | Nhận thông tin hồ sơ và token, lưu vào bộ nhớ, chuyển hướng vào Dashboard quản trị | A1 |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **U01.A1 — Chủ quán chưa được xác minh (Pending Verification)**:
  - **Điểm rẽ:** Tại bước `U01.B6` khi tài khoản có role `poi_owner` nhưng `is_poi_owner_verified=False`.
  - **Hành vi:** Đăng nhập vẫn thành công nhưng giao diện hiển thị banner thông báo "Hồ sơ chủ quán của bạn đang được Admin xét duyệt", các tính năng quản lý POI bị giới hạn chỉ ở chế độ xem.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **U01.E1 — Dữ liệu form không hợp lệ**:
  - **Điểm phát sinh:** Tại bước `U01.B1` khi email sai định dạng hoặc bỏ trống.
  - **Phản hồi:** Hiển thị cảnh báo lỗi tại trường nhập liệu, không gửi request lên máy chủ.
- **U01.E2 — Email không tồn tại trong hệ thống**:
  - **Điểm phát sinh:** Tại bước `U01.B3` khi không tìm thấy user.
  - **Phản hồi:** Trả mã lỗi HTTP 401 với thông báo an toàn: "Email hoặc mật khẩu không chính xác".
- **U01.E3 — Tài khoản đã bị vô hiệu hóa**:
  - **Điểm phát sinh:** Tại bước `U01.B3` khi tài khoản có `is_active=False`.
  - **Phản hồi:** Trả mã lỗi HTTP 403: "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên".
- **U01.E4 — Mật khẩu không trùng khớp**:
  - **Điểm phát sinh:** Tại bước `U01.B4` khi hàm băm không khớp.
  - **Phản hồi:** Trả mã lỗi HTTP 401: "Email hoặc mật khẩu không chính xác".

---

## 6. Extension Points

- Không có extension point được mô hình hóa riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD02 (Đăng nhập), AD02 (Activity đăng nhập).
- **Màn hình UI:** `apps/web-admin/src/pages/Login.tsx`.
- **API Endpoint:** `POST /api/v1/admin/auth/login`.
- **Service & Repository:** `app/services/auth_service.py`, `app/repositories/auth_repo.py`, Collection: `admin_users`, `roles`, `auth_sessions`.
- **Bằng chứng kiểm thử:**
  - `backend/tests/test_auth_rbac.py::test_login_success` (Passed).
  - `backend/tests/test_auth_rbac.py::test_login_invalid_password` (Passed).
