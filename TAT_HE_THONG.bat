@echo off
title TourVoice - Tat He Thong Quan 4
color 0C

echo ======================================================================
echo           DANG DUNG TOAN BO HE THONG TOURVOICE QUẬN 4...
echo ======================================================================
echo.

echo [1/3] Dang dong cac tien trinh tren cong 8000 (Backend FastAPI)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>nul

echo [2/3] Dang dong cac tien trinh tren cong 5173 (Frontend Vite neu co)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>nul

echo [3/3] Dang dong cac cua so chay cua TourVoice...
taskkill /FI "WINDOWTITLE eq TourVoice*" /T /F >nul 2>nul

echo.
echo ======================================================================
echo [OK] Da tat sach toan bo he thong TourVoice!
echo Cong 8000 va 5173 da duoc giai phong hoan toan.
echo ======================================================================
echo.
ping -n 3 127.0.0.1 >nul
exit /b 0
