# U02 — Đăng Xuất & Thu Hồi Phiên Làm Việc

## 1. Thông Tin Nhận Diện
- **Use Case ID:** U02
- **Use Case Name:** Đăng xuất và thu hồi phiên làm việc
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Người dùng đã đăng nhập (Admin, POI Owner, User)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng chủ động kết thúc phiên làm việc. Hệ thống thu hồi phiên trong cơ sở dữ liệu `auth_sessions`, xóa HttpOnly cookie và giải phóng Access Token khỏi bộ nhớ client.

---

## 2. Điều Kiện & Quy Tắc
- **Trigger:** Người dùng bấm nút "Đăng xuất" tại Header hoặc Sidebar.
- **Preconditions:** Người dùng đang có phiên đăng nhập hợp lệ.
- **Success Postconditions:** Session được đánh dấu `revoked_at` trong `auth_sessions`, cookie `tourvoice_refresh_token` bị xóa, client chuyển trạng thái sang `anonymous` và điều hướng về `/login`.
- **Minimum Guarantees:** Không chỉ xóa token ở client; server thực sự thu hồi phiên để ngăn chặn token replay.
- **Business Rules Liên Quan:** `BR-AUTH-02`.

---

## 3. Basic Course of Events

| Step ID | Actor Action | System Response |
|---|---|---|
| **U02.B1** | Bấm nút "Đăng xuất" | Client gọi `POST /api/v1/auth/logout` kèm thông tin phiên |
| **U02.B2** | — | Backend tìm phiên trong `auth_sessions` và cập nhật `revoked_at = now()` |
| **U02.B3** | — | Backend trả về `Set-Cookie` xóa bỏ `tourvoice_refresh_token` |
| **U02.B4** | — | Client xóa Access Token trong bộ nhớ RAM, đặt trạng thái `anonymous` và chuyển về `/login` |

---

## 4. Alternative Paths
- **U02.A1 — Đăng xuất khỏi tất cả thiết bị (Logout All)**:
  - Người dùng bấm "Đăng xuất tất cả thiết bị" tại `/account/security`.
  - Backend gọi `auth_repo.revoke_all_user_sessions(user_id)` và tăng `auth_version`.
  - Mọi JWT access token và refresh token đang hoạt động của user trên các thiết bị khác đều bị từ chối ngay lập tức.

---

## 5. Truy Vết Triển Khai
- **Sơ đồ liên quan:** SD02, 06_xac_thuc_va_bao_mat.puml.
- **Màn hình UI:** Header, Sidebar, `apps/web-admin/src/pages/AccountSecurity.tsx`.
- **API Endpoint:** `POST /api/v1/auth/logout`, `POST /api/v1/auth/logout-all`.
- **Collection:** `auth_sessions`, `admin_users`.
