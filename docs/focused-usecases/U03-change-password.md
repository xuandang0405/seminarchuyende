# U03 — Đổi Mật Khẩu

## 1. Thông Tin Nhận Diện
- **Use Case ID:** U03
- **Use Case Name:** Đổi mật khẩu
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Người dùng đã đăng nhập có tài khoản mật khẩu
- **Maturity:** Focused
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng nhập mật khẩu hiện tại và mật khẩu mới để thay đổi thông tin xác thực. Hệ thống cập nhật băm mật khẩu mới, tăng `auth_version` và thu hồi toàn bộ các phiên cũ để bắt buộc đăng nhập lại.

---

## 2. Điều Kiện & Quy Tắc
- **Trigger:** Người dùng nhập form đổi mật khẩu tại `/account/security` và bấm "Cập Nhật Mật Khẩu".
- **Preconditions:** Người dùng đã đăng nhập hợp lệ và tài khoản có `password_hash` (không áp dụng cho Google-only account chưa đặt pass).
- **Success Postconditions:** `password_hash` được cập nhật trong `admin_users`, `auth_version` tăng thêm 1, tất cả phiên trong `auth_sessions` bị thu hồi, người dùng được chuyển về `/login` để đăng nhập lại.
- **Minimum Guarantees:** Mật khẩu mới tối thiểu 6 ký tự; mật khẩu cũ phải chính xác; tài khoản Google-only bị từ chối với thông báo hướng dẫn rõ ràng.

---

## 3. Basic Course of Events

| Step ID | Actor Action | System Response |
|---|---|---|
| **U03.B1** | Nhập mật khẩu hiện tại, mật khẩu mới và xác nhận | Form kiểm tra độ dài và sự trùng khớp |
| **U03.B2** | Bấm nút xác nhận | Client gửi `POST /api/v1/auth/change-password` kèm Bearer token |
| **U03.B3** | — | Backend xác thực mật khẩu hiện tại với `user.password_hash` |
| **U03.B4** | — | Backend băm mật khẩu mới (bcrypt), lưu vào `admin_users` |
| **U03.B5** | — | Backend tăng `auth_version`, thu hồi toàn bộ phiên trong `auth_sessions` |
| **U03.B6** | Xem thông báo thành công | Client thông báo thành công và điều hướng sang `/login` |

---

## 4. Exception Paths
- **U03.E1 — Mật khẩu hiện tại không chính xác**: Backend trả 400 "Mật khẩu hiện tại không chính xác".
- **U03.E2 — Tài khoản đăng ký qua Google**: Backend trả 400 thông báo tài khoản chưa thiết lập mật khẩu nội bộ.
- **U03.E3 — Mật khẩu mới quá ngắn**: Client/Backend từ chối nếu < 6 ký tự.

---

## 5. Truy Vết Triển Khai
- **Sơ đồ liên quan:** 06_xac_thuc_va_bao_mat.puml.
- **Màn hình UI:** `apps/web-admin/src/pages/AccountSecurity.tsx`.
- **API Endpoint:** `POST /api/v1/auth/change-password`.
- **Collection:** `admin_users`, `auth_sessions`.
