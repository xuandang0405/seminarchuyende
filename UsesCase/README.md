# Bộ mã use case — FastAPI + MongoDB

Ngày lập: 2026-09-15. Phạm vi gồm mô tả ban đầu của nhóm và system-presentation-standalone(1).html.

## Cách dùng với Eraser

1. Giải nén bộ mã.
2. Tạo sơ đồ loại Flow Chart trong phần Diagram as Code.
3. Mở một file trong thư mục eraser và dán toàn bộ mã vào trình soạn thảo.
4. Dùng 00_toan_bo_usecase.txt để xem đủ 65 use case. Khi đưa vào báo cáo, dùng 5 sơ đồ chi tiết để chữ và các đường nối dễ đọc.
5. Mỗi file là một sơ đồ độc lập; không ghép nguyên các file vào cùng một sơ đồ vì ID sẽ bị khai báo lại.

Code Eraser dùng hình oval, actor có biểu tượng người/dịch vụ, khung hệ thống và quan hệ được gắn nhãn. Đây là cách biểu diễn use case bằng Flow Chart. Thư mục plantuml cung cấp bản UML với actor người que, include/extend và kế thừa actor, dùng trong công cụ có hỗ trợ PlantUML.

## Phạm vi và độ chắc chắn

- Không nhãn (H trong danh mục): 51 use case được mô hình hóa từ các chức năng và luồng trong HTML; đây là mô hình phân tích đề xuất, không phải xác nhận mã nguồn đã triển khai đầy đủ mọi hành vi.
- [G]: 11 use case từ mô tả ban đầu: điều khiển nghe, QR, tour, nhập bản dịch, upload MP3, thời gian nghe và tuyến/bản đồ nhiệt. Không tự xem các mục này là chức năng đã có trong HTML.
- [P]: 3 mục xuất báo cáo, cấu hình hệ thống, sao lưu được gợi ra từ tên quyền analytics:export, system:config, system:backup. HTML chưa mô tả đủ luồng thao tác; đây là phạm vi cần chốt, không được tự xem là yêu cầu bắt buộc của thầy.
- Các actor và cách chia use case là quyết định mô hình hóa, không phải số lượng use case được giảng viên ấn định.
- ERD theo HTML đã gửi trước chưa có toàn bộ dữ liệu cho tour/QR/tuyến đã đi. Nếu giữ nhóm [G], cần cập nhật thiết kế database tương ứng ở bước triển khai.

## Tác nhân

- Khách du lịch: chức năng công khai, không bắt buộc có tài khoản.
- Chủ quán / người đăng ký: gồm người mới nộp hồ sơ và chủ quán đã được xác minh; mỗi use case có tiền điều kiện riêng.
- Admin: thao tác theo quyền được cấp.
- Super Admin: kế thừa quyền Admin, thêm các tác vụ phân quyền/quản trị hệ thống. Eraser nối trực tiếp các use case được phép; PlantUML dùng quan hệ kế thừa.
- Dịch vụ định vị, bản đồ cloud, dịch thuật, TTS, AI, thời tiết: tác nhân hỗ trợ bên ngoài ranh giới ứng dụng. Bản đồ cloud/thời tiết chỉ tham gia khi tính năng tương ứng được bật.
- FastAPI, MongoDB, Redis, hàng chờ, worker và Service Worker là thành phần bên trong hệ thống, không được biến thành actor.

## Quy tắc nghiệp vụ phải giữ khi thuyết trình

