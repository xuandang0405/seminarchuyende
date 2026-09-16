# Use Case Change Log — Lịch Sử Cập Nhật Hồ Sơ Nghiệp Vụ

Tài liệu này ghi nhận toàn bộ các thay đổi về mô hình Use Case, cấu trúc đặc tả và sơ đồ nghiệp vụ theo tiêu chuẩn **Focused Use Cases**.

---

## Bảng Nhật Ký Thay Đổi (Change Log)

| Change ID | UC / BR Liên Quan | Mô Tả Trước Thay Đổi | Mô Tả Sau Thay Đổi | Loại | File Đã Sửa | Test / Bằng Chứng Đã Chạy |
|---|---|---|---|---|---|---|
| **CHG-01** | Toàn bộ 65 UCs | Đặc tả sơ lược theo dạng danh mục 1 dòng trong `usecase_catalog.md` | Chuẩn hóa theo mẫu Focused Use Case: Actor Action / System Response, Alt/Exc paths, Min Guarantees, Pre/Post conditions | **DOC** | `docs/focused-usecases/*.md`, `docs/focused-usecases/README.md`, `_template.md` | Đã nghiệm thu cấu trúc tài liệu |
| **CHG-02** | Toàn bộ BRs | Quy tắc nghiệp vụ (3s debounce, 5m cooldown, readiness gate) nằm rải rác trong code | Tổng hợp thành 23 Business Rules (`BR-AUTH-01` đến `BR-TOUR-01`) với tham số định lượng, service thực thi và test | **DOC** | `docs/business-rules.md` | Đối chiếu trực tiếp với codebase |
| **CHG-03** | F02, F03, F04, F06 | Sơ đồ use case offline chưa biểu diễn rõ mối quan hệ giữa F02 và các thao tác cập nhật/sửa/dùng offline | Bổ sung quan hệ `F03 ..> F02 : <<extend>>`, `F04 ..> F02 : <<extend>>`, `F06 ..> F02 : <<extend>>` trong cả PlantUML và Eraser | **MODEL** | `quan4_usecases_code/plantuml/02_offline_va_rieng_tu.puml`, `00_toan_bo_usecase.puml`, bản Eraser tương ứng | Sơ đồ được kiểm tra cú pháp PlantUML & Eraser DSL |
| **CHG-04** | U01 & Bảo vệ phiên | Đăng nhập có thể bị hiểu nhầm là sub-usecase được include ở mọi thao tác | Khẳng định phiên đăng nhập hợp lệ là Precondition (tiền điều kiện); U01 là User-Goal độc lập | **MODEL** | `docs/focused-usecases/U01-login.md`, sơ đồ usecase | `backend/tests/test_auth_rbac.py` passed |
| **CHG-05** | O05 & C07 | Gửi duyệt và xét duyệt dễ bị vẽ gộp hoặc include lẫn nhau | Tách rõ O05 (Chủ quán gửi bài) và C07 (Admin xét duyệt) là 2 use case độc lập của 2 actor khác nhau ở 2 thời điểm | **MODEL** | `docs/focused-usecases/O05-submit-poi-content.md`, `C07-review-submission.md` | `backend/tests/test_moderation.py` passed |
| **CHG-06** | T08, T09, T11 & N01 | Trình phát âm thanh có thể bị hiểu là chạy 3 player riêng biệt cho 3 nguồn | Khẳng định `N01` là Unified Narration Controller dùng chung; T08/T09/T11 include N01; N02 extend N01 khi thiếu audio | **MODEL** | `docs/focused-usecases/T08-T09-T10-audio-narration.md`, `N01-N02-narration-subflows.md` | `mobile/tests/geofence.test.js` passed |
| **CHG-07** | F08 & T13 | Lo ngại việc từ chối thống kê sẽ cản trở du khách đi tour | Làm rõ trong đặc tả và code: Consent F08 hoàn toàn độc lập với phiên tour local T13; từ chối vẫn dùng 100% tính năng | **BEHAVIOR** | `docs/focused-usecases/F08-manage-analytics-consent.md`, `mobile/src/services/AnalyticsOutbox.js` | `backend/tests/test_analytics.py` passed |
| **CHG-08** | C07 & C04 | Phê duyệt submission của chủ quán có thể bị hiểu nhầm là tự động publish ra ngoài | Khẳng định Approval chỉ cập nhật nội dung draft/version; việc công bố ra public bắt buộc phải qua Readiness Gate `BR-POI-01` | **BEHAVIOR** | `docs/focused-usecases/C07-review-submission.md`, `backend/app/services/moderation_service.py` | `backend/tests/test_moderation.py` passed |
| **CHG-09** | S10, S12, S13 | Các tính năng có nhãn `[P]` (Proposal) | Giữ nguyên trạng thái P trong backlog, không coi là bắt buộc hay tuyên bố hoàn thành khi chưa có luồng chốt | **SCOPE_PROPOSAL** | `docs/usecase-gap-analysis.md` | Duy trì tính trung thực của đồ án |
