@echo off
REM MCP Demo Standalone - Run Script for Windows

echo ===================================
echo MCP Demo Standalone Application
echo ===================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo.
    echo Warning: No .env file found. Creating from .env.example...
    copy .env.example .env
    echo Created .env file. Please edit it with your configuration.
    echo.
)

REM Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "flask_session" mkdir flask_session

REM Run the application
echo.
echo Starting MCP Demo on http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python app.py