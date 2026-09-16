# [MÃ_UC] — [Tên Use Case (Động Từ + Mục Tiêu)]

## 1. Thông Tin Nhận Diện

- **Use Case ID:** [MÃ_UC] (ví dụ: T11, C07, U01)
- **Use Case Name:** [Tên nghiệp vụ]
- **Module / System Boundary:** Hệ thống Thuyết minh Du lịch Đa ngôn ngữ (Phân hệ Mobile / Web Admin / Backend API)
- **Primary Actor:** [Người dùng có mục tiêu, ví dụ: Khách du lịch / Admin / Chủ quán]
- **Supporting Actors:** [Dịch vụ ngoài thực sự có tương tác: GPS, Maps, TTS Provider, AI Provider...]
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (hoặc Đang triển khai / Backlog P)
- **Scope:** [H / G / P]; user-goal hoặc supporting-subflow
- **Summary / Goal:** [Mô tả 2-4 câu về giá trị và kết quả người dùng nhận được khi hoàn thành use case]
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** [Sự kiện bắt đầu cụ thể]
- **Preconditions:** [Điều kiện tiên quyết phải đúng trước khi use case bắt đầu]
- **Assumptions:** [Các giả định kỹ thuật / môi trường]
- **Success Postconditions:** [Kết quả hệ thống và dữ liệu sau khi đạt mục tiêu thành công]
- **Minimum Guarantees:** [Các đảm bảo an toàn dữ liệu và bảo mật kể cả khi gặp lỗi hay hủy giữa chừng]
- **Business Rules Liên Quan:** [Danh sách mã BR liên quan: BR-AUTH-01, BR-POI-01...]

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| [UC].B1 | [Hành động của Actor] | [Hệ thống xử lý & phản hồi hiển thị] | [Quy tắc / E1] |
| [UC].B2 | [Hành động tiếp theo hoặc "—"] | [Hệ thống kiểm tra & chuyển bước] | [Quy tắc / A1] |
| [UC].B3 | [Hành động tiếp theo hoặc "—"] | [Hệ thống lưu trữ và trả kết quả] | [Quy tắc] |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **[UC].A1 — [Tên nhánh thay thế, ví dụ: Chế độ Ngoại tuyến / Từ chối duyệt]**:
  - **Điểm rẽ:** Rẽ từ bước `[UC].B[X]` khi [điều kiện].
  - **Các bước con:**
    1. Hệ thống thực hiện [hành vi thay thế].
    2. Người dùng chọn [tùy chọn].
  - **Điểm quay lại / Kết thúc:** Nhập lại bước `[UC].B[Y]` hoặc kết thúc thành công theo nhánh riêng với hậu điều kiện [kết quả].

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ & Lỗi)

- **[UC].E1 — [Tên ngoại lệ, ví dụ: Lỗi quyền truy cập / Mất mạng / Xung đột phiên bản]**:
  - **Điểm phát sinh:** Tại bước `[UC].B[X]` khi [nguyên nhân].
  - **Phản hồi hệ thống:** Hiển thị thông báo lỗi rõ ràng cho người dùng (không lộ stacktrace).
  - **Hành động khắc phục:** Cho phép người dùng [thử lại / hủy bỏ].
  - **Trạng thái dữ liệu:** Đảm bảo tính toàn vẹn dữ liệu theo Minimum Guarantees.

---

## 6. Extension Points (Điểm Mở Rộng)

- [Nếu có use case mở rộng: Ghi rõ tên extension point, vị trí bước cơ sở, điều kiện guard, use case được extend. Nếu không có, ghi: "Không có extension point được mô hình hóa riêng."]

---

## 7. Truy Vết Triển Khai & Nghiệm Thu (Traceability)

- **Sơ đồ liên quan:** [Mã SD*, AD*]
- **Giao diện người dùng (UI Screen):** [Component / Màn hình Web hoặc Mobile]
- **API Endpoint & Method:** [VD: `POST /api/v1/...`]
- **Service & Repository:** [Tên Service, Repository, Collections]
- **Acceptance Criteria (Given / When / Then):**
  - **Scenario 1 (Thành công):**
    - *Given:* [Điều kiện sẵn có]
    - *When:* [Hành động kích hoạt]
    - *Then:* [Kết quả mong đợi quan sát được]
  - **Scenario 2 (Ngoại lệ):**
    - *Given:* [Điều kiện lỗi]
    - *When:* [Hành động kích hoạt]
    - *Then:* [Thông báo và hành vi an toàn]
- **Bằng chứng kiểm thử:** [Đường dẫn file test tự động trong `backend/tests/` hoặc `mobile/tests/`]
