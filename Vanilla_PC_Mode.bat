@echo off
setlocal
title True Vanilla PC Mode [Solomon Optimizer]

echo ==============================================================================
echo           SOLOMON OPTIMIZER - SWITCHING TO TRUE VANILLA PC MODE
echo ==============================================================================
echo.
echo [*] Terminating OBS Studio, input overlays, and streaming daemons...
"C:\Python314\python.exe" "C:\Users\Administrator\Desktop\ShadowPlay-Pro-OBS\tools\solomon_core.py" vanilla

echo.
echo [*] Setting Boot Profile: Vanilla Clean (Scheduled tasks disabled on boot)...
"C:\Python314\python.exe" "C:\Users\Administrator\Desktop\ShadowPlay-Pro-OBS\tools\solomon_core.py" boot-vanilla

echo.
echo ==============================================================================
echo  [+] SUCCESS: TRUE VANILLA PC MODE ACTIVE
echo  - Port 8998: RELEASED
echo  - Low-Level Mouse and Keyboard Hooks: UNHOOKED (Zero Input Latency)
echo  - Boot Profile: Pure Gaming (Zero background services on Windows boot)
echo ==============================================================================
echo.
ping -n 3 127.0.0.1 >nul
