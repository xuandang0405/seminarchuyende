# Prompt cập nhật đồ án theo Focused Use Cases

> Dùng sau `MASTER_PROMPT_TOUR_GUIDE.md`, trên repository đang làm. Gửi kèm file `FocusedUseCases.doc` và mã các sơ đồ hiện có nếu có. Đây là yêu cầu cập nhật tiếp, không phải yêu cầu xây dựng lại dự án.

## 1. Nhiệm vụ của AI

Đọc prompt tổng thể, tài liệu mới và trạng thái repository. Cập nhật hồ sơ phân tích, mã sơ đồ và những phần code thực sự thiếu để hệ thống Thuyết minh Du lịch Đa ngôn ngữ có đặc tả use case rõ ràng, kiểm chứng được và thống nhất với implementation.

Giữ stack: React web, React Native mobile, FastAPI ba lớp Router → Service → Repository, MongoDB server và SQLite/file storage cho offline mobile. Giữ phạm vi nhóm 4 người, 10 tuần và các lựa chọn đã chốt trong master prompt.

**Nếu có thay đổi tên, actor, mục tiêu, phạm vi hoặc quan hệ của use case, phải trực tiếp sửa mã nguồn sơ đồ use case tương ứng. Không chỉ viết rằng “cần cập nhật sơ đồ”.** Cập nhật cả bản Eraser và PlantUML đang được duy trì; cập nhật những định dạng khác nếu repository thực sự sử dụng chúng.

Thực hiện đến hết phần được phép và có đủ dữ liệu: đọc → phân tích khác biệt → cập nhật đặc tả → cập nhật mã sơ đồ → sửa implementation khi cần → kiểm tra → bàn giao diff. Không dừng ở một kế hoạch hoặc hỏi lại sau từng file.

## 2. Hiểu đúng tài liệu mới

`FocusedUseCases.doc` là tài liệu mẫu của **Course Cast**, gồm 5 use case:

- UC1: Maintain Planned Course Work.
- UC2: Generate Course Offerings.
- UC3: Generate Statistics Report.
- UC4: Generate Student Report.
- UC5: Login Authentication.

Tài liệu trình bày actor, maturity, summary, luồng chính theo Actor Action/System Response, Alternative Paths, Exception Paths, Extension Points, Triggers, Assumptions, Preconditions, Post Conditions, tham chiếu Business Rules, tác giả/ngày và Activity Diagram. Có lịch sử phiên bản và ví dụ liên kết actor với use case đăng nhập.

**Ý nghĩa áp dụng:** học cách đặc tả và liên kết tài liệu; không đưa nghiệp vụ học phần vào sản phẩm du lịch. File này không tự bổ sung yêu cầu về framework, MongoDB, tính năng du lịch mới hoặc tiêu chí bắt buộc của giảng viên.

### Bảng áp dụng

| Nội dung tài liệu mẫu | Áp dụng cho đồ án | Tác động mặc định |
|---|---|---|
| ID, tên, actor, maturity, summary | Chuẩn hóa hồ sơ từng UC đang có | Tài liệu |
| Actor Action / System Response | Làm rõ ai làm gì và hệ thống phản hồi thế nào | Tài liệu; sửa code khi phát hiện hành vi thiếu |
| Alternative Paths | Viết nhánh offline, fallback ngôn ngữ, từ chối duyệt, hủy thao tác | Đặc tả, sơ đồ liên quan và test |
| Exception Paths | Viết mất quyền, mạng/provider lỗi, thiếu dung lượng, version conflict | Đặc tả, UI/API/service và test nếu chưa đúng |
| Trigger, precondition, postcondition | Phân biệt lúc bắt đầu, điều kiện sẵn có và kết quả thực tế | Đặc tả và kiểm tra điều kiện |
| Business Rules | Đặt mã quy tắc và liên kết đến UC, code, test | Tài liệu quy tắc; không tự tạo collection MongoDB |
| Activity Diagram đi kèm | So khớp các nhánh với AD01–AD16 | Sửa mã activity khi hành vi thay đổi |
| Lịch sử phiên bản | Theo dõi thay đổi mô hình và lý do | Changelog và mapping ID |
| In báo cáo, Reset kế hoạch học tập | Chỉ là ví dụ trong miền Course Cast | Không tự thêm chức năng vào đồ án |

### Những điểm không được sao chép máy móc

- Không đổi actor của đồ án thành Student, Advisor hoặc Administration Representative; không đổi định danh thành UNFID.
- Không đánh số lại các UC của đồ án thành UC1–UC5. Giữ Txx, Nxx, Fxx, Uxx, Oxx, Cxx, Sxx đã thống nhất.
- Không yêu cầu khách du lịch đăng nhập chỉ vì ví dụ Course Cast gọi Login Authentication trong nhiều luồng.
- Không sao chép chính sách đăng nhập không giới hạn số lần thử. Giữ password hashing, rate limit và thông báo lỗi phù hợp của dự án.
- Không mặc định tạo `include` đến U01 cho mọi chức năng có bảo vệ. Phiên hợp lệ thường là precondition; service vẫn kiểm tra quyền khi xử lý.
- Không biến mọi kiểm tra dữ liệu thành một use case hoặc `extend`. Một bước validation thường là hành vi nội bộ gắn Business Rule.
- Không sao chép số bước không nhất quán. Ví dụ UC3 trong mẫu dùng lại số 6; dự án phải có mã bước duy nhất.
- Không sao chép mốc quay lại khi Cancel/Reset làm hậu điều kiện mâu thuẫn. Hủy bản sửa chưa lưu không được thông báo đã lưu thành công.
- Không coi “Maturity: Focused” là đã code hoặc đã chạy test. Đây là mức hoàn thiện đặc tả, tách khỏi implementation status.
- Không coi “None” trong mẫu là lý do bỏ qua lỗi thực tế của GPS, mạng, storage, quyền hoặc xử lý đồng thời.

