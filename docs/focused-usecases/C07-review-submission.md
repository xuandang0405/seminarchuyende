# C07 — Xét Duyệt Nội Dung Chủ Quán Gửi

## 1. Thông Tin Nhận Diện

- **Use Case ID:** C07
- **Use Case Name:** Xét duyệt nội dung chủ quán gửi
- **Module / System Boundary:** Phân hệ Web Quản trị (Web Admin) & Backend API
- **Primary Actor:** Quản trị viên (Admin / Super Admin có quyền `content:moderate`)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_moderation.py::test_owner_submission_and_admin_review`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Quản trị viên xem xét đề xuất chỉnh sửa hoặc tạo mới nội dung POI do chủ quán gửi lên; kiểm tra đối chiếu phiên bản trước và sau, sau đó đưa ra quyết định Chấp thuận (Approve) hoặc Từ chối (Reject) kèm ghi chú kiểm duyệt.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Admin mở màn hình "Kiểm Duyệt" và chọn một hồ sơ submission đang ở trạng thái `pending`.
- **Preconditions:** Admin đã đăng nhập và có token JWT hợp lệ chứa quyền `content:moderate` hoặc role `admin`/`super_admin`.
- **Assumptions:** Bản ghi submission tồn tại trong database với trạng thái `pending`.
- **Success Postconditions:** Trạng thái của submission chuyển thành `approved` (hoặc `rejected`); nếu được chấp thuận, payload được áp dụng vào POI với version mới tăng thêm 1; thông báo kết quả được tạo trong `owner_notifications`.
- **Minimum Guarantees:** Quyết định từ chối không bao giờ sửa đổi dữ liệu POI public; hai admin duyệt cùng một phiên bản không thể xung đột ghi đè (Optimistic Concurrency); không làm mất tính toàn vẹn dữ liệu khi có sự cố mạng.
- **Business Rules Liên Quan:** `BR-AUTH-01`, `BR-OWNER-01`, `BR-VERSION-01`, `BR-REVIEW-01`, `BR-REVIEW-02`, `BR-POI-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **C07.B1** | Chọn mục "Kiểm Duyệt" trên thanh điều hướng | Hệ thống gửi `GET /api/v1/admin/moderation/submissions`, kiểm tra quyền hạn, hiển thị danh sách các đề xuất đang `pending` | BR-AUTH-01, E1 |
| **C07.B2** | Nhấn chọn một đề xuất để xem chi tiết | Hiển thị thông tin người gửi, thời gian gửi, nội dung trước và sau (Diff) | E2 |
| **C07.B3** | Chọn "Chấp Thuận", nhập ghi chú kiểm duyệt | Hệ thống kiểm tra dữ liệu form hợp lệ, mở hộp thoại xác nhận phê duyệt | A1, E3 |
| **C07.B4** | Bấm "Xác Nhận Duyệt" | Gửi `POST /api/v1/admin/moderation/submissions/{id}` với `decision='approved'`, `admin_note` và `expected_version` | BR-VERSION-01, BR-REVIEW-01, E4 |
| **C07.B5** | — | Backend thực hiện transaction/atomic write: Cập nhật `poi_submissions.status='approved'`, áp dụng payload vào POI, tăng `version`, tạo `owner_notifications` | BR-REVIEW-02, E5 |
| **C07.B6** | Xem kết quả hiển thị | Hệ thống thông báo "Đã phê duyệt thành công", cập nhật danh sách và đánh dấu submission đã được giải quyết | BR-POI-01 |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **C07.A1 — Từ chối nội dung đề xuất (Rejection)**:
  - **Điểm rẽ:** Tại bước `C07.B3`, Admin chọn "Từ Chối" thay vì "Chấp Thuận".
  - **Các bước con:**
    1. Admin bắt buộc nhập lý do từ chối vào ô ghi chú kiểm duyệt.
    2. Admin bấm "Xác Nhận Từ Chối", gửi `decision='rejected'`.
    3. Backend cập nhật `poi_submissions.status='rejected'`, tạo thông báo cho chủ quán trong `owner_notifications`.
    4. Dữ liệu POI gốc được giữ nguyên 100%, không bị sửa đổi.
  - **Điểm kết thúc:** Kết thúc qua bước `C07.B6` với thông báo "Đã từ chối đề xuất".
- **C07.A2 — Hủy bỏ thao tác trước khi gửi**:
  - **Điểm rẽ:** Tại bước `C07.B3` hoặc `C07.B4`, Admin bấm "Hủy" hoặc đóng Modal.
  - **Các bước con:** Không có request nào được gửi đến server; submission vẫn giữ nguyên trạng thái `pending`.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **C07.E1 — Hết hạn phiên làm việc hoặc không đủ quyền**:
  - **Điểm phát sinh:** Tại bước `C07.B1` hoặc `C07.B4` khi token JWT hết hạn.
  - **Phản hồi:** Trả mã lỗi HTTP 401 / 403, chuyển hướng về trang Đăng nhập (`/login`).
- **C07.E2 — Submission không còn tồn tại**:
  - **Điểm phát sinh:** Tại bước `C07.B2` nếu bản ghi bị xóa.
  - **Phản hồi:** Hiển thị thông báo "Đề xuất này không còn tồn tại", làm mới danh sách.
- **C07.E3 — Thiếu lý do từ chối**:
  - **Điểm phát sinh:** Tại bước `C07.B3` khi từ chối mà để trống ô ghi chú.
  - **Phản hồi:** Form báo lỗi "Vui lòng nhập lý do từ chối để thông báo cho chủ quán".
- **C07.E4 — Xung đột phiên bản kiểm duyệt (Concurrent Review Conflict)**:
  - **Điểm phát sinh:** Tại bước `C07.B4` khi một Admin khác đã phê duyệt hoặc từ chối đề xuất này trước.
  - **Phản hồi:** Backend trả HTTP 400/409 "Submission has already been reviewed or version mismatch". Web hiển thị cảnh báo và tải lại trạng thái mới nhất.
- **C07.E5 — Lỗi cơ sở dữ liệu khi commit**:
  - **Điểm phát sinh:** Tại bước `C07.B5` khi server mất kết nối DB.
  - **Phản hồi:** Trả lỗi HTTP 500 kèm `request_id`, không tạo dữ liệu dở dang.

---

## 6. Extension Points

- Không có extension point được mô hình hóa riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD10 (Duyệt đăng ký & nội dung), AD10 (Activity kiểm duyệt).
- **Màn hình UI:** `apps/web-admin/src/pages/Moderation.tsx`.
- **API Endpoint:**
  - `GET /api/v1/admin/moderation/submissions`
  - `POST /api/v1/admin/moderation/submissions/{submission_id}`
- **Service & Repository:** `app/services/moderation_service.py`, Collection: `poi_submissions`, `POI`, `owner_notifications`.
- **Bằng chứng kiểm thử:**
  - `backend/tests/test_moderation.py::test_owner_submission_and_admin_review` (Passed).
- **Acceptance Criteria:**
  - *Given:* Đề xuất cập nhật POI đang ở trạng thái `pending`.
  - *When:* Admin gửi quyết định `approved` kèm `expected_version`.
  - *Then:* Trạng thái submission thành `approved`, POI được cập nhật nội dung mới, và chủ quán nhận được thông báo trong mục thông báo.
