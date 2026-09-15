# Danh mục 65 use case

H: mô hình hóa từ HTML; G: yêu cầu ban đầu; P: cần chốt phạm vi.

| ID | Use case | Nguồn | Tác nhân trực tiếp | Quy tắc / phạm vi |
|---|---|---|---|---|
| T01 | Xem bản đồ du lịch | H | Khách du lịch, Dịch vụ bản đồ cloud | Hiển thị POI và vị trí. Dịch vụ bản đồ ngoài chỉ tham gia chế độ cloud/hybrid; offline dùng tài nguyên đã tải. |
| T02 | Xác định vị trí hiện tại | H | Khách du lịch, Dịch vụ định vị thiết bị | Dùng vị trí hiện tại hoặc vị trí đã lưu còn phù hợp. Có luồng từ chối quyền/không lấy được vị trí; không bảo đảm GPS chính xác tuyệt đối. |
| T03 | Tìm kiếm địa điểm | H | Khách du lịch | Tìm POI trong dữ liệu hiện có; tìm kiếm xuất hiện trong luồng analytics của HTML. |
| T04 | Xem địa điểm gần nhất | H | Khách du lịch | Dựa trên vị trí khả dụng để xác định và làm nổi bật POI gần. |
| T05 | Xem chi tiết địa điểm | H | Khách du lịch | Tên, mô tả, ảnh, địa chỉ và nội dung theo ngôn ngữ. |
| T06 | Xem món ăn của địa điểm | H | Khách du lịch | Hiển thị MenuItem của POI khi có và người dùng muốn xem. |
| T07 | Chọn ngôn ngữ nội dung và giao diện | H | Khách du lịch | Đồng bộ lựa chọn cho thuyết minh và giao diện; HTML tách content locale và UI bundle, có fallback khi chưa sẵn sàng. |
| T08 | Nghe thuyết minh theo yêu cầu | H | Khách du lịch | Người dùng chủ động chọn nghe một POI. |
| T09 | Nghe tự động khi đến gần POI | H | Khách du lịch | Geofence chọn POI phù hợp; debounce, cooldown, ưu tiên và hàng chờ là quy tắc bên trong use case. |
| T10 | Điều khiển phát thuyết minh | G | Khách du lịch | Tạm dừng, tiếp tục, dừng hoặc tua theo khả năng trình phát. Không nhầm với điều khiển tác vụ tạo audio của admin. |
| T11 | Quét QR để nghe | G | Khách du lịch | Giải mã QR của POI và nghe mà không cần GPS; offline cần có ánh xạ QR và nội dung tương ứng đã lưu. |
| T12 | Xem và chọn tour | G | Khách du lịch | Xem danh sách POI và thứ tự của tour. |
| T13 | Bắt đầu hoặc kết thúc tour | G | Khách du lịch | Tour đã được chọn khi bắt đầu. Kết thúc phiên không bắt buộc chọn lại tour; chỉ theo dõi tuyến khi có đồng ý phù hợp. |
| N01 | Phát nội dung thuyết minh | H | Thông qua use case khác | Hành vi dùng chung cho nghe thủ công, GPS và QR. Chọn đúng ngôn ngữ, file có sẵn hoặc nguồn dự phòng; xử lý lỗi phát. |
| N02 | Chuẩn bị thuyết minh theo yêu cầu | H | Thông qua use case khác | Thử tạo nội dung khi thiếu audio phù hợp và có mạng; nếu thất bại, use case nghe dùng luồng dự phòng. Không bắt buộc gọi API khi audio đã có. |
| F01 | Chọn chế độ bản đồ | H | Khách du lịch | Cloud, Offline Pack hoặc Hybrid; phụ thuộc cấu hình và pack có sẵn. |
| F02 | Tải gói sử dụng offline | H | Khách du lịch | Gói gồm map, POI, ảnh và audio theo ngôn ngữ; kiểm tra dung lượng và checksum trước khi kích hoạt. |
| F03 | Cập nhật gói offline | H | Khách du lịch | Tải phiên bản gói mới; giữ bản đang dùng cho đến khi bản mới được kiểm tra. |
| F04 | Sửa gói offline thiếu hoặc lỗi | H | Khách du lịch | Tải lại tài nguyên thiếu/hỏng khi có mạng và còn dung lượng. |
| F05 | Xóa gói offline | H | Khách du lịch | Xóa gói đã chọn và giải phóng dung lượng. |
| F06 | Sử dụng nội dung đã tải offline | H | Khách du lịch | Xem bản đồ/POI và nghe nội dung đã có; thiếu tài nguyên không được giả định có thể tự tải khi mất mạng. |
| F07 | Đồng bộ nội dung khi có mạng | H | Khách du lịch | Ứng dụng đồng bộ full/delta và xử lý POI đã bị gỡ; việc chạy tự động không làm worker thành actor bên ngoài. |
| F08 | Cho phép hoặc từ chối thống kê | H | Khách du lịch | Public analytics chỉ thu thập sau khi đồng ý. Mã thiết bị/phiên là giả danh, không tự động bảo đảm ẩn danh hoàn toàn. |
| U01 | Đăng nhập cổng quản trị hoặc chủ quán | H | Chủ quán / người đăng ký, Quản trị viên | Khách du lịch dùng chức năng công khai không bị buộc đăng nhập. Login không được include vào mọi thao tác đã có phiên hợp lệ. |
| U02 | Đăng xuất | H | Chủ quán / người đăng ký, Quản trị viên | Kết thúc phiên đăng nhập. |
| U03 | Đổi mật khẩu | H | Chủ quán / người đăng ký, Quản trị viên | Cần đăng nhập; có kiểm tra mật khẩu và quyền thay đổi tài khoản của mình. |
| O01 | Đăng ký làm chủ quán | H | Chủ quán / người đăng ký | Luồng đăng ký công khai; tạo hồ sơ chờ xét duyệt, không tự cấp quyền chủ quán đã xác minh. |
| O02 | Xem trạng thái đăng ký chủ quán | H | Chủ quán / người đăng ký | Sau đăng nhập, tài khoản chưa xác minh vẫn xem trạng thái xét duyệt của mình. |
| O03 | Xem các địa điểm của mình | H | Chủ quán / người đăng ký | Yêu cầu chủ quán đã xác minh và kiểm tra quyền sở hữu. |
| O04 | Soạn hoặc sửa nội dung quán | H | Chủ quán / người đăng ký | Chỉ tài nguyên thuộc quyền quản lý; nội dung cần kiểm duyệt được gửi thành submission trước khi xuất bản. |
| O05 | Gửi nội dung chờ duyệt | H | Chủ quán / người đăng ký | Gửi đề nghị POI mới hoặc thay đổi POI theo phạm vi cần duyệt; không tự công bố chỉ vì gửi thành công. |
| O06 | Xem kết quả duyệt nội dung | H | Chủ quán / người đăng ký | Xem pending/approved/rejected và admin_note của submission thuộc mình. |
| O07 | Xem thông báo xét duyệt | H | Chủ quán / người đăng ký | Xem danh sách và chi tiết thông báo; portal nghiệp vụ tuân theo cổng xác minh owner. |
| O08 | Đánh dấu thông báo đã đọc | H | Chủ quán / người đăng ký | Cập nhật trạng thái thông báo thuộc tài khoản hiện tại. |
| O09 | Quản lý món ăn của quán | H | Chủ quán / người đăng ký | Theo quyền thực tế trong HTML: đọc/thêm/sửa món ăn thuộc quán mình; không mặc định cấp quyền xóa cho role owner. |
| O10 | Xem thống kê quán của mình | H | Chủ quán / người đăng ký | Chỉ số liệu liên quan đến POI thuộc quyền quản lý. |
| C01 | Thêm địa điểm | H | Quản trị viên | Thêm POI gốc và các thông tin liên quan. |
| C02 | Sửa địa điểm | H | Quản trị viên | Đổi nội dung cần làm mất hiệu lực audio cũ và chuẩn bị lại bản cần thiết trước khi công bố. |
| C03 | Xóa địa điểm | H | Quản trị viên | Kiểm tra quyền, xử lý bản dịch và tài nguyên liên quan, cập nhật phiên bản dữ liệu. |
| C04 | Bật hoặc tắt công bố địa điểm | H | Quản trị viên | Trong HTML, bật public cần nội dung tiếng Anh và audio sẵn sàng. Tắt công bố không đồng nghĩa xóa dữ liệu. |
| C05 | Quản lý món ăn | H | Quản trị viên | Đọc/thêm/sửa/xóa menu theo quyền admin. |
| C06 | Duyệt đăng ký chủ quán | H | Quản trị viên | Chấp nhận hoặc từ chối, ghi chú lý do; kết quả quyết định trạng thái xác minh. |
| C07 | Duyệt nội dung chủ quán gửi | H | Quản trị viên | Chấp nhận hoặc từ chối submission; trường hợp duyệt phải tuân thủ điều kiện nội dung công khai. |
| C08 | Nhập hoặc sửa bản dịch thuyết minh | G | Quản trị viên | Chỉnh nội dung đa ngôn ngữ bằng CMS theo yêu cầu ban đầu; HTML chủ yếu mô tả pipeline tạo bản dịch. |
| C09 | Dịch nội dung tự động | H | Quản trị viên, Dịch vụ dịch thuật | Gọi dịch vụ dịch thuật để tạo nội dung ngôn ngữ đích; có lỗi và fallback. |
| C10 | Upload file audio MP3 | G | Quản trị viên | Nguồn audio thu sẵn từ mô tả ban đầu; cần kiểm tra file và gắn đúng POI/ngôn ngữ. |
| C11 | Tạo audio bằng TTS | H | Quản trị viên, Dịch vụ TTS | Tạo giọng đọc từ văn bản bằng dịch vụ TTS; có thể được dùng lại bởi pipeline on-demand. |
| C12 | Theo dõi tác vụ tạo audio | H | Quản trị viên | Xem tiến độ và trạng thái queued/running/paused/completed/failed/cancelled. |
| C13 | Tạm dừng, tiếp tục hoặc hủy tác vụ audio | H | Quản trị viên | Chỉ các trạng thái cho phép chuyển trạng thái mới chấp nhận lệnh. |
| C14 | Dùng AI gợi ý mô tả | H | Quản trị viên, Chủ quán / người đăng ký, Dịch vụ AI, Dịch vụ thời tiết | Owner phải được xác minh, đúng quyền tài nguyên và còn hạn mức. Dịch vụ thời tiết chỉ tham gia nếu bật weather context; thiếu thời tiết có thể bỏ qua. |
| C15 | Quản lý tour và thứ tự địa điểm | G | Quản trị viên | Thêm/sửa/xóa tour, chọn các POI và thứ tự ghé thăm; thuộc mô tả ban đầu. |
| C16 | Tạo hoặc vô hiệu hóa mã QR | G | Quản trị viên | Gắn QR với POI/trạm dừng và quản lý hiệu lực; là phần hoàn thiện chức năng QR trong yêu cầu ban đầu. |
| S01 | Quản lý tài khoản | H | Quản trị viên | Đọc/thêm/sửa/xóa hoặc khóa tài khoản theo quyền và giới hạn mức quyền được giao. |
| S02 | Quản lý vai trò và bộ quyền | H | Super Admin | Dynamic roles và permission arrays. Bản mô hình giao quản trị quyền nhạy cảm cho Super Admin. |
| S03 | Gán vai trò và quyền tài khoản | H | Super Admin | Kiểm soát việc cấp quyền. HTML có quyền theo role và quyền bổ sung cho user. |
| S04 | Xem nhật ký thao tác | H | Quản trị viên | Tra cứu audit logs theo người thực hiện, thao tác, tài nguyên và thời gian. |
| S05 | Xem dashboard thống kê | H | Quản trị viên | Lượt xem, lượt nghe, tìm kiếm và số thiết bị đã đồng ý còn trong cửa sổ online; không diễn giải thành số người duy nhất. |
| S06 | Xem địa điểm được nghe nhiều | H | Quản trị viên | Top POI theo số liệu tổng hợp. |
| S07 | Xem thời gian nghe trung bình | G | Quản trị viên | Tính thời gian nghe thực tế theo POI, không cộng khoảng dừng hoặc thời gian tua. |
| S08 | Xem thống kê tuyến đã đi | G | Quản trị viên | Dựa trên phiên/tour và dữ liệu tuyến được phép thu thập; yêu cầu bổ sung thiết kế dữ liệu so với ERD HTML trước. |
| S09 | Xem bản đồ nhiệt du khách | G | Quản trị viên | Tổng hợp mẫu vị trí hợp lệ theo vùng và thời gian, theo phạm vi đồng ý và chính sách lưu dữ liệu. |
| S10 | Xuất báo cáo thống kê | P | Quản trị viên | HTML khai báo analytics:export; chưa chứng minh màn hình/luồng xuất báo cáo hoàn chỉnh. Đưa vào như phạm vi cần chốt. |
| S11 | Xem giám sát vị trí runtime | H | Quản trị viên | Chức năng runtime_observability được mô tả riêng với analytics; cần xác định rõ quyền và quy tắc thu thập, không dùng để vượt lựa chọn riêng tư. |
| S12 | Cấu hình hệ thống | P | Super Admin | Suy ra từ quyền system:config trong HTML; cấu hình cụ thể và giao diện chưa được đặc tả. |
| S13 | Sao lưu dữ liệu | P | Super Admin | Suy ra từ quyền system:backup; chưa có mô tả luồng sao lưu. Không tự bổ sung chức năng khôi phục hoặc thao tác lên DB thật. |

## Include và extend

| Nguồn mũi tên | Quan hệ | Đích mũi tên | Điều kiện |
|---|---|---|---|
| T04 | include | T02 | Hành vi dùng chung được bao gồm |
| T09 | include | T02 | Hành vi dùng chung được bao gồm |
| T08 | include | N01 | Hành vi dùng chung được bao gồm |
| T09 | include | N01 | Hành vi dùng chung được bao gồm |
| T11 | include | N01 | Hành vi dùng chung được bao gồm |
| T06 | extend | T05 | có menu và người dùng chọn xem |
| T10 | extend | N01 | đang phát hoặc tạm dừng |
| N02 | extend | N01 | thiếu audio phù hợp và có mạng |
| N02 | include | C11 | Hành vi dùng chung được bao gồm |
| C09 | extend | N02 | chưa có bản dịch ngôn ngữ đích |
| C13 | extend | C12 | người quản trị chọn điều khiển tác vụ |
| C14 | extend | O04 | chủ quán yêu cầu và còn hạn mức |
| C14 | extend | C01 | admin chọn hỗ trợ AI |
| C14 | extend | C02 | admin chọn hỗ trợ AI |
