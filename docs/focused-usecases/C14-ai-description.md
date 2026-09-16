# C14 — Dùng AI Gợi Ý Mô Tả Địa Điểm

## 1. Thông Tin Nhận Diện

- **Use Case ID:** C14
- **Use Case Name:** Dùng AI gợi ý mô tả địa điểm
- **Module / System Boundary:** Phân hệ Trợ Lý AI Backend & Web Admin / Owner Portal
- **Primary Actor:** Quản trị viên (Admin) hoặc Chủ quán (Owner)
- **Supporting Actors:** Dịch vụ AI (Google Gemini / OpenAI / Demo Provider)
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`ai_usage_limits`, `POIList.tsx`)
- **Scope:** [H]; user-goal / supporting extension
- **Summary / Goal:** Người dùng (Admin hoặc Chủ quán) bấm nút yêu cầu AI gợi ý đoạn văn bản giới thiệu hấp dẫn về di tích lịch sử hoặc món ăn đặc sản Quận 4. Hệ thống kiểm tra hạn mức gọi AI trong ngày, sinh văn bản mẫu đưa vào khung soạn thảo để người dùng chỉnh sửa trước khi lưu.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Người dùng bấm nút "✨ AI Gợi Ý Mô Tả" trong form soạn thảo POI.
- **Preconditions:** Người dùng đã đăng nhập; tài khoản chưa vượt quá hạn mức gọi AI trong ngày (`ai_usage_limits`).
- **Assumptions:** Dịch vụ AI có sẵn hoặc đang ở chế độ mock dữ liệu văn hóa Quận 4.
- **Success Postconditions:** Nhận văn bản gợi ý; tăng bộ đếm lượt dùng AI trong ngày (`count += 1`); văn bản được điền vào ô soạn thảo draft.
- **Minimum Guarantees:** Kết quả của AI chỉ là bản nháp (draft), tuyệt đối không tự động lưu đè hoặc tự động công bố ra ngoài (`BR-AI-01`); hai request đồng thời không thể vượt quá hạn mức ngày.
- **Business Rules Liên Quan:** `BR-AI-01`, `BR-AUTH-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **C14.B1** | Bấm nút "✨ AI Gợi Ý Mô Tả" | Form gửi yêu cầu kèm tên địa điểm và danh mục món ăn | — |
| **C14.B2** | — | Backend kiểm tra hạn mức trong `ai_usage_limits` theo user và ngày hiện tại | BR-AI-01, E1 |
| **C14.B3** | — | Gọi API sinh nội dung mô tả văn hóa du lịch / ẩm thực Quận 4 | E2 |
| **C14.B4** | — | Tăng `count` trong `ai_usage_limits`, trả về văn bản gợi ý | — |
| **C14.B5** | Xem và chỉnh sửa văn bản gợi ý | Đoạn văn được điền vào trường mô tả, người dùng có thể sửa đổi theo ý muốn trước khi lưu | A1 |

---

## 4. Alternative Paths

- **C14.A1 — Người dùng từ chối gợi ý**:
  - **Điểm rẽ:** Tại bước `C14.B5` khi người dùng bấm "Hủy" hoặc xóa đoạn văn bản.
  - **Hành vi:** Giữ nguyên văn bản gốc trước đó của form, không ảnh hưởng đến dữ liệu database.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **C14.E1 — Vượt quá hạn mức gọi AI trong ngày**:
  - **Điểm phát sinh:** Tại bước `C14.B2` khi `count >= daily_limit`.
  - **Phản hồi:** Trả HTTP 429: "Bạn đã dùng hết hạn mức AI của ngày hôm nay. Vui lòng thử lại vào ngày mai".
- **C14.E2 — Lỗi kết nối dịch vụ AI bên ngoài**:
  - **Điểm phát sinh:** Tại bước `C14.B3` khi AI Provider bị lỗi hoặc thiếu API key.
  - **Phản hồi:** Backend trả đoạn văn mẫu giới thiệu Quận 4 được định nghĩa an toàn, không làm crash form.

---

## 6. Extension Points

- Extend vào `C01`, `C02` (Admin thêm/sửa POI) và `O04` (Chủ quán soạn nội dung).

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD15 (AI gợi ý mô tả), AD15 (Activity AI).
- **Màn hình UI:** `apps/web-admin/src/pages/POIList.tsx`.
- **API Endpoint:** `POST /api/v1/ai/generate-description`.
- **Collection:** `ai_usage_limits`, `POI`.
- **Bằng chứng kiểm thử:** `backend/tests/test_api.py` (Passed).
