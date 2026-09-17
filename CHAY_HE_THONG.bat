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
    echo [LOI] Khong tim thay thu muc backend!
    echo Vui long dat file bat trong thu muc seminar hoac seminarchuyende.
    echo.
    pause
    exit /b 1
)

REM 2. Khoi tao file .env neu chua co
if not exist "%PROJECT_DIR%backend\.env" (
    if exist "%PROJECT_DIR%backend\.env.example" (
        echo [INFO] Tao file .env cho backend tu .env.example...
        copy "%PROJECT_DIR%backend\.env.example" "%PROJECT_DIR%backend\.env" >nul
    )
)

REM 3. Kiem tra Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py"
    ) else (
        color 0C
        echo [LOI] May tinh cua ban chua cai dat Python!
        echo Vui long cai dat Python 3.10+ va tich vao "Add Python to PATH".
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
    echo [INFO] Su dung Python: %PYTHON_CMD%
)

REM 4. Khoi chay Backend Server FastAPI (Port 8000)
echo.
echo [1/3] Dang khoi dong Backend FastAPI tai cong 8000...
start "TourVoice_Backend" cmd /k "title TourVoice - Backend Server && cd /d "%PROJECT_DIR%backend" && "%PYTHON_EXEC%" run.py"

REM 5. Kiem tra Node.js / npm de chay Frontend React Vite (Port 5173 neu co)
set "HAS_VITE=0"
where npm >nul 2>nul
if %errorlevel% equ 0 (
    if exist "%PROJECT_DIR%apps\web-admin\package.json" (
        if exist "%PROJECT_DIR%apps\web-admin\node_modules" (
            echo [2/3] Dang khoi dong Frontend React Vite tai cong 5173...
            set "HAS_VITE=1"
            start "TourVoice_Vite" cmd /k "title TourVoice - Frontend Vite && cd /d "%PROJECT_DIR%apps\web-admin" && npm run dev"
        ) else (
            echo [2/3] Apps\web-admin chua cai node_modules. Frontend Web Admin va Client se chay qua Backend!
        )
    )
) else (
    echo [2/3] May chua cai Node.js/npm. Giao dien Web Admin va Client se chay truc tiep qua Backend!
)

REM 6. Cho server khoi dong va tu dong mo trinh duyet
echo [3/3] Cho server san sang trong giay lat...
ping -n 4 127.0.0.1 >nul

echo [INFO] Dang mo trinh duyet web...
start http://localhost:8000/admin/
start http://localhost:8000/client/
if "!HAS_VITE!"=="1" start http://localhost:5173/

cls
color 0B
echo ======================================================================
echo       HE THONG TOURVOICE QUAN 4 DA KHOI DONG THANH CONG!
echo ======================================================================
echo.
echo  [CAC DUONG DAN TRUY CAP]:
echo   1. Cong Quan Tri CMS (Admin / Chu quan) : http://localhost:8000/admin/
echo   2. Giao Dien Du Khach (Client)          : http://localhost:8000/client/
echo   3. Tai Lieu API Swagger UI              : http://localhost:8000/docs
if "!HAS_VITE!"=="1" echo   4. Cong React Web-Admin (Vite)          : http://localhost:5173/
echo.
echo  [TAI KHOAN DEMO CO SAN]:
echo   - Super Admin   : superadmin@tourvoice.vn   - Pass: Admin@123456
echo   - Admin Duyet   : admin@tourvoice.vn        - Pass: Admin@123456
echo   - Chu Quan An   : owner.verified@quan4.vn   - Pass: Owner@123456
echo   - Khach Du Lich : tourist@test.vn          - Pass: User@123456
echo.
echo ======================================================================
echo  [PHIM TAT DIEU KHIEN]:
echo   [1] Mo lai Cong Admin (http://localhost:8000/admin/)
echo   [2] Mo lai Giao Dien Khach (http://localhost:8000/client/)
echo   [3] Mo lai API Docs (http://localhost:8000/docs)
echo   [Q] TAT TOAN BO HE THONG (Giai phong port 8000 va dung server)
echo ======================================================================
echo.

:menu_loop
choice /C 123Q /N /M "Nhap lua chon cua ban [1, 2, 3, Q]: "
if errorlevel 4 goto shutdown
if errorlevel 3 goto open_docs
if errorlevel 2 goto open_client
if errorlevel 1 goto open_admin
goto menu_loop

:open_admin
start http://localhost:8000/admin/
goto menu_loop

:open_client
start http://localhost:8000/client/
goto menu_loop

:open_docs
start http://localhost:8000/docs
goto menu_loop

:shutdown
echo.
echo [INFO] Dang dong cac server TourVoice...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>nul
taskkill /FI "WINDOWTITLE eq TourVoice*" /T /F >nul 2>nul
echo [OK] Da tat toan bo he thong TourVoice.
ping -n 3 127.0.0.1 >nul
exit /b 0
