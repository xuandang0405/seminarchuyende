# Báo Cáo Hoàn Thành: Triển Khai Xác Thực Thật, Đăng Nhập Google & Bảo Vệ Truy Cập (UPDATE_PROMPT_LOGIN_GOOGLE_SECURITY)

Dự án đã triển khai đầy đủ và kiểm chứng toàn diện các yêu cầu kỹ thuật của tài liệu `UPDATE_PROMPT_LOGIN_GOOGLE_SECURITY.md` trên repository hiện tại theo kiến trúc 3 lớp (**Router → Service → Repository**), không dùng token giả, không bypass security.

---

## 1. Tóm Tắt Các Hạng Mục Đã Thực Hiện

### A. Cơ Sở Dữ Liệu & Migration Idempotent
1. **Bổ sung 3 Collection mở rộng**:
   - `auth_identities`: Lưu định danh Google/OIDC `(provider, issuer, subject, user_id, email_at_link)`.
   - `auth_action_tokens`: Lưu token đặt lại mật khẩu một lần (hash SHA-256, TTL 15 phút, consume nguyên tử).
   - `oauth_transactions`: Lưu trạng thái tạm thời của OAuth 2.0 (state, nonce, PKCE verifier, browser binding, returnTo, TTL 10 phút).
2. **Migration & Index Script**:
   - File migration: [`002_auth_google_security.py`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/backend/app/db/migrations/002_auth_google_security.py).
   - Cập nhật [`indexes.py`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/backend/app/db/indexes.py) đảm bảo unique index compound cho `(provider, issuer, subject)`, `(user_id, provider)`, index TTL cho transactions và action tokens.

### B. Backend Xác Thực & Bảo Mật Thực Tế (FastAPI)
1. **Đăng nhập Email / Mật khẩu**:
   - Xác thực mật khẩu với bcrypt hash, kiểm tra tài khoản hoạt động (`is_active`).
   - Xử lý tài khoản chỉ đăng nhập bằng Google (Google-only): từ chối đăng nhập bằng form mật khẩu và thông báo rõ: *"Tài khoản này được đăng ký qua Google. Vui lòng đăng nhập bằng nút Google."*
2. **Google OAuth 2.0 / OpenID Connect Flow**:
   - Service: [`google_auth_service.py`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/backend/app/services/google_auth_service.py).
   - **Authorization Code + PKCE S256**: Sinh code verifier/challenge chuẩn RFC 7636 và browser binding.
   - **Xác minh Claims & Chữ ký**: Xác minh ID Token qua RS256 JWKS công khai của Google, kiểm tra `issuer`, `audience`, `nonce`, hạn dùng và `email_verified`.
   - **Chính sách Anti Auto-merge (Nghiêm ngặt)**: Nếu email Google trùng với tài khoản cục bộ hiện có chưa liên kết, backend **tuyệt đối không tự động gộp**, trả về thông báo yêu cầu đăng nhập bằng mật khẩu rồi liên kết trong Cài đặt Bảo mật.
   - **Chính sách Non-Promotion**: Tài khoản Google mới luôn nhận vai trò mặc định `user`, không tự nâng lên admin, không tự động xác minh chủ quán (`is_poi_owner_verified=False`).
3. **Quản lý Phiên & Token**:
   - **Access Token**: JWT ngắn hạn (15 phút), nằm hoàn toàn trong bộ nhớ RAM của client.
   - **Refresh Token**: Nằm trong cookie `HttpOnly`, `SameSite=lax`, thời hạn 30 ngày.
   - **Rotation & Replay Detection**: Mỗi lần refresh sẽ sinh refresh token mới và cập nhật hash trong `auth_sessions`. Nếu phát hiện dùng lại token cũ (replay attack), toàn bộ token family sẽ bị thu hồi ngay lập tức.
   - **Thu hồi phiên (Revocation)**: Hỗ trợ đăng xuất từng phiên cụ thể hoặc `POST /api/v1/auth/logout-all` (thu hồi tất cả phiên và tăng `auth_version`).
4. **Khôi phục Mật Khẩu (Password Recovery)**:
   - Service: [`password_recovery_service.py`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/backend/app/services/password_recovery_service.py).
   - `POST /api/v1/auth/forgot-password`: Luôn trả thông điệp chung (Generic Response) để chống lộ tài khoản (User Enumeration). Tài khoản Google-only không bị cấp token mật khẩu.
   - `POST /api/v1/auth/reset-password`: Tiêu thụ token nguyên tử (`find_one_and_update`), chỉ sử dụng được duy nhất một lần.

### C. Giao Diện Web Admin (React + TypeScript + Tailwind)
1. **Auth Context Máy Trạng Thái**:
   - [`AuthContext.tsx`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/apps/web-admin/src/context/AuthContext.tsx): Quản lý 4 trạng thái (`loading`, `authenticated`, `anonymous`, `error`). Phân biệt lỗi mất mạng với lỗi 401; cơ chế Single-Flight tránh gọi refresh trùng lặp. Cung cấp hàm `fetchWithAuth` tự động retry 401.
2. **Bảo vệ Đường Dẫn**:
   - [`ProtectedRoute.tsx`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/apps/web-admin/src/components/ProtectedRoute.tsx): Không lóe nội dung khi đang kiểm tra phiên, kiểm soát vai trò (`allowedRoles`), quyền (`requiredPermission`) và trạng thái duyệt chủ quán (`requireOwnerVerified`).
