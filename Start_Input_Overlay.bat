@echo off
title Captain Solo Kinetic Telemetry Overlay
echo [1/2] Initializing Input Overlay Daemon (Adaptive 0-Overhead Poller)...

:: Check if daemon is already active on port 8998
netstat -ano | findstr ":8998 " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [Daemon] Already active on port 8998.
) else (
    start "" "C:\Python314\pythonw.exe" "C:\Users\Administrator\Desktop\ShadowPlay-Pro-OBS\daemon\input_overlay_daemon.py"
    timeout /t 1 >nul
)

echo [2/2] Launching Overlay Interface...
:: Launch in browser or OBS dock
start "" "http://127.0.0.1:8998"

echo Kinetic Overlay Active!
timeout /t 2 >nul
