# U06 — Đặt Lại Mật Khẩu Qua Token

## 1. Thông Tin Nhận Diện
- **Use Case ID:** U06
- **Use Case Name:** Đặt lại mật khẩu qua token (Reset Password)
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Người dùng sở hữu liên kết khôi phục mật khẩu
- **Maturity:** Focused
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng sử dụng token hành động nhận được để thiết lập mật khẩu mới. Hệ thống tiêu thụ token một cách nguyên tử (atomic single-use consumption), cập nhật băm mật khẩu mới, tăng `auth_version` và vô hiệu hóa tất cả các phiên hiện có.

---

## 2. Điều Kiện & Quy Tắc
- **Trigger:** Người dùng truy cập đường dẫn `/reset-password?token=...` và gửi mật khẩu mới.
- **Preconditions:** Token còn hạn (dưới 15 phút), chưa bị tiêu thụ (`consumed_at is None`) và mục đích là `password_reset`.
- **Success Postconditions:** Mật khẩu mới được băm và lưu vào `admin_users`, token chuyển sang trạng thái đã dùng (`consumed_at = now`), `auth_version` tăng thêm 1, toàn bộ phiên đăng nhập cũ bị hủy.
- **Minimum Guarantees:** Token chỉ sử dụng được duy nhất một lần; giải quyết race condition bằng thao tác nguyên tử `find_one_and_update`; không thể tái sử dụng token đã hết hạn hoặc đã tiêu thụ.

---

## 3. Basic Course of Events

| Step ID | Actor Action | System Response |
|---|---|---|
| **U06.B1** | Nhập mật khẩu mới và xác nhận | Form kiểm tra độ dài tối thiểu (>= 6) và sự trùng khớp |
| **U06.B2** | Bấm nút xác nhận | Client gửi `POST /api/v1/auth/reset-password` với `{ token, new_password }` |
| **U06.B3** | — | Backend tính `token_hash = sha256(token)` và tiêu thụ nguyên tử trong `auth_action_tokens` |
| **U06.B4** | — | Backend cập nhật `password_hash` mới, tăng `auth_version` và thu hồi toàn bộ session trong `auth_sessions` |
| **U06.B5** | Xem thông báo thành công | Client thông báo thành công và chuyển hướng về `/login` để đăng nhập lại |

---

## 4. Exception Paths
- **U06.E1 — Token không hợp lệ hoặc đã dùng**: Backend trả 400 "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn".
- **U06.E2 — Mật khẩu mới quá ngắn**: Trả 400 nếu < 6 ký tự.

---

## 5. Truy Vết Triển Khai
- **Sơ đồ liên quan:** 06_xac_thuc_va_bao_mat.puml.
- **Màn hình UI:** `apps/web-admin/src/pages/ResetPassword.tsx`.
- **API Endpoint:** `POST /api/v1/auth/reset-password`.
- **Collection:** `auth_action_tokens`, `admin_users`, `auth_sessions`.
