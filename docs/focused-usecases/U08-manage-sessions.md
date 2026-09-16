# U08 — Xem & Thu Hồi Phiên Đăng Nhập

## 1. Thông Tin Nhận Diện
- **Use Case ID:** U08
- **Use Case Name:** Xem và thu hồi phiên làm việc của mình
- **Module / System Boundary:** Phân hệ Xác thực & Quản lý Phiên (Auth Module)
- **Primary Actor:** Người dùng đã đăng nhập
- **Maturity:** Focused
- **Scope:** [H]; user-goal
- **Summary / Goal:** Người dùng giám sát các thiết bị đang đăng nhập tài khoản của mình (IP, User-Agent, thời gian hoạt động gần nhất) và có thể chủ động thu hồi từng phiên cụ thể hoặc toàn bộ các phiên khác để bảo vệ an toàn tài khoản.

---

## 2. Điều Kiện & Quy Tắc
- **Trigger:** Người dùng truy cập mục Phiên Hoạt Động tại `/account/security`.
- **Preconditions:** Người dùng đã đăng nhập hợp lệ.
- **Success Postconditions:** Hiển thị danh sách phiên còn hiệu lực (không bị lộ token hash); khi bấm "Thu hồi", phiên đó bị đánh dấu `revoked_at` trong `auth_sessions`.
- **Minimum Guarantees:** Người dùng chỉ có thể xem và thu hồi phiên thuộc chính tài khoản của mình (`user_id == session.user_id`); không bao giờ có thể xem hoặc xóa phiên của người khác qua việc thay đổi session ID (chống IDOR).

---

## 3. Basic Course of Events

| Step ID | Actor Action | System Response |
|---|---|---|
| **U08.B1** | Mở trang Bảo mật | Client gửi `GET /api/v1/auth/sessions` kèm Bearer token |
| **U08.B2** | — | Backend truy vấn `auth_sessions` với điều kiện `user_id == current_user.id`, `revoked_at is None`, `expires_at > now` (loại trừ `refresh_token_hash`) |
| **U08.B3** | Xem danh sách | Hiển thị bảng phiên gồm Trình duyệt, IP, Hoạt động gần nhất |
| **U08.B4** | Bấm "Thu hồi" 1 phiên | Client gửi `DELETE /api/v1/auth/sessions/{session_id}` |
| **U08.B5** | — | Backend xác nhận `session.user_id == current_user.id`, cập nhật `revoked_at = now()` và phản hồi thành công |

---

## 4. Exception Paths
- **U08.E1 — IDOR / Thu hồi phiên người khác**: Nếu người dùng gọi `DELETE /api/v1/auth/sessions/{id}` với session ID thuộc người khác, backend trả 404/403 và không làm ảnh hưởng tới phiên của nạn nhân.

---

## 5. Truy Vết Triển Khai
- **Sơ đồ liên quan:** 06_xac_thuc_va_bao_mat.puml, SD-AUTH-GUARD.
- **Màn hình UI:** `apps/web-admin/src/pages/AccountSecurity.tsx`.
- **API Endpoint:** `GET /api/v1/auth/sessions`, `DELETE /api/v1/auth/sessions/{session_id}`.
- **Collection:** `auth_sessions`.
