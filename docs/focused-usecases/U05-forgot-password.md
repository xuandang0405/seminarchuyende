# U05 — Yêu Cầu Khôi Phục Mật Khẩu

## 1. Thông Tin Nhận Diện
- **Use Case ID:** U05
- **Use Case Name:** Yêu cầu khôi phục mật khẩu (Forgot Password)
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Người dùng quên mật khẩu
- **Maturity:** Focused
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng gửi địa chỉ email để yêu cầu khôi phục mật khẩu. Hệ thống luôn phản hồi một thông điệp chung (generic message) để chống user enumeration, và tạo token hành động 1 lần (one-time action token) trong `auth_action_tokens` nếu tài khoản có hỗ trợ mật khẩu.

---

## 2. Điều Kiện & Quy Tắc
- **Trigger:** Người dùng bấm "Quên mật khẩu?" tại `/login` và gửi biểu mẫu tại `/forgot-password`.
- **Preconditions:** Không yêu cầu đăng nhập.
- **Success Postconditions:** Luôn nhận phản hồi thành công chung chung; nếu tài khoản hợp lệ có password, một token ngẫu nhiên được băm và lưu vào `auth_action_tokens` với hạn dùng 15 phút.
- **Minimum Guarantees:** Không tiết lộ tài khoản có tồn tại hay không; tài khoản Google-only không bao giờ sinh token khôi phục mật khẩu; token luôn được lưu dạng hash SHA-256.

---

## 3. Basic Course of Events

| Step ID | Actor Action | System Response |
|---|---|---|
| **U05.B1** | Nhập email và bấm gửi | Client gửi `POST /api/v1/auth/forgot-password` với `{ email }` |
| **U05.B2** | — | Backend kiểm tra sự tồn tại của user và trường `password_hash` |
| **U05.B3** | — | Nếu đủ điều kiện, backend sinh raw token, băm SHA-256, lưu vào `auth_action_tokens` (TTL 15 phút) |
| **U05.B4** | Xem thông báo | Luôn nhận phản hồi: "Nếu email này tồn tại trong hệ thống và có mật khẩu, hướng dẫn đặt lại mật khẩu đã được xử lý." |

---

## 4. Truy Vết Triển Khai
- **Sơ đồ liên quan:** 06_xac_thuc_va_bao_mat.puml.
- **Màn hình UI:** `apps/web-admin/src/pages/ForgotPassword.tsx`.
- **API Endpoint:** `POST /api/v1/auth/forgot-password`.
- **Collection:** `auth_action_tokens`, `admin_users`.