## 3. Đầu vào và thứ tự đối chiếu

Đọc những nguồn thực sự có trong workspace:

1. `MASTER_PROMPT_TOUR_GUIDE.md` và tài liệu quyết định mới hơn đã được người dùng xác nhận.
2. `FocusedUseCases.doc` để lấy cấu trúc đặc tả. Khi đọc file Word, trích cả bảng và kiểm tra sơ đồ nhúng nếu công cụ hỗ trợ.
3. Catalog 65 UC, mã use case Eraser/PlantUML, 15 SD và 16 AD đã có.
4. ERD gốc 22 collection, schema-additions, migration/index, DTO, repository và database contract đang áp dụng.
5. Code web/mobile/backend/worker, test và trạng thái triển khai hiện tại.

Nếu có ZIP sơ đồ, giải nén để làm việc với file nguồn. Nếu code nguồn sơ đồ đã ở repository, sửa bản đó; không tạo một bản khác khiến nguồn cũ vẫn sai. Không giả định tên file cụ thể khi chưa tìm thấy.

Nếu thiếu file gốc, dùng nội dung đã nhúng trong master prompt để làm phần có căn cứ và ghi rõ nguồn chưa đối chiếu. Khi tạo một bản dựng lại do mất source, đặt nhãn `reconstructed` và ghi nguồn; không nói đã sửa chính xác một file chưa đọc được.

Tạo bảng gap analysis:

`GAP_ID | nguồn và UC | hiện trạng có bằng chứng | điểm thiếu/mâu thuẫn | loại thay đổi | tác động code/schema/sơ đồ/test | cách xử lý | trạng thái`.

Phân loại thay đổi thành:

- **DOC**: bổ sung cách mô tả, không đổi nghiệp vụ.
- **MODEL**: sửa actor, ranh giới, mức mục tiêu hoặc quan hệ UC.
- **BEHAVIOR**: làm code đúng yêu cầu đã có hoặc cụ thể hóa một quy tắc còn thiếu.
- **SCOPE_PROPOSAL**: ý tưởng chức năng mới chưa được yêu cầu; ghi backlog, không tự coi là bắt buộc.

Tài liệu mới mặc định tạo nhu cầu DOC/MODEL, không đủ để tự mở rộng scope. S10 xuất báo cáo, S12 cấu hình quản trị và S13 sao lưu/khôi phục qua chức năng quản trị vẫn là P theo master prompt, trừ khi người dùng có chỉ dẫn mới rõ ràng.

## 4. Mẫu Focused Use Case bắt buộc

Lập một template và sử dụng nhất quán. Đây là schema tài liệu, không phải yêu cầu tạo bảng database.

### Thông tin nhận diện

- **Use Case ID:** mã hiện có, ví dụ T11.
- **Use Case Name:** động từ + mục tiêu, tránh tên lớp/hàm.
- **Module/System Boundary:** phạm vi hệ thống đang mô hình hóa.
- **Primary Actor:** tác nhân có mục tiêu; trường hợp subflow nội bộ ghi rõ UC gọi, không bịa người dùng mới.
- **Supporting Actors:** dịch vụ/hệ thống ngoài ranh giới thực sự cần thiết.
- **Maturity:** Draft/Focused theo mức hoàn chỉnh tài liệu.
- **Implementation Status:** chưa làm/đang làm/đã code/đã kiểm tra/bị chặn; có bằng chứng.
- **Scope:** H/G/P; user-goal/supporting-subflow/internal-processing nếu cần phân tầng.
- **Summary/Goal:** giá trị và kết quả người dùng muốn nhận, 2–4 câu.
- **Version/Change Reference:** version hồ sơ và mã thay đổi.

### Điều kiện và quy tắc

- **Trigger:** sự kiện bắt đầu cụ thể.
- **Preconditions:** điều kiện đã đúng trước khi bắt đầu. Không dùng precondition để che một nhánh lỗi nằm trong phạm vi.
- **Assumptions:** giả định môi trường/phạm vi, không thay cho validation.
- **Success Postconditions:** kết quả sau khi thực sự đạt mục tiêu; tách accepted/queued khỏi completed với luồng bất đồng bộ.
- **Minimum Guarantees:** điều gì vẫn đúng khi hủy/lỗi, ví dụ không công bố nhầm POI hoặc không làm mất pack active.
- **Business Rules:** tham chiếu mã BR; không chép các số 2.1/2.7 của Course Cast.

