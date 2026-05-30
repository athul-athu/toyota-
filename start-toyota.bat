@echo off
title Toyota Payroll - Launcher
cd /d "%~dp0"

echo ============================================
echo   Toyota Payroll - Starting...
echo ============================================
echo.

if not exist "server\.venv\Scripts\python.exe" (
  echo Virtual environment not found.
  echo Please run setup-first-time.bat first.
  pause
  exit /b 1
)

if not exist ".env" (
  echo .env file not found at repo root.
  echo Run setup-first-time.bat or copy .env.example to .env
  pause
  exit /b 1
)

echo Starting Django API on http://localhost:8000 ...
start "Toyota - Django API" cmd /k "cd /d ""%~dp0server"" && .venv\Scripts\python.exe manage.py runserver 8000"

echo Waiting for API to start...
timeout /t 4 /nobreak >nul

echo Starting Admin Dashboard on http://localhost:3000 ...
start "Toyota - Admin Dashboard" cmd /k "cd /d ""%~dp0admin-dash"" && npm run dev"

timeout /t 6 /nobreak >nul
echo Opening browser...
start http://localhost:3000/login

echo.
echo ============================================
echo   Running!
echo   Dashboard: http://localhost:3000
echo   API:       http://localhost:8000
echo   Close the two terminal windows to stop.
echo ============================================
echo.
pause
