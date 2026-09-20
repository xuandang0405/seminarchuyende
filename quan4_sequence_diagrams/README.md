# Sequence diagrams — Hệ thống thuyết minh du lịch đa ngôn ngữ

Bộ mã gồm 15 luồng tương tác chính, mỗi luồng có tối đa 5 lifeline. Đây là thiết kế phân tích đề xuất cho FastAPI + MongoDB dựa trên HTML đã gửi và yêu cầu ban đầu; không khẳng định mã nguồn hiện tại đã triển khai tất cả các bước.

## Dùng trong Eraser

1. Giải nén bộ mã.
2. Chọn loại Sequence Diagram trong phần Diagram as Code.
3. Mở một file trong thư mục eraser và dán toàn bộ mã vào trình soạn thảo.
4. Mỗi file là một sơ đồ độc lập; không nối nguyên các file thành một sơ đồ.
5. Các file trong thư mục mermaid dùng cho trình hiển thị Mermaid, không phải cú pháp Eraser.

Mỗi file Eraser có comment giải thích giả định và mức chi tiết. autoNumber đánh số thông điệp. Mũi tên nét liền thể hiện lời gọi/thông điệp; nét đứt dùng cho phản hồi. alt/else là các nhánh thay thế; opt là tùy điều kiện; loop là lặp; par/and là các nhánh song song; break kết thúc luồng trong trường hợp ngoại lệ.

## Danh sách

| Số | Luồng | Nguồn | Use case liên quan |
|---|---|---|---|
| 01 | Mở ứng dụng và nạp nội dung đa ngôn ngữ | H | T01, T03, T05, T07, F07 |
| 02 | Đăng nhập qua ba lớp FastAPI | H | U01 |
| 03 | Admin thêm/sửa POI, trợ lý Gemini 3.6 AI (tự điền/tối ưu mô tả/soạn audio) & tạo audio | H, Code | C01, C02, C04, C14 |
| 04 | Tự động thuyết minh khi đến gần POI | H | T02, T04, T09, N01, N02 |
| 05 | Quét QR để nghe thuyết minh | G | T11, N01 |
| 06 | Tải và kích hoạt gói offline | H | F02, F03, F04, F05, F06 |
| 07 | Worker tạo audio và lưu kết quả an toàn | H | C09, C11, C12, C13, N02 |
| 08 | Đăng ký chủ quán chờ xác minh | H | O01, O02 |
| 09 | Chủ quán gửi nội dung chờ kiểm duyệt | H | O03, O04, O05, O06 |
| 10 | Admin xét duyệt hồ sơ hoặc nội dung chủ quán | H | C06, C07, O02, O06, O07, O08 |
| 11 | Ghi nhận và đồng bộ thống kê có chống trùng | H | F08, S05, S06, S07 |
| 12 | Worker tổng hợp dữ liệu cho dashboard | H | S05, S06, S07 |
| 13 | Admin hoặc chủ quán xem thống kê đúng phạm vi | H | O10, S05, S06, S07 |
| 14 | Chọn tour và bắt đầu hoặc kết thúc chuyến đi | G | T12, T13, C15, S08 |
| 15 | AI gợi ý mô tả, kịch bản thuyết minh & bản địa hóa 6 ngôn ngữ qua Gemini 3.6 | H, Code | C14, O04 |

H: mô hình hóa từ chức năng và luồng trong HTML, có thêm chi tiết thiết kế để làm rõ tính đúng đắn.
G: QR và tour thuộc mô tả ban đầu; HTML và ERD trước chưa mô tả đầy đủ dữ liệu/API của chúng.

Các sơ đồ gom các use case liên quan thành luồng nghiệp vụ. Không phải 65 use case đều cần một sequence diagram riêng. Các mục P về xuất báo cáo, cấu hình và sao lưu chưa được xem là luồng triển khai đã xác nhận.

## Đọc kiến trúc ba lớp

- Trong các sơ đồ backend: Client -> Router -> Service -> Repository -> MongoDB.
- Router nhận HTTP, xác thực phiên qua dependency và kiểm tra hình dạng dữ liệu.
- Service kiểm tra quyền nghiệp vụ, trạng thái và các quy tắc xử lý.
- Repository thực hiện đọc/ghi và transaction; tránh truy cập MongoDB trực tiếp từ Router.
- Các cột API trong sơ đồ phía client đại diện ranh giới FastAPI đã gộp Router/Service; chi tiết được thể hiện ở sơ đồ backend tương ứng.
- Sơ đồ worker không có HTTP Router vì được kích hoạt bằng tác vụ nền. Worker và Audio Service được gộp để giữ sơ đồ dễ đọc.
- Ở sơ đồ AI, client được lược bỏ: điểm bắt đầu là request đã đến Router.

## Những quyết định cần giữ khi triển khai