### Basic Course of Events

Viết thành bảng:

`Step ID | Actor Action | System Response | BR/nhánh liên quan`.

- Mã bước dạng `T11.B1`, `T11.B2`; mỗi mã chỉ xuất hiện như định nghĩa đúng một lần.
- Tách hành động và phản hồi; nếu một ô không có hành động phù hợp thì ghi “—”, không bịa một thao tác người dùng.
- Mô tả nghiệp vụ và kết quả quan sát được. Chi tiết Router/Service/Repository nằm ở implementation mapping, không làm bảng nghiệp vụ thành call stack.

### Alternative Paths

Mỗi nhánh có ID như `T11.A1`, bước bắt đầu, điều kiện, các bước con, điểm quay lại chính xác hoặc kết thúc riêng và hậu điều kiện. Không viết “quay về bước trước”.

Offline hợp lệ, fallback đã cho phép hoặc quyết định từ chối duyệt có thể là alternative hợp lệ, không mặc định là lỗi hệ thống.

### Exception Paths

Mỗi nhánh có ID như `T11.E1`, bước phát sinh, nguyên nhân/điều kiện, phản hồi, retry/hủy và trạng thái dữ liệu sau lỗi. Thông báo UI phải phù hợp; không trả stacktrace cho người dùng.

Với kết quả commit chưa rõ, quy định xác minh trạng thái hoặc retry idempotent. Không cam kết “database chưa đổi” chỉ vì client bị timeout.

### Extension Points

Chỉ khai báo khi mô hình thật sự có use case mở rộng tại một điểm của UC cơ sở. Ghi tên điểm, mã bước trong UC cơ sở, guard, UC mở rộng và kết quả sau khi trở lại. Nếu không có, ghi “Không có extension point được mô hình hóa riêng”.

Không đánh đồng trường “Extension Points” trong tài liệu mẫu với mọi helper function hoặc bước kiểm tra dữ liệu.

### Truy vết và nghiệm thu

- SD/AD liên quan và các bước/nhánh tương ứng.
- UI screen/component, endpoint và DTO liên quan.
- Service, repository, collection; trường đọc/ghi; transaction hoặc điều kiện version nếu có.
- Acceptance criteria dạng Given/When/Then; liên kết đến test hoặc bước kiểm tra thiết bị.
- Tác giả/người review khi có thông tin thật; không bịa tên thành viên hay kết quả duyệt.
- Lịch sử chỉnh sửa và câu hỏi mở còn ảnh hưởng tới triển khai.

## 5. Phạm vi đặc tả và thứ tự làm

Giữ catalog hiện có: T01–T13, N01–N02, F01–F08, U01–U03, O01–O10, C01–C16, S01–S13. Đây là baseline 65 ID, không phải yêu cầu ép mọi phiên bản tương lai luôn có đúng 65 oval.

Đợt đầu viết kỹ các UC rủi ro cao: U01, C01/C02, C06/C07, O01/O05, T08/T09/T11, N01/N02, F02/F07/F08, T13, C11/C13, C14, S05/S07 và O10. Tiếp tục hoàn thiện đặc tả ngắn gọn nhưng đầy đủ cho các UC H/G còn lại.

N01/N02 và các xử lý nền có thể nằm ở mức supporting subflow; không ép thành mục tiêu độc lập của một người dùng. Giữ ID và liên kết tới UC gọi để không phá traceability.

Đối với P: ghi phạm vi đang chờ chốt, câu hỏi mở và việc chưa đưa vào implementation; không tự viết tiêu chí như đã cam kết triển khai.

Nếu gộp, tách hoặc đổi tên UC:

- Ưu tiên giữ ID khi mục tiêu không đổi.
- UC mới chỉ được cấp ID mới khi có mục tiêu/phạm vi mới rõ ràng.
- Không tái sử dụng ID cũ cho mục tiêu khác.
- Ghi `old_id → new_id`, loại quan hệ `renamed/refined/split/merged/retired`, lý do và những nơi phải cập nhật.
- Không xóa lịch sử hoặc test đang tham chiếu ID cũ mà chưa có mapping thay thế.

## 6. Danh mục Business Rules dùng chung

Tái sử dụng quy tắc đã có trong master prompt; dùng ID hiện hữu nếu repository đã có một catalog tương đương. Bảng sau là ID đề xuất để thống nhất tài liệu, không phải thêm nghiệp vụ mới.