3. **Các Trang Mới & Cải Tiến**:
   - `/login`: Form đăng nhập mật khẩu với nút bật/tắt hiện mật khẩu, nút "Đăng nhập bằng Google", chống double submit.
   - `/auth/callback`: Hoàn tất khôi phục phiên ứng dụng sau redirect backend sạch, không để lộ token trên URL.
   - `/forgot-password` & `/reset-password`: Khôi phục mật khẩu.
   - `/account`: Xem thông tin tài khoản, vai trò, quyền hạn.
   - `/account/security`: Đổi mật khẩu, liên kết Google OAuth, xem bảng phiên đang hoạt động (IP, Trình duyệt, hoạt động gần nhất) và nút thu hồi từng phiên / đăng xuất tất cả.
   - `/owner/registration-status`: Hiển thị tiến trình xét duyệt chủ quán.
   - `/403`: Màn hình từ chối truy cập rõ ràng.

### D. Sơ Đồ & Tài Liệu Kỹ Thuật
1. **Mã PlantUML độc lập**:
   - Use case xác thực: [`06_xac_thuc_va_bao_mat.puml`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/quan4_usecases_code/plantuml/06_xac_thuc_va_bao_mat.puml).
   - Sequence: [`SD02.puml`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/quan4_sequence_diagrams/plantuml/SD02.puml), [`SD-AUTH-GOOGLE.puml`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/quan4_sequence_diagrams/plantuml/SD-AUTH-GOOGLE.puml), [`SD-AUTH-GUARD.puml`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/quan4_sequence_diagrams/plantuml/SD-AUTH-GUARD.puml).
   - Activity: [`AD02.puml`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/activity%20diagram/plantuml/AD02.puml), [`AD-AUTH-GOOGLE.puml`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/activity%20diagram/plantuml/AD-AUTH-GOOGLE.puml).
2. **Focused Use Cases**:
   - Đầy đủ từ `U01` đến `U08` trong thư mục [`docs/focused-usecases/`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/focused-usecases/).
3. **Hướng dẫn cấu hình Google Cloud**:
   - Tài liệu chi tiết: [`docs/google-auth-setup.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/google-auth-setup.md).

---

## 2. Kết Quả Kiểm Thử (Verification Results)

### 1. Kiểm Thử Backend Tự Động (Pytest: 27/27 PASSED)
Suite [`test_auth_google_security.py`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/backend/tests/test_auth_google_security.py) kiểm thử 10 kịch bản tương ứng 18 tiêu chuẩn:
- `test_1_login_credentials_and_passwordless`: Mật khẩu đúng, sai, account inactive, và Google-only account. (PASSED)
- `test_2_unauthenticated_and_privilege_escalation`: Không có token -> 401; user thường gọi API admin -> 403. (PASSED)
- `test_3_refresh_token_rotation_and_reuse_detection`: Xoay vòng refresh cookie và phát hiện dùng lại token cũ. (PASSED)
- `test_4_logout_and_logout_all`: Thu hồi phiên đơn và thu hồi toàn bộ thiết bị. (PASSED)
- `test_5_google_oauth_anti_automerge`: Từ chối auto-merge khi email Google trùng tài khoản nội bộ. (PASSED)
- `test_6_google_oauth_new_user_role_assignment`: User Google mới nhận role `user` và `is_poi_owner_verified=False`. (PASSED)
- `test_7_google_account_linking_flow`: Liên kết tài khoản Google từ phiên đã đăng nhập. (PASSED)
- `test_8_password_recovery_flow`: Phản hồi generic và token reset 1 lần nguyên tử. (PASSED)
- `test_9_active_sessions_management`: Xem danh sách phiên (không lộ hash) và thu hồi phiên của chính mình. (PASSED)
- `test_10_public_endpoints_unrestricted`: POIs, Tours, Health, CSRF tiếp tục public không bị auth chặn. (PASSED)

### 2. Kiểm Thử Frontend Build
- `npm run build` trong `apps/web-admin/`: **0 errors**, biên dịch thành công qua TypeScript và Vite (1.64s).

### 3. Kiểm Thử Mobile App
- `node tests/geofence.test.js`: **6/6 tests passed**. Các tính năng du lịch (GPS, QR, Narration) không bị bắt buộc đăng nhập.

---

## 3. Phân Định Kiểm Chứng: Phần Đã Tự Động vs Phần Cần Google Credentials Thật

| Hạng mục xác thực | Trạng thái kiểm chứng | Chi tiết yêu cầu |
|---|---|---|
| **Logic mã hóa PKCE, Nonce, State Binding** | ✅ Đã kiểm chứng 100% tự động | Unit/Integration test nội bộ |
| **Bảo vệ chống Replay State & ID Token Validation** | ✅ Đã kiểm chứng 100% tự động | Mock payload chuẩn RS256 |
| **Quy tắc Anti Auto-merge khi trùng Email** | ✅ Đã kiểm chứng 100% tự động | Database local test |
| **Phân quyền Role Guard & Owner Verification** | ✅ Đã kiểm chứng 100% tự động | RBAC test suite |
| **HttpOnly Cookie Refresh Rotation & In-memory Token** | ✅ Đã kiểm chứng 100% tự động | AsyncClient cookie assertions |
| **Đổi mã Authorization Code thực tế với Google Server** | ⚠️ **Cần Google Credentials Thật** | Cần nhập `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET` theo hướng dẫn tại [`google-auth-setup.md`](file:///c:/Users/BiKiMC/Desktop/Seminar/seminarchuyende/docs/google-auth-setup.md) |
| **Màn hình đăng nhập tài khoản thực tế của Google** | ⚠️ **Cần Google Credentials Thật** | Cần tài khoản Google được add vào mục Test Users trên Google Cloud Console |
