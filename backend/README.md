# Tour Guide Backend (FastAPI & MongoDB)

Hệ thống Backend REST API cho dự án Tour Guide sử dụng **FastAPI** và cơ sở dữ liệu **MongoDB** (driver bất đồng bộ `motor`).

## Cấu trúc thư mục

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py          # Xác thực Admin (Register, Login, Me)
│   │       │   ├── pois.py          # Quản lý POI (Điểm tham quan)
│   │       │   ├── tours.py         # Quản lý Tours (Lộ trình & Điểm dừng)
│   │       │   ├── languages.py     # Danh sách ngôn ngữ hệ thống
│   │       │   └── health.py        # Health check & kết nối MongoDB
│   │       └── router.py            # Gom nhóm router v1
│   ├── core/
│   │   ├── config.py                # Pydantic Settings đọc .env
│   │   ├── database.py              # Quản lý vòng đời kết nối Motor MongoDB
│   │   └── security.py              # JWT & Bcrypt băm mật khẩu
│   ├── schemas/                     # Pydantic models cho request & response
│   └── main.py                      # Khởi tạo FastAPI App, CORS middleware
├── .env                             # Cấu hình môi trường hiện tại
├── .env.example                     # Mẫu cấu hình môi trường
├── requirements.txt                 # Danh sách package Python
└── run.py                           # Script khởi động nhanh server
```

## Hướng dẫn chạy

### 1. Kích hoạt môi trường ảo (Virtual Environment)

Môi trường ảo `.venv` đã được tạo sẵn trong thư mục `backend`:

Trong PowerShell:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

*(Nếu gặp lỗi script disabled trong PowerShell, chạy: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

### 2. Cài đặt thư viện (nếu cần cập nhật thêm)

```powershell
pip install -r requirements.txt
```

### 3. Khởi động Backend

```powershell
python run.py
```

hoặc bằng lệnh `uvicorn`:
```powershell
uvicorn app.main:app --reload --port 8000
```

### 4. Truy cập tài liệu API tự động

- **Swagger UI (tương tác trực tiếp)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (tài liệu chi tiết)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