| BR đề xuất | Quy tắc cần đặc tả | UC tiêu biểu |
|---|---|---|
| BR-AUTH-01 | Tài khoản/phiên phải hợp lệ; kiểm tra quyền tại server | U01, C01, O05 |
| BR-OWNER-01 | Owner cần trạng thái xác minh và đúng phạm vi sở hữu | O03, O05, O09, O10 |
| BR-POI-01 | Public POI phải vượt readiness gate và không bị xóa/tắt | C04, T05, T11 |
| BR-VERSION-01 | Mutation/duyệt kiểm tra expected version | C02, C06, C07 |
| BR-IDEM-01 | Cùng key và payload không tạo tác động lặp; khác payload bị từ chối | C01, O01, O05 |
| BR-GEO-01 | Accuracy, bán kính và debounce quyết định ứng viên hợp lệ | T09 |
| BR-GEO-02 | Cooldown tự động chỉ ghi khi audio thực sự bắt đầu phát | T09, N01 |
| BR-AUDIO-01 | Một player, chống trùng và thứ tự ưu tiên nhất quán | T08, T09, T10, T11, N01 |
| BR-AUDIO-02 | Kết quả cũ sai locale/version/token không được phát | T07, N01, N02 |
| BR-AUDIO-03 | Local TTS chỉ dùng khi có văn bản và giọng phù hợp | N01, F06 |
| BR-QR-01 | QR phải thuộc định dạng hỗ trợ; online kiểm tra mã và POI | T11, C16 |
| BR-QR-02 | Offline chỉ biết mapping/thời hạn trong snapshot đã lưu | T11, F06 |
| BR-OFFLINE-01 | Verify staging xong mới activate; lỗi không phá pack cũ | F02, F03, F04 |
| BR-OFFLINE-02 | Xóa pack không xóa asset vẫn được pack khác tham chiếu | F05 |
| BR-REVIEW-01 | Một pending version chỉ có một quyết định thắng | C06, C07 |
| BR-REVIEW-02 | Chấp thuận nội dung không tự đồng nghĩa public ngay | C07, C04 |
| BR-JOB-01 | Job bền vững, claim/lease và finalize theo input hiện hành | C11, C13, N02 |
| BR-CONSENT-01 | Tham quan hoạt động khi từ chối analytics; không thu/gửi trái lựa chọn | F08, T13 |
| BR-EVENT-01 | Event ID ổn định; ACK từng mục và retry không đếm trùng | F07, S05 |
| BR-METRIC-01 | Không cộng lặp progress tích lũy; mẫu số trung bình được định nghĩa | S07, O10 |
| BR-AGG-01 | Generation mới không bị mất khi worker cũ hoàn tất | S05, S06, S07 |
| BR-AI-01 | Quota nguyên tử; AI chỉ gợi ý draft | C14, O04 |
| BR-TOUR-01 | Tour giữ thứ tự/version; phiên local không phụ thuộc analytics | T12, T13 |

Mỗi BR có nội dung, nguồn, phạm vi, tham số cấu hình, service/engine thực thi và test. Khi quy tắc đổi, cập nhật một nguồn chính rồi sửa mọi UC tham chiếu. Đừng giữ hai giá trị cooldown hoặc hai công thức trung bình khác nhau trong hai tài liệu.

## 7. Yêu cầu bắt buộc sửa mã use case

### Tìm và quản lý nguồn

- Tìm file thực tế bằng `rg --files` và tìm tên/ID UC trong source. Xác định `.puml`, mã Eraser `.txt` và định dạng khác đang dùng.
- Nếu đã có source, sửa tại chỗ và giữ lịch sử Git. Chỉ tạo thư mục mới khi chưa có nơi chuẩn, ví dụ `docs/diagrams/usecases/plantuml/` và `docs/diagrams/usecases/eraser/`.
- Nếu mã được sinh tự động, sửa model/generator chính trước rồi sinh lại output. Không sửa output để lần generate sau ghi đè mất thay đổi.
- Không chỉ sửa ảnh xuất, file PDF, ZIP hoặc đoạn code trong câu trả lời. Phải sửa file nguồn trong repository.

### Những thay đổi nào cần sửa sơ đồ

- Thêm/bỏ/đổi tên hoặc phân loại actor.
- Thêm/bỏ/gộp/tách/đổi tên UC hoặc đổi mục tiêu khiến label cũ sai.
- Thay association, generalization, include, extend, extension point hoặc system boundary.
- Chuyển UC sang nhóm/scope khác hoặc sửa nhãn đã thể hiện trong source.

Nếu chỉ làm rõ một bước/exception trong đặc tả mà không đổi phần thông tin sơ đồ biểu diễn, ghi `No semantic diagram change` cùng lý do trong changelog. Không cố thêm một oval hoặc mũi tên vô nghĩa để tạo diff. Khi nhãn hoặc quan hệ đã đổi thì bắt buộc có diff source tương ứng.

### Ranh giới và quan hệ

- Chốt ranh giới hệ thống Tour Guide gồm các ứng dụng và dịch vụ nội bộ. MongoDB, Redis và worker nội bộ không tự trở thành actor nghiệp vụ chỉ vì xuất hiện trong sequence.
- Actor là vai trò tương tác với hệ thống; dịch vụ ngoài chỉ là supporting actor khi nằm ngoài boundary và có tương tác thực sự.
- Không suy ra actor generalization chỉ từ số priority của role. Generalization cần ý nghĩa chuyên biệt hóa phù hợp.
- `include`: mũi tên từ UC bao gồm tới UC được bao gồm. Dùng khi mô hình có hành vi được chèn/tái sử dụng tại điểm gọi.
- `extend`: mũi tên từ UC mở rộng tới UC cơ sở; ghi điểm mở rộng và điều kiện áp dụng, UC cơ sở có ý nghĩa độc lập.
- Nhánh A1/E1 trong văn bản không tự đồng nghĩa một quan hệ UML `extend`.

