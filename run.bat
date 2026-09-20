@echo off
setlocal enabledelayedexpansion
title TourVoice - Khoi Dong He Thong Quan 4
color 0A

echo ======================================================================
echo           HE THONG THUYET MINH DU LICH TU DONG QUAN 4
echo ======================================================================
echo.

REM 1. Xac dinh thu muc goc du an
set "BASE_DIR=%~dp0"
if exist "%BASE_DIR%backend\run.py" (
    set "PROJECT_DIR=%BASE_DIR%"
) else if exist "%BASE_DIR%seminarchuyende\backend\run.py" (
    set "PROJECT_DIR=%BASE_DIR%seminarchuyende\"
) else (
    color 0C
    echo [LOI] Khong tim thay thu muc backend cua TourVoice!
    echo Vui long dat file bat trong thu muc seminar hoac seminarchuyende.
    echo.
    pause
    exit /b 1
)

REM 2. Giai phong cac port 8000 va 5173 neu con tien trinh treo tu truoc
echo [0/3] Kiem tra va giai phong port 8000, 5173 neu bi chiem dung...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    echo [INFO] Dong tien trinh cu PID %%a tren port 8000...
    taskkill /f /pid %%a >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a >nul 2>nul
)

REM 3. Khoi tao file .env neu chua co
if not exist "%PROJECT_DIR%backend\.env" (
    if exist "%PROJECT_DIR%backend\.env.example" (
        echo [INFO] Khoi tao file .env cho backend tu .env.example...
        copy "%PROJECT_DIR%backend\.env.example" "%PROJECT_DIR%backend\.env" >nul
    )
)

REM 4. Kiem tra trinh thong dich Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py"
    ) else (
        color 0C
        echo [LOI] May tinh chua cai dat Python!
        echo Vui long cai dat Python 3.10+ va tich chon "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
)

REM Kiem tra moi truong ao virtualenv neu co
if exist "%PROJECT_DIR%backend\.venv\Scripts\python.exe" (
    set "PYTHON_EXEC=%PROJECT_DIR%backend\.venv\Scripts\python.exe"
    echo [INFO] Su dung Virtualenv: backend\.venv
) else (
    set "PYTHON_EXEC=%PYTHON_CMD%"
    echo [INFO] Su dung Python he thong: %PYTHON_CMD%
)

REM 5. Khoi chay Backend Server FastAPI (Port 8000)
echo.
echo [1/3] Dang khoi dong Backend FastAPI (Port 8000)...
set "UVICORN_RELOAD=true"
start "TourVoice_Backend" cmd /k "title TourVoice - Backend Server (Port 8000) && cd /d "%PROJECT_DIR%backend" && "%PYTHON_EXEC%" run.py"

REM 6. Kiem tra Node.js / npm de chay Frontend React Vite (Port 5173 neu co)
set "HAS_VITE=0"
where npm >nul 2>nul
if %errorlevel% equ 0 (
    if exist "%PROJECT_DIR%apps\web-admin\package.json" (
        if exist "%PROJECT_DIR%apps\web-admin\node_modules" (
            echo [2/3] Dang khoi dong Frontend React Vite (Port 5173)...
            set "HAS_VITE=1"
            start "TourVoice_Vite" cmd /k "title TourVoice - Frontend Vite (Port 5173) && cd /d "%PROJECT_DIR%apps\web-admin" && npm run dev"
        ) else (
            echo [2/3] React Web Admin da duoc build san vao dist/ va duoc phuc vu truc tiep qua Backend FastAPI!
        )
    )
) else (
    echo [2/3] React Web Admin da duoc build san vao dist/ va duoc phuc vu truc tiep qua Backend FastAPI!
)

REM Lay dia chi IP mang LAN cua may chu nay
set "SERVER_IP=127.0.0.1"
for /f "delims=" %%i in ('"%PYTHON_EXEC%" -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2^>nul') do set "SERVER_IP=%%i"

REM 7. Cho server khoi dong va tu dong mo trinh duyet
echo [3/3] Cho server san sang trong giay lat...
ping -n 4 127.0.0.1 >nul

echo [INFO] Dang mo trinh duyet web...
if "!HAS_VITE!"=="1" (
    start http://localhost:5173/
) else (
    start http://localhost:8000/admin/
)
start http://localhost:8000/docs

cls
color 0B
echo ======================================================================
echo    TOURVOICE QUAN 4 - DANG HOAT DONG TREN MAY CHU NAY (100%% LIVE SERVER)
echo ======================================================================
echo.
echo  [CAC DUONG DAN TRUY CAP SERVER]:
echo   1. Quan Tri React Web (Truy cap tai may chu) : http://localhost:8000/admin/
echo   2. Quan Tri React Web (Mang LAN/Dien thoai)   : http://!SERVER_IP!:8000/admin/
if "!HAS_VITE!"=="1" echo   3. Cong React Vite Dev (Port 5173)          : http://localhost:5173/
echo   4. Tai Lieu API Swagger UI                   : http://localhost:8000/docs
echo   5. App Mobile React Native (Expo)            : cd mobile ^&^& npm start (da tro toi server !SERVER_IP!)
echo.
echo  [TAI KHOAN DEMO CO SAN]:
echo   - Super Admin   : superadmin@tourvoice.vn   - Pass: Admin@123456
echo   - Admin Duyet   : admin@tourvoice.vn        - Pass: Admin@123456
echo   - Chu Quan An   : owner.verified@quan4.vn   - Pass: Owner@123456
echo   - Khach Du Lich : tourist@test.vn          - Pass: User@123456
echo.
echo ======================================================================
echo  [PHIM TAT DIEU KHIEN]:
echo   [1] Mo Cong Quan Tri React (http://localhost:8000/admin/)
if "!HAS_VITE!"=="1" echo   [2] Mo React Vite Dev Server (http://localhost:5173/)
echo   [3] Mo API Docs Swagger UI (http://localhost:8000/docs)
echo   [4] Khoi Chay App Mobile React Native Expo
echo   [Q] TAT TOAN BO HE THONG (Giai phong port 8000, 5173 va dong cua so)
echo ======================================================================
echo.

:menu_loop
choice /C 1234Q /N /M "Nhap lua chon cua ban [1, 2, 3, 4, Q]: "
if errorlevel 5 goto shutdown
if errorlevel 4 goto run_mobile
if errorlevel 3 goto open_docs
if errorlevel 2 goto open_vite
if errorlevel 1 goto open_admin
goto menu_loop

:open_admin
start http://localhost:8000/admin/
goto menu_loop

:open_vite
if "!HAS_VITE!"=="1" (
    start http://localhost:5173/
) else (
    start http://localhost:8000/admin/
)
goto menu_loop

:open_docs
start http://localhost:8000/docs
goto menu_loop

:run_mobile
start "TourVoice_Mobile" cmd /k "title TourVoice - React Native Expo && cd /d "%PROJECT_DIR%mobile" && npm start"
goto menu_loop

:shutdown
echo.
echo [INFO] Dang tat cac server TourVoice...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do taskkill /f /pid %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do taskkill /f /pid %%a >nul 2>nul
taskkill /FI "WINDOWTITLE eq TourVoice*" /T /F >nul 2>nul
echo [OK] Da tat toan bo he thong TourVoice!
ping -n 2 127.0.0.1 >nul
exit /b 0
