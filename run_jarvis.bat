@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo            JARVIS STARTING
echo ==========================================
echo.

if not exist "tahrun.py" (
    echo ERROR: tahrun.py not found.
    pause
    exit /b 1
)

python "tahrun.py"

echo.
echo ==========================================
echo            JARVIS STOPPED
echo ==========================================
pause
