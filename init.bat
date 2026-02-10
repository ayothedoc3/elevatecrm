@echo off
REM =============================================================================
REM Elevate CRM - Development Environment Setup Script (Windows)
REM =============================================================================
REM This script sets up and starts the development environment for Elevate CRM.
REM
REM Prerequisites:
REM   - Node.js 20+ (https://nodejs.org/)
REM   - Python 3.10+ (https://www.python.org/)
REM   - npm or yarn
REM
REM Usage:
REM   init.bat              - Full setup and start
REM   init.bat --install    - Install dependencies only
REM   init.bat --backend    - Start backend only
REM   init.bat --frontend   - Start frontend only
REM =============================================================================

setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0

echo ============================================
echo   Elevate CRM - Development Setup
echo ============================================
echo.

REM Check prerequisites
echo Checking prerequisites...

REM Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js is not installed. Please install Node.js 20+
    exit /b 1
)
for /f "tokens=1" %%i in ('node -v') do set NODE_VER=%%i
echo   [OK] Node.js %NODE_VER%

REM Check npm
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: npm is not installed
    exit /b 1
)
for /f "tokens=1" %%i in ('npm -v') do set NPM_VER=%%i
echo   [OK] npm %NPM_VER%

REM Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed. Please install Python 3.10+
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version') do set PY_VER=%%i
echo   [OK] Python %PY_VER%

echo.

REM Parse arguments
if "%1"=="--install" goto :install_only
if "%1"=="--backend" goto :backend_only
if "%1"=="--frontend" goto :frontend_only

REM Default: full setup and start
:full_setup
call :install_backend
call :install_frontend

echo ============================================
echo   Starting Elevate CRM...
echo ============================================
echo.

REM Start backend in new window
start "Elevate CRM Backend" cmd /k "cd /d %PROJECT_ROOT%backend && call venv\Scripts\activate.bat && python server.py"
timeout /t 3 /nobreak >nul

REM Start frontend in new window
start "Elevate CRM Frontend" cmd /k "cd /d %PROJECT_ROOT%frontend && npm start"

echo ============================================
echo   Elevate CRM is running!
echo ============================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8001
echo   API Docs:  http://localhost:8001/docs
echo.
echo Close the command windows to stop the servers.
echo.
goto :eof

:install_only
call :install_backend
call :install_frontend
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo To start the development servers, run:
echo   init.bat
echo.
goto :eof

:backend_only
call :install_backend
echo Starting backend server...
cd /d %PROJECT_ROOT%backend
call venv\Scripts\activate.bat
python server.py
goto :eof

:frontend_only
call :install_frontend
echo Starting frontend server...
cd /d %PROJECT_ROOT%frontend
npm start
goto :eof

:install_backend
echo Setting up backend...
cd /d %PROJECT_ROOT%backend

if not exist venv (
    echo   Creating Python virtual environment...
    python -m venv venv
)

echo   Installing Python dependencies...
call venv\Scripts\activate.bat
pip install -q --upgrade pip
pip install -q -r requirements.txt

if not exist .env (
    echo   Creating backend .env file...
    (
        echo # Elevate CRM Backend Configuration
        echo # PostgreSQL (Phase 1 core)
        echo DATABASE_URL=postgresql://crm_user:crm_password@localhost:5432/crm_os
        echo.
        echo # Security
        echo SECRET_KEY=your-secret-key-change-in-production
        echo JWT_ALGORITHM=HS256
        echo ACCESS_TOKEN_EXPIRE_MINUTES=1440
        echo.
        echo # CORS
        echo CORS_ORIGINS=*
        echo.
        echo # OpenAI API ^(for AI features^)
        echo OPENAI_API_KEY=your-openai-api-key
        echo.
        echo # Stripe ^(for payments^)
        echo STRIPE_SECRET_KEY=your-stripe-secret-key
        echo STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
        echo.
        echo # Twilio ^(for SMS^)
        echo TWILIO_ACCOUNT_SID=your-twilio-account-sid
        echo TWILIO_AUTH_TOKEN=your-twilio-auth-token
        echo TWILIO_PHONE_NUMBER=your-twilio-phone-number
        echo.
        echo # SendGrid ^(for email^)
        echo SENDGRID_API_KEY=your-sendgrid-api-key
        echo.
        echo # Server settings
        echo HOST=0.0.0.0
        echo PORT=8001
    ) > .env
)

echo   [OK] Backend setup complete
cd /d %PROJECT_ROOT%
echo.
goto :eof

:install_frontend
echo Setting up frontend...
cd /d %PROJECT_ROOT%frontend

echo   Installing frontend dependencies...
call npm install --silent

if not exist .env (
    echo   Creating frontend .env file...
    (
        echo # Elevate CRM Frontend Configuration
        echo REACT_APP_BACKEND_URL=http://localhost:8001
        echo REACT_APP_API_URL=http://localhost:8001
        echo REACT_APP_APP_PHASE=1
    ) > .env
)

echo   [OK] Frontend setup complete
cd /d %PROJECT_ROOT%
echo.
goto :eof
