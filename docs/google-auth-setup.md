# Hướng Dẫn Cấu Hình Google OAuth 2.0 & OpenID Connect

Tài liệu này hướng dẫn chi tiết quy trình đăng ký và thiết lập credentials thực tế trên **Google Cloud Console** để tích hợp tính năng Đăng nhập và Liên kết Google trên hệ thống TourVoice.

---

## 1. Tổng Quan Kiến Trúc Xác Thực Google

- **Chuẩn giao thức:** OpenID Connect (OIDC) / OAuth 2.0 Authorization Code Flow kèm PKCE (RFC 7636).
- **Scope yêu cầu:** `openid email profile` (tối thiểu cần thiết, không yêu cầu quyền Google Drive hay Gmail).
- **Endpoint Backend tiếp nhận Callback:**
  ```text
  http://localhost:8000/api/v1/auth/google/callback
  ```
- **Trang Callback Web Client (React):**
  ```text
  http://localhost:5173/auth/callback
  ```
- **Cơ chế truyền token:** Backend xác minh ID token với Google qua chữ ký RS256 JWKS, tạo phiên `auth_sessions`, đặt HttpOnly Refresh Cookie và redirect về trang web sạch. Tuyệt đối không truyền access/refresh token qua Query String URL.

---

## 2. Các Bước Tạo Credentials Trên Google Cloud Console

### Bước 1: Tạo Dự Án (Google Cloud Project)
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Đăng nhập bằng tài khoản Google.
3. Bấm vào menu chọn dự án ở góc trên bên trái -> chọn **"New Project" (Dự án mới)**.
4. Đặt tên dự án: `TourVoice-District-4` (hoặc tên tương tự) -> Bấm **"Create"**.

### Bước 2: Thiết Lập Màn Hình Đồng Ý OAuth (OAuth Consent Screen)
1. Vào menu **APIs & Services** -> chọn **OAuth consent screen**.
2. Chọn loại người dùng: **External (Bên ngoài)** -> Bấm **Create**.
3. Điền thông tin ứng dụng cơ bản:
   - **App name:** `TourVoice - Thuyết Minh Du Lịch Quận 4`
   - **User support email:** Điền email của bạn.
   - **Developer contact information:** Điền email của bạn.
4. Bấm **Save and Continue**.
5. **Mục Scopes (Phạm vi):**
   - Bấm **Add or Remove Scopes**.
   - Chọn 3 scopes:
     - `.../auth/userinfo.email`
     - `.../auth/userinfo.profile`
     - `openid`
   - Bấm **Update** -> Bấm **Save and Continue**.
6. **Mục Test Users (Người dùng thử nghiệm):**
   - Khi app ở trạng thái *Testing*, chỉ các email được thêm vào danh sách này mới có thể đăng nhập.
   - Bấm **Add Users** và nhập email Google của bạn (và các thành viên trong nhóm).
   - Bấm **Save and Continue**.

### Bước 3: Tạo OAuth 2.0 Client ID
1. Vào menu **APIs & Services** -> chọn **Credentials**.
2. Bấm **+ CREATE CREDENTIALS** -> chọn **OAuth client ID**.
3. Trong mục **Application type**, chọn: **Web application**.
4. Đặt tên: `TourVoice Web & Backend Client`.
5. **Authorized JavaScript origins (Nguồn gốc JavaScript được phép):**
   - `http://localhost:5173`
   - `http://localhost:8000`
   - `http://127.0.0.1:5173`
   - `http://127.0.0.1:8000`
6. **Authorized redirect URIs (URI chuyển hướng được phép):**
   - **BẮT BUỘC KHỚP CHÍNH XÁC:**
     ```text
     http://localhost:8000/api/v1/auth/google/callback
     ```
7. Bấm **CREATE**.
8. Hộp thoại xuất hiện cung cấp:
   - **Client ID** (dạng: `xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com`)
   - **Client Secret** (dạng: `GOCSPX-xxxxxxxxxxxxxxxxxxxx`)

---

## 3. Cấu Hình Vào Dự Án TourVoice

Sao chép thông tin vào file `.env` tại thư mục `backend/`:

```env
# Google OAuth 2.0 Configuration
GOOGLE_CLIENT_ID=xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:5173
FRONTEND_CALLBACK_URL=http://localhost:5173/auth/callback
```

---

## 4. Phân Định Kiểm Thử Tự Động vs Kiểm Thử Cần Credentials Thật

| Hạng mục kiểm tra | Phương thức kiểm tra | Yêu cầu Google Credentials thật? |
|---|---|---|
| **Cơ chế PKCE, state binding và chống CSRF** | Automated Unit/Integration Test | ❌ Không cần (Mock kiểm soát được) |
| **Bảo vệ chống Replay Attack trên State** | Automated Integration Test | ❌ Không cần (Test trực tiếp database TTL) |
| **Xác minh Claims (issuer, audience, sub, nonce, email_verified)** | Automated Test (`test_auth_google_security.py`) | ❌ Không cần (Đã test logic validation chặt chẽ) |
| **Quy tắc chống Auto-merge khi email trùng** | Automated Integration Test | ❌ Không cần (Test dữ liệu cục bộ) |
| **Cấp quyền vai trò mặc định 'user' (Non-promotion)** | Automated Integration Test | ❌ Không cần (Test trực tiếp role assignment) |
| **Liên kết Google từ Security settings** | Automated Integration Test | ❌ Không cần |
| **Khôi phục phiên bằng HttpOnly cookie khi reload** | Automated Browser/API Test | ❌ Không cần |
| **Đổi mã authorization code tại Google Token Endpoint** | End-to-End Live Check | ✅ **CẦN CREDENTIALS THẬT** (Cần Client ID/Secret từ Google Cloud Console) |
| **Màn hình đăng nhập tài khoản thực tế của Google (accounts.google.com)** | End-to-End Live Check | ✅ **CẦN CREDENTIALS THẬT** (Cần trình duyệt thật có tài khoản test users) |
