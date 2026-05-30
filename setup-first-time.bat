@echo off
title Toyota Payroll - First-time setup
cd /d "%~dp0"

echo ============================================
echo   Toyota Payroll - First-time setup
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found. Install Python 3.12+ and add to PATH.
  pause
  exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js not found. Install from https://nodejs.org/
  pause
  exit /b 1
)

if not exist ".env" (
  echo Creating .env from .env.example ...
  copy /Y ".env.example" ".env"
  echo.
  echo IMPORTANT: Edit .env with your Supabase keys and Gmail App Password.
  echo See SETUP.md for step-by-step instructions.
  echo.
  pause
)

if not exist "admin-dash\.env.local" (
  echo Creating admin-dash\.env.local for local Django ...
  (
    echo NEXT_PUBLIC_API_URL=http://localhost:8000
  ) > "admin-dash\.env.local"
) else (
  echo Using existing admin-dash\.env.local
)

echo [1/4] Python virtual environment...
cd server
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [2/4] Database migrations...
python manage.py migrate
cd ..

echo [3/4] Admin dashboard dependencies...
cd admin-dash
call npm install
cd ..

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo Next steps:
echo   1. Edit .env in this folder (Supabase + SMTP) - see SETUP.md
echo   2. Run server\supabase\schema.sql in Supabase SQL Editor
echo   3. Double-click start-toyota.bat
echo.
pause
