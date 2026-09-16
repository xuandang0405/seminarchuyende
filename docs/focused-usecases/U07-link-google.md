# U07 — Liên Kết Tài Khoản Google

## 1. Thông Tin Nhận Diện
- **Use Case ID:** U07
- **Use Case Name:** Liên kết tài khoản Google (Account Linking)
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Người dùng đã đăng nhập hệ thống
- **Supporting Actors:** Google Identity Provider (OAuth 2.0 / OIDC)
- **Maturity:** Focused
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng chủ động liên kết tài khoản Google của mình từ màn hình Cài đặt bảo mật. Hệ thống khởi tạo giao dịch liên kết có ràng buộc `purpose=link` và `user_id`, sau khi Google xác nhận danh tính thì lưu bản ghi vào `auth_identities`.

---

## 2. Điều Kiện & Quy Tắc
- **Trigger:** Người dùng bấm "Liên Kết Ngay" trong mục Định Danh Google tại `/account/security`.
- **Preconditions:** Người dùng đang đăng nhập với phiên làm việc hợp lệ; tài khoản hiện tại chưa từng liên kết Google.
- **Success Postconditions:** Tạo bản ghi trong `auth_identities` gắn kết `user_id` với `(provider='google', issuer='accounts.google.com', subject=sub)`; từ thời điểm này người dùng có thể đăng nhập bằng nút Google.
- **Minimum Guarantees:**
  - Một tài khoản TourVoice chỉ được liên kết với 1 Google identity.
  - Một tài khoản Google identity chỉ được thuộc về 1 tài khoản TourVoice (nếu Google sub này đã thuộc người khác -> từ chối liên kết).
  - Không cho phép dùng callback đăng nhập thông thường để giả mạo liên kết tài khoản.

---

## 3. Basic Course of Events

| Step ID | Actor Action | System Response |
|---|---|---|
| **U07.B1** | Bấm "Liên Kết Ngay" | Client gửi `POST /api/v1/auth/google/link/start` kèm Bearer token |
| **U07.B2** | — | Backend kiểm tra tài khoản chưa có link, sinh OAuth transaction với `purpose='link'`, `user_id=user_id` |
| **U07.B3** | Xác thực trên Google | Google chuyển hướng về callback backend |
| **U07.B4** | — | Backend consume transaction, verify ID token, kiểm tra identity chưa thuộc ai, lưu vào `auth_identities` |
| **U07.B5** | — | Backend chuyển hướng về `/auth/callback?linked=true&return_to=/account/security` |
| **U07.B6** | Xem trạng thái cập nhật | Màn hình hiển thị badge "Đã liên kết" màu xanh |

---

## 4. Exception Paths
- **U07.E1 — Tài khoản Google đã thuộc người khác**: Trả về lỗi "Tài khoản Google này đã được liên kết với một tài khoản khác."
- **U07.E2 — Tài khoản hiện tại đã có liên kết Google**: Từ chối với thông báo "Tài khoản của bạn đã được liên kết với Google rồi."

---

## 5. Truy Vết Triển Khai
- **Sơ đồ liên quan:** 06_xac_thuc_va_bao_mat.puml.
- **Màn hình UI:** `apps/web-admin/src/pages/AccountSecurity.tsx`.
- **API Endpoint:** `POST /api/v1/auth/google/link/start`, `GET /api/v1/auth/google/callback`.
- **Collection:** `oauth_transactions`, `auth_identities`.