1. GPS và hàng chờ phát audio nằm ở client. Backend không phải nhận mọi tọa độ để quyết định phát.
2. Nội dung offline chỉ dùng được khi tài nguyên đã có. Local TTS không được giả định luôn có giọng phù hợp.
3. Kết quả tải hoặc tạo audio phải kiểm tra request token/ngôn ngữ/phiên bản trước khi dùng để tránh phát nội dung cũ.
4. QR offline chỉ biết snapshot cục bộ và thời hạn đã lưu; không biết tức thì trạng thái vô hiệu hóa ở server.
5. Gói offline được tải vào staging và kiểm tra checksum. Chỉ đổi active pointer khi đủ tài nguyên. Cache API và IndexedDB không mặc định cùng một transaction.
6. Audio jobs cần trạng thái bền vững. Nếu dùng Celery/Redis, broker vận chuyển task ID; MongoDB vẫn có thể giữ snapshot/trạng thái phục hồi.
7. Lease, heartbeat, idempotency, version và dấu dirty/generation trong sơ đồ là các chi tiết thiết kế đề xuất. Cần bổ sung field/index/repository phù hợp; không phải các field đã được trích xuất từ HTML.
8. Với idempotency: cùng key và cùng payload trả lại kết quả cũ; cùng key nhưng payload khác bị từ chối. Việc lưu kết quả phải đồng bộ với tác động nghiệp vụ.
9. MongoDB transaction nhiều document cần môi trường hỗ trợ transaction, thường là replica set hoặc cluster Atlas phù hợp. MongoDB standalone không đáp ứng điều kiện này.
10. Không giữ transaction mở trong lúc gọi dịch/TTS/AI hoặc upload file. Gọi dịch vụ bên ngoài và transaction metadata là các giai đoạn tách biệt.
11. Khi task cũ hoàn tất muộn, không được ghi đè nội dung mới. Cleanup phải kiểm tra file không còn tham chiếu trước khi xóa.
12. Đăng nhập, quyền thực tế, xác minh owner và quyền sở hữu vẫn phải kiểm tra phía server. Đăng ký thành công không tự cấp quyền chủ quán đã xác minh.
13. Duyệt submission không đồng nghĩa công bố ngay: HTML còn có điều kiện tiếng Anh/audio readiness.
14. Analytics phải tôn trọng sự đồng ý. Retry dùng cùng event ID, client xử lý ACK theo từng sự kiện.
15. Read model tổng hợp có độ trễ. Worker ghi lại kết quả theo kỳ và kiểm tra generation/lease để không mất sự kiện đến sau hoặc ghi đè kết quả mới.
16. Thời gian nghe trung bình và theo dõi tuyến lấy từ yêu cầu ban đầu; cần thiết kế payload và mẫu số rõ ràng. Không đồng nhất thiết bị/phiên với số người.
17. Bộ mã này không sửa database, không triển khai worker, không gọi dịch vụ AI/TTS thật và không lưu thay đổi vào workspace Eraser.

## Giả định theo từng luồng

### 01_khoi_dong_va_dong_bo — Mở ứng dụng và nạp nội dung đa ngôn ngữ

- API là ranh giới FastAPI; chi tiết Router, Service, Repository được tách ở sơ đồ backend.
- Cache gồm IndexedDB cho snapshot và Cache API cho tài nguyên theo hướng PWA của HTML.
- ETag chỉ được gửi khi client còn snapshot tương ứng với đúng ngôn ngữ. Các quyết định về request token và merge được đề xuất để tránh dữ liệu cũ ghi đè.

### 02_dang_nhap — Đăng nhập qua ba lớp FastAPI

- Web ở đây là portal admin hoặc chủ quán, không phải yêu cầu đăng nhập của khách du lịch.
- Repository có thể đọc cả admin_users và roles. Kiểm tra mật khẩu, trạng thái tài khoản và tạo token nằm trong Service.
- Đây là luồng cookie cho PWA; tên hàm và cách tách repository là thiết kế đề xuất.

### 03_them_sua_poi — Admin thêm hoặc sửa POI và tạo yêu cầu audio

- Người thực hiện đã đăng nhập và có quyền tạo hoặc sửa POI.
- Đề xuất lưu POI, version và yêu cầu audio bền vững trong một transaction; không giả định hàng chờ chỉ nằm trong RAM.
- Transaction nhiều document cần MongoDB có hỗ trợ transaction. Sơ đồ này mô tả thiết kế cần triển khai, không xác nhận code HTML đã làm đúng toàn bộ.
- expected version, idempotency key và trạng thái kích hoạt là các cơ chế được cụ thể hóa trong mô hình; đổi nội dung tiếng nói cần chuẩn bị lại audio.
- Bản ghi idempotency là đề xuất bổ sung; phải cùng transaction với POI và tác vụ. Cùng key nhưng payload khác phải bị từ chối.

