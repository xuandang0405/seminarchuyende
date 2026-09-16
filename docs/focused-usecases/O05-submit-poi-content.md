# O05 — Gửi Nội Dung Quán Chờ Xét Duyệt

## 1. Thông Tin Nhận Diện

- **Use Case ID:** O05
- **Use Case Name:** Gửi nội dung quán chờ xét duyệt
- **Module / System Boundary:** Phân hệ Cổng Thông Tin Chủ Quán & Backend API
- **Primary Actor:** Chủ quán đã được xác minh (Verified POI Owner)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_moderation.py::test_owner_submission_and_admin_review`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Chủ quán soạn thảo thông tin cập nhật (hoặc yêu cầu tạo mới) điểm ẩm thực của mình, sau đó gửi hồ sơ đề xuất (Submission) lên hệ thống để Admin kiểm duyệt. Nội dung công khai trên mobile được bảo vệ nguyên vẹn cho đến khi Admin phê duyệt.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Chủ quán bấm nút "Gửi Duyệt" từ màn hình chi tiết quán của tôi (`/owner`).
- **Preconditions:** Chủ quán đã đăng nhập và tài khoản đã được xác thực (`is_poi_owner_verified=True`).
- **Assumptions:** Chủ quán là người sở hữu hợp pháp của POI (`poi.owner_id == actor_id`).
- **Success Postconditions:** Tạo mới bản ghi trong `poi_submissions` với `status='pending'` và payload chứa thông tin đề xuất; dữ liệu POI công khai chưa bị thay đổi.
- **Minimum Guarantees:** Chủ quán A không thể gửi đề xuất sửa đổi POI thuộc quyền sở hữu của chủ quán B (Chống lỗ hổng IDOR - `BR-OWNER-01`).
- **Business Rules Liên Quan:** `BR-OWNER-01`, `BR-AUTH-01`, `BR-IDEM-01`, `BR-REVIEW-02`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **O05.B1** | Mở form chỉnh sửa thông tin quán | Hiển thị thông tin hiện tại: Tên quán, địa chỉ, mô tả, hình ảnh | BR-OWNER-01, E1 |
| **O05.B2** | Chỉnh sửa nội dung mong muốn | Form validate độ dài và tính hợp lệ của dữ liệu | — |
| **O05.B3** | Bấm nút "Gửi Xét Duyệt" | Gửi `POST /api/v1/owner/submissions` với payload và `poi_id` | BR-IDEM-01 |
| **O05.B4** | — | Backend kiểm tra quyền sở hữu IDOR: xác nhận POI thuộc quyền của user | E2 |
| **O05.B5** | — | Tạo document `poi_submissions` với `status='pending'`, lưu version hiện tại của POI | BR-REVIEW-02 |
| **O05.B6** | Xem kết quả | Hiển thị thông báo "Đề xuất đã được gửi đi và đang chờ Admin phê duyệt" | — |

---

## 4. Alternative Paths

- Không có nhánh thay thế.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **O05.E1 — Tài khoản chủ quán chưa được duyệt**:
  - **Điểm phát sinh:** Tại bước `O05.B1` khi `is_poi_owner_verified=False`.
  - **Phản hồi:** Chặn thao tác, hiển thị thông báo "Tài khoản của bạn đang chờ Admin duyệt, chưa thể gửi đề xuất nội dung".
- **O05.E2 — Vi phạm quyền sở hữu (IDOR Violation)**:
  - **Điểm phát sinh:** Tại bước `O05.B4` khi chủ quán gửi `poi_id` không thuộc quyền quản lý của mình.
  - **Phản hồi:** Trả mã lỗi HTTP 403 Forbidden: "You do not own this POI".

---

## 6. Extension Points

- `C14 Dùng AI gợi ý mô tả` có thể extend tại bước `O05.B2` để hỗ trợ chủ quán viết bài giới thiệu món ăn.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD09 (Chủ quán gửi nội dung), AD09 (Activity gửi nội dung).
- **Màn hình UI:** `apps/web-admin/src/pages/OwnerPortal.tsx`.
- **API Endpoint:** `POST /api/v1/owner/submissions`.
- **Service & Repository:** `app/services/owner_service.py`, `app/repositories/owner_repo.py`, Collection: `poi_submissions`, `POI`.
- **Bằng chứng kiểm thử:** `backend/tests/test_moderation.py::test_owner_submission_and_admin_review` (Passed).
