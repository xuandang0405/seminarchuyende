# Nhóm 5 - Hệ Thống Tour Guide (Thuyết Minh Tự Động)

Dự án chuyên đề xây dựng hệ thống Tour Guide thông minh với Backend **FastAPI** và cơ sở dữ liệu **MongoDB**.

## Cấu trúc dự án

```text
Seminar/
├── backend/            # Mã nguồn Backend API (FastAPI, Motor, Pydantic)
│   ├── app/            # Logic ứng dụng (Auth, POIs, Tours, Languages...)
│   ├── .env.example    # Mẫu cấu hình môi trường
│   ├── requirements.txt # Danh sách thư viện Python
│   ├── run.py          # Script khởi chạy server
│   └── README.md       # Hướng dẫn chi tiết chạy Backend
├── frontend/           # Mã nguồn Frontend (sắp triển khai)
├── init_mongodb.js     # Script khởi tạo Schema và Index cho MongoDB
└── README.md           # Tài liệu tổng quan dự án
```

## Khởi động nhanh Backend

1. Di chuyển vào thư mục `backend`:
   ```bash
   cd backend
   ```
2. Kích hoạt môi trường ảo:
   ```bash
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   ```
3. Cài đặt thư viện:
   ```bash
   pip install -r requirements.txt
   ```
4. Tạo file `.env` từ `.env.example` và điền cấu hình MongoDB.
5. Chạy server:
   ```bash
   python run.py
   ```
6. Truy cập Swagger UI tại: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