### 04_gps_tu_dong_thuyet_minh — Tự động thuyết minh khi đến gần POI

- Geofence và Narration chạy trong client; không gửi mọi tọa độ lên backend để quyết định phát.
- API gộp việc cung cấp metadata và tài nguyên audio tại ranh giới HTTP; triển khai thật có thể tải audio từ URL storage riêng.
- Cooldown, debounce và ưu tiên theo cấu hình. Chỉ xử lý nội dung khi mục đã đến lượt phát.
- Nếu local TTS không có giọng đã cài phù hợp, phải báo thiếu nội dung, không hứa TTS luôn hoạt động offline.
- Kết quả tải chỉ được phát nếu request token và ngôn ngữ vẫn còn hiệu lực.

### 05_quet_qr — Quét QR để nghe thuyết minh

- QR là yêu cầu ban đầu; HTML chưa mô tả API hoặc collection QR đầy đủ.
- Chỉ chấp nhận QR thuộc định dạng/miền được ứng dụng hỗ trợ; mã được ánh xạ sang POI, không gọi tùy ý URL lạ.
- Offline chỉ biết trạng thái QR từ snapshot đã lưu và thời hạn cục bộ; không thể bảo đảm biết ngay việc vô hiệu hóa từ server.
- Narration tiếp tục xử lý chọn nguồn và hàng chờ như sơ đồ 04, bỏ qua điều kiện khoảng cách GPS.

### 06_tai_goi_offline — Tải và kích hoạt gói offline

- API manifest và nguồn tài nguyên được biểu diễn theo vai trò; URL cụ thể phụ thuộc triển khai.
- Gói phải ghim version và checksum. Dữ liệu chưa được kiểm tra nằm trong staging, không được gắn thành gói đang dùng.
- Cache API và IndexedDB không được giả định cùng một transaction; chỉ đổi active pointer sau khi tài nguyên và metadata đã sẵn sàng.
- Khi lỗi, giữ gói đang hoạt động. Có thể giữ staging hợp lệ để tiếp tục tải với cùng manifest fingerprint.

### 07_worker_dich_va_tts — Worker tạo audio và lưu kết quả an toàn

- Worker và Audio Service được gộp một cột; broker có thể là Celery/Redis hoặc cơ chế task manager, không bị khẳng định là bắt buộc.
- Bắt đầu khi worker nhận được task ID; MongoDB giữ trạng thái bền vững. Claim bằng lease và heartbeat là thiết kế đề xuất.
- Cột Dịch vụ dịch và TTS gộp các API cung cấp nội dung để sơ đồ có tối đa 5 lifeline.
- Audio được lưu ở storage; MongoDB lưu metadata và trạng thái. Việc commit cần kiểm tra version đầu vào và task còn được phép hoàn tất.
- Cleanup phải kiểm tra tài nguyên không còn được tham chiếu trước khi xóa; lỗi ghi không được mặc định đồng nghĩa transaction chưa commit.
- Mọi lệnh ghi trạng thái retry hoặc hoàn tất phải kiểm tra lease còn thuộc worker và tác vụ chưa bị hủy.

### 08_dang_ky_chu_quan — Đăng ký chủ quán chờ xác minh

- Đăng ký là luồng công khai; tạo tài khoản không đồng nghĩa được phép quản lý POI.
- Unique email phải được kiểm tra bằng index, không chỉ bằng thao tác tìm trước khi insert.
- Tạo user và hồ sơ đăng ký trong cùng transaction là thiết kế đề xuất cần MongoDB hỗ trợ transaction.
- PII nếu được thu thập được mã hóa ở Service theo mô tả HTML; không trả password hash hoặc dữ liệu nhạy cảm trong response.

### 09_chu_quan_gui_noi_dung — Chủ quán gửi nội dung chờ kiểm duyệt

- Đã đăng nhập là tiền điều kiện; phía server vẫn phải kiểm tra owner đã xác minh và quyền sở hữu.
- Những thay đổi thuộc phạm vi kiểm duyệt được lưu thành submission, không sửa trực tiếp nội dung công khai.
- Một mã yêu cầu ổn định khi retry giúp tránh tạo hai submission; cần thiết kế index hoặc bản ghi idempotency phù hợp.

### 10_admin_kiem_duyet — Admin xét duyệt hồ sơ hoặc nội dung chủ quán

- Reviewer đã đăng nhập và có quyền tương ứng; trạng thái hiện hành vẫn được kiểm tra tại thời điểm ghi.
- Nhánh hồ sơ đăng ký và nhánh submission là hai nghiệp vụ thay thế, không phải lúc nào cũng thực hiện cả hai.
- Thông báo được lưu trong ứng dụng; owner đọc ở lần tải portal tiếp theo theo điều kiện xác minh, không giả định có email hoặc SMS.
- POI được duyệt chưa nhất thiết công khai ngay: còn điều kiện English/audio readiness và activation_requested.

