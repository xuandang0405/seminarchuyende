# O10 — Xem Thống Kê Quán Của Mình

## 1. Thông Tin Nhận Diện

- **Use Case ID:** O10
- **Use Case Name:** Xem thống kê quán của mình
- **Module / System Boundary:** Phân hệ Cổng Thông Tin Chủ Quán & Backend API
- **Primary Actor:** Chủ quán (POI Owner có quyền `analytics:view_own`)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`test_analytics.py`, `OwnerPortal.tsx`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Chủ quán xem số liệu thống kê lượt nghe thuyết minh và thời gian du khách tìm hiểu về quán ăn của riêng mình. Hệ thống tự động giới hạn phạm vi truy vấn (`owner_scope`), tuyệt đối không cho phép chủ quán xem số liệu của các quán khác.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Chủ quán bấm vào tab "Thống kê" trong màn hình Quán Của Tôi (`/owner`).
- **Preconditions:** Chủ quán đã đăng nhập và đã được cấp quyền `analytics:view_own`.
- **Assumptions:** Quán của chủ quán đã có dữ liệu POI.
- **Success Postconditions:** Hiển thị số lượt nghe và thời lượng nghe trung bình chỉ tính riêng cho POI thuộc sở hữu của chủ quán.
- **Minimum Guarantees:** Chống rò rỉ dữ liệu cạnh tranh: Chủ quán A không thể xem chỉ số của chủ quán B (`BR-OWNER-01`).
- **Business Rules Liên Quan:** `BR-OWNER-01`, `BR-METRIC-01`, `BR-AUTH-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **O10.B1** | Bấm mục "Thống kê quán" trên Owner Portal | Gọi `GET /api/v1/owner/analytics` | BR-AUTH-01 |
| **O10.B2** | — | Backend trích xuất `user._id`, lọc danh sách POI thuộc sở hữu của chủ quán | BR-OWNER-01 |
| **O10.B3** | — | Truy vấn chỉ số từ `analytics_poi_daily_metrics` trong phạm vi các POI thuộc quyền | BR-METRIC-01 |
| **O10.B4** | Xem kết quả | Hiển thị: Tổng lượt khách nghe thuyết minh quán mình, thời gian nghe trung bình và món ăn được xem nhiều nhất | — |

---

## 4. Alternative Paths

- Không có nhánh thay thế.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **O10.E1 — Chủ quán chưa có POI nào**:
  - **Điểm phát sinh:** Tại bước `O10.B2` khi chủ quán mới chưa có điểm đến được duyệt.
  - **Phản hồi:** Hiển thị thông báo "Bạn chưa có địa điểm nào được công bố để thống kê".

---

## 6. Extension Points

- Không có extension point riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD13 (Xem thống kê), AD13.
- **Màn hình UI:** `apps/web-admin/src/pages/OwnerPortal.tsx`.
- **API Endpoint:** `GET /api/v1/owner/analytics`.
- **Service:** `app/services/analytics_service.py`, `app/services/owner_service.py`.
- **Bằng chứng kiểm thử:** `backend/tests/test_analytics.py` (Passed).
