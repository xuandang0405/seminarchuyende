# Triển khai TourVoice Quận 4

Bản phát hành dùng một Web App cho du khách, chủ sạp và quản trị viên. Máy chủ Linux cần Docker Engine, Docker Compose v2 (có `up --wait`), Bash, curl, Python 3 và OpenSSL. Docker cần truy cập kho ảnh và kho gói để build lần đầu. Chạy các lệnh tại thư mục vừa giải nén.

## Demo báo cáo qua SSH

```bash
tar -xzf tourvoice-web-deploy.tar.gz
cd tourvoice-web
bash deploy/scripts/deploy.sh demo
bash deploy/scripts/deploy.sh admin-demo
```

Lệnh demo tạo khóa riêng, khởi động Nginx, API, MongoDB replica set và worker. Bản demo có ba địa điểm Quận 4, một tour giá mô phỏng và audio mẫu Việt/Anh để thử tải ngoại tuyến. Mật khẩu admin được nhập trực tiếp trên server. Chủ sạp đăng ký tại trang đăng nhập quản trị, sau đó admin duyệt. Khách đăng ký từ cẩm nang.

Trên máy dùng để trình diễn, mở tunnel (thay thông tin SSH bằng máy chủ của bạn):

```bash
ssh -N -L 8080:127.0.0.1:8080 user@server
```

Mở [cẩm nang](http://localhost:8080/client/), [đăng nhập quản trị](http://localhost:8080/admin/login) và [cổng chủ sạp](http://localhost:8080/owner/). Giữ terminal SSH mở. Dùng URL localhost để trình duyệt có thể cấp quyền GPS và đăng ký service worker. Mở cửa sổ ẩn danh cho khách để tránh dùng chung phiên đăng nhập admin. Dữ liệu demo nằm trong volume của project `tourvoice-demo`.

## Máy chủ công khai qua HTTPS

```bash
cp deploy/env/.env.production.example deploy/env/.env.production
chmod 600 deploy/env/.env.production
nano deploy/env/.env.production
bash deploy/scripts/deploy.sh up
bash deploy/scripts/deploy.sh admin
```

Điền tên miền HTTPS ở các URL và TRUSTED_HOSTS, tạo hai khóa riêng theo hướng dẫn trong mẫu, cấu hình SMTP và cổng thanh toán thật tương ứng với phương thức sử dụng. Nếu dùng VNPAY thật, đặt thêm `VNPAY_PAY_URL` và `VNPAY_API_URL` do merchant cấp. Thêm khóa Google OAuth hoặc Gemini nếu sử dụng. Chỉ reverse proxy HTTPS trên máy chủ được đưa cổng 8080 ra ngoài. Ví dụ phần cấu hình Nginx trong server block HTTPS:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_read_timeout 90s;
    client_max_body_size 50M;
}
```

Chạy `bash deploy/scripts/smoke-test.sh https://ten-mien-cua-ban` sau khi bật HTTPS. Tạo hoặc nhập danh mục địa điểm và tour trước khi mở cho du khách. MongoDB và media dùng volume theo project `tourvoice`. Dữ liệu máy phát triển, tài khoản và cấu hình bí mật cần chuyển riêng nếu muốn giữ lại dữ liệu cũ.

## Vận hành

Xem trạng thái bằng `docker compose -p tourvoice -f deploy/docker-compose.prod.yml ps` và log bằng `docker compose -p tourvoice -f deploy/docker-compose.prod.yml logs --tail 100 backend worker reverse-proxy`. Với demo, dùng project `tourvoice-demo` và đặt `TOURVOICE_ENV_FILE=./env/.env.demo` trước các lệnh Compose. Dùng `TOURVOICE_PORT` nếu cổng loopback 8080 đã bận. Giữ nguyên project name, khóa và các volume khi cập nhật.
