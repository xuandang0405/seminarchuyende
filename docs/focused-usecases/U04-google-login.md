# U04 — Đăng Nhập Bằng Google OpenID Connect

## 1. Thông Tin Nhận Diện
- **Use Case ID:** U04
- **Use Case Name:** Đăng nhập bằng Google OpenID Connect
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Khách truy cập hoặc người dùng hệ thống
- **Supporting Actors:** Google Identity Provider (OAuth 2.0 / OIDC)
- **Maturity:** Focused
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng chọn xác thực nhanh qua tài khoản Google. Hệ thống thực hiện Authorization Code flow kèm PKCE S256 và browser binding, xác minh chữ ký Google ID token bằng bộ khóa công khai RS256 JWKS, resolve định danh `(provider, issuer, subject)`, cấp phiên làm việc qua HttpOnly cookie và chuyển hướng về trang web nội bộ an toàn.

---

## 2. Điều Kiện & Quy Tắc
- **Trigger:** Người dùng bấm "Đăng nhập bằng Google" tại `/login`.
- **Preconditions:** Google OAuth Client ID & Secret đã được cấu hình trong `settings`.
- **Success Postconditions:** Nhận diện hoặc tạo mới tài khoản `admin_users` với vai trò `user`, lưu định danh vào `auth_identities`, phát phiên `auth_sessions`, đặt HttpOnly refresh cookie và chuyển về URL đích an toàn (returnTo).
- **Minimum Guarantees:**
  - **STRICT ANTI AUTO-MERGE**: Nếu email Google trùng với tài khoản cục bộ hiện có nhưng chưa từng liên kết Google, backend tuyệt đối từ chối tự động ghép và yêu cầu đăng nhập mật khẩu trước.
  - **STRICT NON-PROMOTION**: Tài khoản Google mới luôn nhận vai trò `user`, không tự động trở thành admin hay chủ quán đã duyệt (`is_poi_owner_verified=False`).
  - **SECURE TOKENS**: Token ứng dụng không bao giờ truyền qua URL/Query String.

---

## 3. Basic Course of Events

| Step ID | Actor Action | System Response |
|---|---|---|
| **U04.B1** | Bấm "Đăng nhập bằng Google" | Frontend gọi `GET /api/v1/auth/google/start?return_to=...` |
| **U04.B2** | — | Backend sinh state, nonce, PKCE pair, browser binding, lưu vào `oauth_transactions` và trả auth URL |
| **U04.B3** | Chuyển sang Google và đồng ý cấp quyền | Google chuyển hướng về backend callback `GET /api/v1/auth/google/callback` |
| **U04.B4** | — | Backend consume transaction, đổi code lấy tokens với Google, xác minh RS256 JWKS và claims |
| **U04.B5** | — | Backend tìm `auth_identities` hoặc tạo mới user (role: 'user'), tạo `auth_sessions` và đặt HttpOnly cookie |
| **U04.B6** | — | Backend redirect về `/auth/callback?return_to=...` sạch sẽ |
| **U04.B7** | Xem trang ứng dụng | Web client gọi `/api/v1/auth/csrf` -> `/api/v1/auth/refresh` -> nạp access token vào RAM -> mở trang đích |

---

## 4. Exception Paths
- **U04.E1 — Email trùng tài khoản cũ chưa liên kết**: Backend trả 302 redirect về lỗi "Tài khoản đã tồn tại với email này. Vui lòng đăng nhập bằng mật khẩu rồi liên kết Google trong mục Cài đặt Bảo mật."
- **U04.E2 — Sai lệch trình duyệt hoặc state hết hạn**: Từ chối callback, hiển thị thông báo lỗi an toàn.
- **U04.E3 — ID token không hợp lệ hoặc email chưa xác minh**: Từ chối xác thực.

---

## 5. Truy Vết Triển Khai
- **Sơ đồ liên quan:** SD-AUTH-GOOGLE, AD-AUTH-GOOGLE, 06_xac_thuc_va_bao_mat.puml.
- **Màn hình UI:** `apps/web-admin/src/pages/Login.tsx`, `apps/web-admin/src/pages/AuthCallback.tsx`.
- **API Endpoint:** `GET /api/v1/auth/google/start`, `GET /api/v1/auth/google/callback`.
- **Collection:** `oauth_transactions`, `auth_identities`, `admin_users`, `auth_sessions`.