### 11_ghi_nhan_analytics — Ghi nhận và đồng bộ thống kê có chống trùng

- App và outbox cục bộ được gộp một cột để giữ đủ ba lớp backend trên sơ đồ.
- Dùng event ID ổn định cho mỗi sự kiện. Client chỉ bỏ các sự kiện server xác nhận hoặc từ chối vĩnh viễn, không xóa cả batch khi mới gửi.
- Đề xuất upsert event và đánh dấu kỳ cần tổng hợp trong cùng transaction; tránh insert trùng gây lỗi transaction rồi bỏ sót cập nhật.
- Rate limit có thể dùng Redis trong Service; chi tiết Redis được lược khỏi sơ đồ.
- Các thông số thời gian nghe nằm trong payload sự kiện; phải kiểm tra và không cộng lặp các giá trị tích lũy khi retry.

### 12_tong_hop_thong_ke — Worker tổng hợp dữ liệu cho dashboard

- Job có lease và thế hệ dữ liệu cần xử lý là thiết kế đề xuất để không mất sự kiện đến trong lúc đang tổng hợp.
- Kết quả của một kỳ được ghi đè có kiểm soát thay vì cộng lại toàn bộ khi retry.
- Cần đọc snapshot nhất quán hoặc mốc dữ liệu xác định. Commit phải kiểm tra lease và không ghi đè kết quả của worker mới hơn.
- Nếu có sự kiện mới, job vẫn còn dirty và tiếp tục được xử lý; không xóa dấu dirty bằng kết quả cũ.
- Số liệu dashboard có độ trễ tổng hợp, không phải mọi thay đổi xuất hiện ngay lập tức.

### 13_xem_thong_ke — Admin hoặc chủ quán xem thống kê đúng phạm vi

- Chủ quán chỉ được đọc chỉ số cho POI thuộc mình và phải có quyền view_own; Admin cần quyền analytics tương ứng.
- Kho dữ liệu tổng hợp được chuẩn bị bởi sơ đồ 12. Không mặc định mỗi request phải quét mọi sự kiện.
- Chỉ số online từ Redis nếu triển khai được lấy qua adapter ở Service, lược khỏi sơ đồ MongoDB này.
- Xuất báo cáo, cấu hình và sao lưu vẫn là các mục P cần chốt, không được khẳng định đã có luồng triển khai.
- Thời gian nghe trung bình lấy từ yêu cầu ban đầu; các field/chỉ số cụ thể cần bổ sung khi triển khai.

### 14_tham_gia_tour — Chọn tour và bắt đầu hoặc kết thúc chuyến đi

- Tour thuộc yêu cầu ban đầu, chưa có schema đầy đủ trong ERD bám HTML trước đó; cần bổ sung khi triển khai.
- Chức năng tham quan vẫn hoạt động khi không đồng ý analytics; phiên thao tác có thể giữ cục bộ.
- App và outbox được gộp trong cột Ứng dụng. Sự kiện tour được đồng bộ theo sơ đồ 11.
- Phát theo POI sử dụng sơ đồ GPS hoặc nghe chủ động; không bắt buộc phát liên tục cả tour khi bắt đầu.

### 15_ai_goi_y_mo_ta — AI gợi ý mô tả với kiểm tra quyền và hạn mức

- Sơ đồ bắt đầu sau khi Router nhận request từ portal đã xác thực; bỏ lifeline client để giữ đủ Service, Repository, MongoDB và provider.
- Owner phải được xác minh, có quyền với tài nguyên và còn hạn mức. Admin có chính sách hạn mức riêng theo mô tả HTML.
- Đề xuất nhận hạn mức nguyên tử trong MongoDB, không tách thao tác đọc count và tăng count thiếu điều kiện.
- Gateway hoặc provider dự phòng được gộp một cột; weather context là nhánh tùy cấu hình, không phải điều kiện bắt buộc.
- Kết quả AI là gợi ý; không tự ghi đè hoặc xuất bản POI. Chính sách tính/hoàn quota khi provider lỗi phải được chốt lúc triển khai.

## Nguồn

- File đính kèm system-presentation-standalone(1).html và mô tả ban đầu của nhóm.
- Eraser Sequence Diagram: https://docs.eraser.io/sequence-diagram-syntax
- Mermaid Sequence Diagram: https://mermaid.js.org/syntax/sequenceDiagram.html
- MongoDB transaction considerations: https://www.mongodb.com/docs/manual/core/transactions-production-consideration/

## Kiểm tra

Đã kiểm tra ID, đầu nối, số lifeline và cấu trúc nhánh của mô hình sinh mã. Chưa render trực tiếp bằng Eraser hoặc bằng engine Mermaid.