1. Đã đăng nhập là tiền điều kiện của các thao tác cần bảo vệ. Không nối include đến Đăng nhập từ mọi use case.
2. Owner chưa được xác minh vẫn đăng nhập và xem trạng thái đăng ký; quyền quản lý quán/nội dung/thống kê phụ thuộc xác minh và quyền sở hữu.
3. Nộp nội dung thành công không đồng nghĩa nội dung đã xuất bản. Admin xét duyệt; public POI trong HTML còn cần sẵn sàng tiếng Anh và audio.
4. Đăng ký chủ quán, duyệt hồ sơ, gửi submission và đọc thông báo là các mục tiêu khác nhau. Association không biểu diễn thứ tự thực hiện; quy trình thời gian nên vẽ bằng activity/sequence diagram.
5. Nghe bằng GPS, chọn thủ công hoặc quét QR đều dùng hành vi Phát nội dung thuyết minh. Không giả định mỗi lượt nghe đều cần gọi API TTS/dịch.
6. Chuẩn bị thuyết minh theo yêu cầu chỉ mở rộng luồng nghe khi thiếu audio phù hợp và có mạng; dịch chỉ bổ sung nếu thiếu bản dịch. TTS thất bại vẫn phải có luồng báo lỗi/dự phòng.
7. Cooldown, debounce, ưu tiên, hàng chờ, chống phát trùng, TTL, checksum và transaction là chi tiết/quy tắc bên trong use case. Không cần biến mỗi cơ chế thành một mục tiêu người dùng.
8. Offline chỉ sử dụng tài nguyên đã có. QR offline cần có ánh xạ QR–POI; tải/cập nhật/sửa gói cần kết nối phù hợp.
9. Public analytics cần sự đồng ý. Runtime observability được HTML mô tả riêng nhưng không được mặc định dùng để vượt lựa chọn riêng tư.
10. Không đồng nhất số thiết bị/phiên với số người. Mẫu vị trí gắn ID ngẫu nhiên không tự động thành dữ liệu hoàn toàn ẩn danh.
11. Quyền xem thống kê của owner chỉ áp dụng cho quán của mình. Quyền mặc định owner trong HTML cho menu là đọc/thêm/sửa; sơ đồ không tự cấp thêm quyền xóa.
12. [P] mô tả phạm vi đề xuất; bộ mã này không tạo API, database, tài khoản hay tác vụ sao lưu thật.

## Ký hiệu

- Đường liền: actor tham gia use case, không phải luồng điều khiển.
- include: mũi tên từ use case sử dụng đến hành vi dùng chung được bao gồm.
- extend: mũi tên từ hành vi mở rộng đến use case cơ sở; điều kiện nằm trong comment Eraser và nhãn PlantUML.
- Kế thừa actor trong PlantUML: SuperAdmin --|> Admin.
- system boundary: khung ứng dụng bao quanh các use case; actor nằm ngoài khung.

## Danh sách sơ đồ

- 00_toan_bo_usecase: Toàn bộ use case dự án - 65 trường hợp sử dụng
- 01_khach_va_thuyet_minh: Khách du lịch, tour và thuyết minh
- 02_offline_va_rieng_tu: Offline và lựa chọn thu thập thống kê
- 03_chu_quan_va_tai_khoan: Chủ quán, đăng ký và nội dung chờ duyệt
- 04_quan_tri_noi_dung: Quản trị nội dung, audio, tour và QR
- 05_phan_quyen_thong_ke_van_hanh: Phân quyền, thống kê và vận hành

## Nguồn đối chiếu

- system-presentation-standalone(1).html: Chapter 00 (kiến trúc), 04 (GPS/thuyết minh), 05 (POI), 06 (TTS), 07 (RBAC), 08 (đa ngôn ngữ), 09 (offline), 10 (bản đồ), 11 (admin/owner/AI), và các sơ đồ analytics/runtime.
- Mô tả ban đầu do nhóm cung cấp: tour, QR, upload MP3, thống kê nghe/tuyến và heatmap.
- Eraser Flow Chart syntax: https://docs.eraser.io/flow-chart-syntax
- PlantUML use case syntax: https://plantuml.com/use-case-diagram

Kiểm tra đã thực hiện: ID không trùng, các đầu nối tồn tại, include không tạo vòng lặp, các view chi tiết phủ đủ 65 use case. Chưa render trực tiếp bằng Eraser hoặc PlantUML.