Tham chiếu ký pháp: [OMG UML Notation Guide](https://www.omg.org/cgi-bin/doc?formal%2F03-03-10.pdf=). Các quyết định cụ thể về login, actor và việc tách subflow phải dựa vào ranh giới và mục tiêu của dự án.

### Các điểm cần rà soát cụ thể

1. U01: không include đăng nhập lại trong mọi lần tạo/sửa POI nếu use case đã bắt đầu với phiên hợp lệ.
2. T08/T09/T11: có mục tiêu kích hoạt khác nhau; dùng chung N01 nếu catalog mô hình hóa N01 là reusable subflow.
3. N02: chuẩn bị audio theo yêu cầu chỉ xảy ra khi nguồn chưa sẵn sàng; không mô hình hóa thành công việc luôn bắt buộc ở mọi lần nghe. Chọn nhánh nội bộ hoặc extension có lý do; không dùng đồng thời hai cách mâu thuẫn.
4. O05 và C07: gửi duyệt và xét duyệt là hai mục tiêu của hai vai trò, diễn ra ở thời điểm khác nhau; gửi duyệt không include việc Admin duyệt ngay trong cùng lần thực hiện.
5. C07 và C04: duyệt nội dung và công bố có liên hệ nhưng không đồng nhất; giữ readiness gate.
6. F02: các bước tải, verify và activate không tự trở thành hàng loạt mục tiêu người dùng. F03/F04/F05 có thể là mục tiêu riêng vì người dùng chủ động cập nhật/sửa/xóa gói.
7. S05/S07/O10: chia sẻ logic đọc thống kê không đồng nghĩa owner có quyền xem phạm vi admin.
8. Các lựa chọn Print trong Course Cast không tự tạo UC mới hoặc đưa S10 từ P sang bắt buộc.

### Kiểm tra source sau chỉnh sửa

- ID/alias duy nhất; mọi đầu nối tham chiếu actor/UC có thật.
- Không còn label cũ hoặc alias orphan sau rename/merge.
- Hai định dạng mô tả cùng actor, scope và quan hệ nghiệp vụ.
- Eraser dùng đúng DSL đã chọn; không dán PlantUML vào Eraser rồi khẳng định tương thích. Nếu Eraser là biểu diễn gần đúng bằng flowchart, ghi rõ điều đó.
- Chạy parser/render khi công cụ có sẵn; nếu chỉ kiểm tra tĩnh thì ghi đúng giới hạn. Không báo render thành công khi chưa chạy.
- Không thêm engine/generator hoặc dependency phức tạp chỉ để kiểm tra vài sơ đồ; ưu tiên công cụ hiện có và script kiểm tra ID/quan hệ nhỏ nếu cần.

## 8. Đồng bộ sequence, activity, database và implementation

Khi một luồng thay đổi, cập nhật đúng phạm vi chịu ảnh hưởng:

| UC/nhóm | Sơ đồ liên quan | Điểm phải khớp |
|---|---|---|
| U01 | SD02, AD02 | Điều kiện đăng nhập, lỗi và phân quyền |
| C01/C02/C04 | SD03, AD03; SD07/AD07 khi tạo audio | Idempotency, version, job bất đồng bộ, gate công bố |
| T09 | SD04, AD04, AD16 | GPS độc lập với queue; debounce/cooldown/priority |
| T11 | SD05, AD05, AD16 | Camera, online/offline, không phụ thuộc GPS |
| F02/F03/F04/F06 | SD06, AD06 | Staging, verify, activate, hủy/lỗi và giữ pack cũ |
| C09/C11/C13/N02 | SD07, AD07 | Claim, retry/cancel, lease, version và kết quả cũ |
| O01 | SD08, AD08 | User chưa xác minh và registration pending |
| O05 | SD09, AD09 | Ownership, submission, chưa cập nhật public |
| C06/C07 | SD10, AD10 | Quyết định pending/version, notification và readiness |
| F08 và thu thập sự kiện | SD11, AD11 | Consent, outbox, retry và ACK |
| S05/S06/S07/O10 | SD12/SD13, AD12/AD13 | Tổng hợp, scope và công thức |
| T12/T13 | SD14, AD14 | Tour version, session local, consent độc lập |
| C14 | SD15, AD15 | Quyền, quota và draft |
| T08/T10/N01 | AD16 và các sequence gọi Narration | Một player, điều khiển audio và kết quả phát thực tế |

Trong activity, mỗi nhánh Có/Không hoặc guard phải có đường đi rõ, điểm gộp/thoát đúng. Trong sequence, phân biệt request được nhận và task đã hoàn tất; tránh gửi phản hồi hoàn tất trước khi có kết quả. Không ép mọi UC có đúng một SD/AD riêng nếu diagram hiện có đã đủ rõ.

### Database

Tài liệu FocusedUseCases không tự yêu cầu đổi schema. Giữ 22 collection nền tảng và các phần mở rộng đã chốt trong master prompt; không thiết kế lại database.

Đặc biệt giữ `POI`, `MenuItem`, ID/reference string và `admin_users.role → roles.name`. Kiểm tra actual schema/migration trước khi chỉnh code; không chỉ dựa vào một ảnh ERD.

Không tạo collection `usecases`, `actors`, `business_rules` hoặc `alternative_paths` chỉ vì thêm các mục đó vào tài liệu. Đặc tả nằm trong repository.

Nếu một BEHAVIOR gap thực sự cần dữ liệu mới, ghi field/collection, kiểu, default, migration/index, bảo toàn dữ liệu và UC/BR chứng minh nhu cầu; cập nhật ERD và DTO tương ứng. Không tạo migration cho thay đổi chỉ thuộc DOC/MODEL.

### Code sản phẩm

Chỉ sửa phần implementation đang khác yêu cầu hoặc còn thiếu; không refactor rộng, đổi framework hoặc viết lại code đã chạy tốt. Mỗi thay đổi phải đi qua lớp đúng trách nhiệm và có kiểm tra tương ứng.

Ví dụ cần kiểm tra thực tế: form Cancel có vô tình lưu không; API review có chống hai người duyệt cùng version không; QR có bị ép quyền GPS không; client có xóa cả outbox dù chỉ một phần được ACK không. Đây là câu hỏi kiểm tra, không khẳng định trước rằng code hiện tại có lỗi.

## 9. Ví dụ Focused UC cho T11

Đây là mẫu áp dụng vào đồ án từ yêu cầu đã chốt. Khi đưa vào repository, đối chiếu implementation và điền đường dẫn/test thật; không coi mẫu là bằng chứng đã test.

**ID/tên:** T11 — Quét QR để nghe thuyết minh.

**Actor chính:** khách du lịch. **Subflow:** N01 điều phối nghe; N02 chỉ khi cần chuẩn bị nguồn. **SD/AD:** SD05, AD05, AD16.

**Trigger:** khách mở chức năng quét QR.

**Preconditions:** ứng dụng đã khởi tạo đủ để mở scanner. Không yêu cầu đăng nhập, GPS hoặc consent analytics. Camera permission được xử lý trong flow, không ghi như điều kiện đã chắc chắn có.

**Success:** QR đã được resolve theo quy tắc online/offline và thuyết minh đúng POI/ngôn ngữ hiệu lực bắt đầu phát. Nếu mới xếp hàng, trạng thái chỉ là accepted/pending, chưa gọi là đã nghe thành công.

**Minimum guarantees:** QR sai không dẫn tới gọi URL tùy ý; không mất nội dung offline tốt; không tự thu analytics khi chưa đồng ý; lỗi không làm phát kết quả của request cũ.

| Step | Actor Action | System Response | Quy tắc/nhánh |
|---|---|---|---|
| T11.B1 | Chọn Quét QR | Kiểm tra hoặc xin quyền camera | E1 |
| T11.B2 | Đưa camera vào mã | Đọc mã, kiểm tra định dạng được hỗ trợ | BR-QR-01, E2 |
| T11.B3 | — | Tạo yêu cầu nghe với locale hiện hành, kiểm tra kết nối | A1 |
| T11.B4 | — | Online: tra mã và kiểm tra hiệu lực/POI công khai | BR-POI-01, E3, E4 |
| T11.B5 | — | Chuyển POI/locale/version hợp lệ sang N01; hiện trạng thái queue | BR-AUDIO-01, A2 |
| T11.B6 | — | N01 chọn nguồn, kiểm tra token/locale/version trước phát | BR-AUDIO-02/03, E5 |
| T11.B7 | Nghe hoặc điều khiển player | Khi bắt đầu phát thật, cập nhật trạng thái; analytics chỉ qua flow có consent | T10, BR-CONSENT-01 |

**A1 — Offline:** rẽ tại B3 khi không có mạng. Tìm mapping/cache và kiểm tra thời hạn trong snapshot theo BR-QR-02. Nếu hợp lệ, nhập lại B5; nếu thiếu/hết hạn, báo cần kết nối và kết thúc, không chờ GPS. Không hứa biết ngay một mã vừa bị thu hồi ở server.

**A2 — Đang có audio:** rẽ tại B5. N01 áp dụng queue/priority; khi đủ điều kiện tiếp tục B6. GPS vẫn được xử lý độc lập. Nếu người dùng hủy yêu cầu khi chờ, loại item đúng token, kết thúc trạng thái cancelled và không cập nhật cooldown như đã phát.

**E1:** camera bị từ chối tại B1 → hướng dẫn cấp quyền hoặc quay lại; không gửi yêu cầu audio.

**E2:** định dạng sai tại B2 → thông báo mã không hỗ trợ, cho quét lại B2 hoặc thoát.

**E3:** mã inactive/hết hạn hoặc POI không public tại B4 → báo không dùng được và kết thúc; không tìm cách bỏ qua trạng thái từ server bằng cache cũ.

**E4:** request tra cứu lỗi tại B4 → cho retry có kiểm soát hoặc thoát. Chỉ chuyển sang cache khi chính sách offline đã cho phép và hiển thị đúng trạng thái; không tự coi lỗi mạng là xác nhận mã hợp lệ.

**E5:** không có nguồn đọc, lỗi phát hoặc request đã cũ tại B6 → xử lý theo N01, không phát sai nội dung và không ghi cooldown trước khi bắt đầu thành công.

**Extension points:** chưa bắt buộc tách use case mở rộng riêng; N01 là subflow dùng chung. Không tự đổi A1/A2 thành hai quan hệ extend chỉ vì có nhánh thay thế.

**Dữ liệu:** đọc `qr_codes`, `POI`, `poi_localizations`; đọc cache local khi offline. Chỉ yêu cầu job/ghi sự kiện khi nhánh N02 hoặc consent tương ứng cho phép.

**Acceptance:** QR hợp lệ hoạt động khi GPS bị từ chối; mapping cache hợp lệ hoạt động offline; mã sai không gọi URL ngoài; đổi locale giữa lúc tải không phát kết quả cũ; pending queue không được hiển thị là đã phát.

## 10. Ví dụ Focused UC cho C07

**ID/tên:** C07 — Xét duyệt nội dung chủ quán gửi.

**Actor chính:** Admin/người có quyền kiểm duyệt phù hợp. **SD/AD:** phần submission của SD10/AD10; không gộp thành xét duyệt đăng ký C06.

**Trigger:** reviewer mở submission và chọn thao tác xét duyệt.

**Preconditions:** đã có phiên đăng nhập tại thời điểm bắt đầu. Server vẫn kiểm tra hiệu lực phiên/quyền ở từng request; phiên có thể hết hạn hoặc quyền thay đổi trong lúc mở form.

**Success:** đúng submission version được ghi một quyết định; thay đổi POI được áp dụng nếu chấp thuận; thông báo và job cần thiết được ghi nhất quán. Trạng thái công bố vẫn theo readiness gate, không mặc định public.

**Minimum guarantees:** reviewer không ghi đè quyết định mới hơn; từ chối không áp dụng payload vào POI public; retry không tạo thông báo/job trùng. Nếu commit chưa rõ, đọc lại để xác minh trước khi kết luận.

| Step | Actor Action | System Response | Quy tắc/nhánh |
|---|---|---|---|
| C07.B1 | Mở submission | Kiểm tra phiên/quyền và đọc nội dung/version | BR-AUTH-01, E1 |
| C07.B2 | Xem nội dung trước/sau | Hiển thị trạng thái hiện tại và thông tin cần duyệt | E2 |
| C07.B3 | Chọn chấp thuận và nhập ghi chú | Validate quyết định và payload nghiệp vụ | A1, E3 |
| C07.B4 | Xác nhận gửi | Kiểm tra lại pending/version và version POI gốc khi có | BR-VERSION-01, BR-REVIEW-01, E4 |
| C07.B5 | — | Lưu quyết định, POI, notification và job cần thiết nhất quán | BR-IDEM-01, BR-JOB-01, E5 |
| C07.B6 | Xem kết quả | Hiển thị quyết định đã xác nhận và trạng thái sẵn sàng/công bố thực tế | BR-REVIEW-02 |

**A1 — Từ chối:** thay cho lựa chọn chấp thuận tại B3, reviewer chọn từ chối và cung cấp lý do theo quy tắc. Tiếp tục B4/B5 để lưu quyết định + notification; không áp dụng payload và không tạo job TTS cho payload bị từ chối. Kết thúc qua B6 với trạng thái rejected, không phải lỗi hệ thống.

**A2 — Hủy trước gửi:** tại B3/B4 trước khi request gửi đi, đóng form hoặc hủy quyết định; kết thúc không tạo mutation. Nếu request đã gửi, “đóng màn hình” không được hứa là hủy transaction; phải xác minh kết quả từ server.

**E1:** phiên/quyền không còn hợp lệ → dừng mutation, xử lý đăng nhập hoặc thông báo thiếu quyền; không tự động gửi lại quyết định sau đăng nhập khi chưa xác minh version.

**E2:** submission đã không còn tồn tại/không thể xem → hiển thị lỗi thích hợp, không suy diễn rằng đang pending.

**E3:** payload/ghi chú không hợp lệ → chỉ rõ vấn đề và quay về B3.

**E4:** người khác đã duyệt hoặc version thay đổi tại B4/B5 → trả conflict, tải trạng thái mới; không tự overwrite. Quyết định còn hợp lệ cần reviewer xác nhận lại trên dữ liệu mới.

**E5:** DB lỗi hoặc phản hồi timeout ở B5 → xác minh theo mã yêu cầu và trạng thái lưu; nếu cần retry thì cùng key và payload. Không gửi notification hoặc tạo job lần hai để “bù” khi chưa biết commit trước đã thành công hay chưa.

**Dữ liệu:** `poi_submissions`, `POI`, `poi_localizations` khi liên quan, `owner_notifications`, `audio_tasks`, `audit_logs`, idempotency theo thiết kế đã chốt. Không tạo collection mới chỉ để thêm mẫu Focused UC.

**Acceptance:** hai reviewer cùng version chỉ một quyết định thắng; từ chối không sửa POI; chấp thuận khi audio chưa ready chưa làm public giả; retry sau timeout không tạo tác động trùng.

## 11. Từ đặc tả sang test và code

Mở rộng traceability hiện có, không tạo bảng thứ hai mâu thuẫn:

`UC_ID | Spec Version | Flow/Step ID | BR_ID | SD/AD branch | screen | endpoint | service/engine | repository/collection | test/manual evidence | status`.

Quy tắc kiểm tra:

- Luồng chính có acceptance scenario chứng minh kết quả quan sát được.
- Nhánh A/E quan trọng có test hoặc checklist thiết bị thích hợp; không viết test unit giả cho khả năng native cần kiểm tra thật.
- Không bắt buộc mỗi câu mô tả có một test riêng. Có thể một test chứng minh nhiều step nếu mapping rõ.
- Phân biệt lỗi expected như conflict/mất mạng với lỗi implementation.
- Test cancellation kiểm tra tác động dữ liệu đúng giai đoạn, không chỉ thấy nút Cancel đóng modal.
- Test bất đồng bộ phân biệt queued/running/completed/failed/cancelled.
- Không sửa test để chấp nhận implementation sai đặc tả; nếu đổi yêu cầu, phải có change record trước.
- Không ghi “đã kiểm tra” khi mới viết test hoặc khi test bị skip vì thiếu môi trường.

Ví dụ tên liên kết: `test_T11_E3_inactive_qr_rejected`, `test_C07_E4_review_conflict`, `test_F02_download_failure_preserves_active_pack`. Dùng quy ước sẵn có nếu tương đương; không đổi toàn bộ tên test chỉ vì thêm prompt này.

## 12. File và kết quả phải bàn giao

Tái sử dụng đường dẫn hiện có khi có thể; đường dẫn dưới đây là gợi ý cho trường hợp chưa có cấu trúc tương ứng:

1. `docs/focused-usecases/README.md`: cách đọc, quy ước ID và scope.
2. `docs/focused-usecases/_template.md`: template chung.
3. Các file đặc tả như `T11-scan-qr.md`, `C07-review-submission.md`; giữ một nguồn chính cho mỗi UC.
4. `docs/business-rules.md` và bảng liên kết quy tắc.
5. `docs/usecase-gap-analysis.md`: điểm đã có/thiếu, bằng chứng và thay đổi thực tế.
6. `docs/usecase-change-log.md`: before/after, lý do, ID mapping và các source bị ảnh hưởng.
7. Source use case Eraser/PlantUML đã sửa; source SD/AD bị ảnh hưởng cũng được cập nhật.
8. `docs/requirements-traceability.md` đã mở rộng theo step/branch.
9. Diff code sản phẩm và test cho những BEHAVIOR gap thực sự được xác nhận.
10. Schema-additions/migration/ERD chỉ khi có thay đổi dữ liệu thật sự cần thiết; nếu không, ghi “không thay đổi schema”.

Changelog mỗi thay đổi có: `Change ID`, UC/BR, mô tả trước/sau, loại DOC/MODEL/BEHAVIOR/SCOPE_PROPOSAL, file đã sửa, test/kiểm tra đã chạy và phần còn chặn.

Không bắt buộc tạo ảnh hoặc document Word mới trong đợt này. Ưu tiên Markdown và mã sơ đồ version-control được. Không trả ảnh đẹp thay cho source code cần bảo trì.

## 13. Thứ tự thực hiện và điều kiện hoàn thành

1. Kiểm kê nguồn và code thực tế; đọc master prompt và tài liệu mới.
2. Viết gap analysis ngắn, phân biệt bổ sung tài liệu với thay đổi chức năng.
3. Tạo template Focused UC và catalog Business Rules.
4. Hoàn thiện nhóm UC ưu tiên; tiếp tục những UC H/G còn lại theo độ phức tạp thực tế.
5. Rà actor/include/extend, giữ hoặc sửa quan hệ theo căn cứ; ghi mapping nếu đổi ID.
6. **Trực tiếp sửa code sơ đồ use case bị ảnh hưởng**, rồi SD/AD tương ứng. Nếu không cần đổi mô hình, ghi lý do cụ thể.
7. Sửa những phần implementation thiếu so với yêu cầu đã chốt; cập nhật test và type/API contract nếu có tác động.
8. Kiểm tra consistency, parser/render khi có công cụ, test cần thiết và regression của luồng bị ảnh hưởng.
9. Bàn giao bảng file thay đổi, kết quả thực chạy, phần không thay đổi và câu hỏi mở còn thiết yếu.

Hoàn thành khi:

- Có thể lần từ mục tiêu UC → bước/nhánh → BR → sơ đồ → implementation → bằng chứng kiểm tra.
- Không có tham chiếu bước hoặc ID bị mồ côi.
- Các nhãn/actor/quan hệ đã thay đổi trong đặc tả được phản ánh ở source sơ đồ phù hợp.
- Không import nghiệp vụ Course Cast, không tự nâng P thành bắt buộc, không đổi stack/schema gốc tùy ý.
- Tài liệu nêu đúng code đang chạy và phần chưa triển khai; không che gap bằng cách mô tả tính năng như đã tồn tại.

**Bắt đầu ngay trên repository hiện tại. Trước tiên xác định source cần sửa, tạo template và gap analysis, sau đó thực hiện các cập nhật được xác nhận. Không dựng lại toàn bộ dự án từ đầu.**
