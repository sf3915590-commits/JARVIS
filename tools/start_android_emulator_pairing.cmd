@echo off
setlocal
cd /d "%~dp0.."
title JARVIS - Android emulator pairing
if not exist "jarvis_companion_server.py" (
 echo This older GitHub checkout lacks jarvis_companion_server.py.
 echo No files or services were changed. Use the newer Windows project.
 pause
 exit /b 1
)
where python >nul 2>&1
if errorlevel 1 (
 echo Python was not found. Nothing changed.
 pause
 exit /b 1
)
python -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',8778))==0 else 1)"
if not errorlevel 1 (
 echo Port 8778 is already in use. Existing service untouched.
 echo Inspect the existing process before issuing a new pairing code.
 pause
 exit /b 1
)
echo.
echo This setup only touches the separate Android HTTPS service.
echo It will NOT stop desktop JARVIS, Tailscale, HUD or chat port 8766.
echo.
python jarvis_companion_server.py init 10.0.2.2
if errorlevel 1 (
 echo Certificate initialization failed; no server started.
 pause
 exit /b 1
)
echo.
echo Android emulator Chat URL: https://10.0.2.2:8778/api/chat
echo Copy the certificate SHA-256 fingerprint printed above.
start "JARVIS Android companion HTTPS" cmd /k "python jarvis_companion_server.py serve --listen 127.0.0.1 --port 8778"
timeout /t 2 >nul
echo.
echo The next command requires local owner confirmation.
python jarvis_companion_server.py code profile-1
echo.
echo In Android Main, save the HTTPS URL and certificate fingerprint,
echo then enroll profile-1 with the private desktop-issued code.
echo Never share the code or any private key.
pause
