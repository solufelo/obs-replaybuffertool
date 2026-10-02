@echo off
setlocal
title CPTSOLO Lumin OS Mode [Solomon Optimizer]

echo ==============================================================================
echo           SOLOMON OPTIMIZER - ACTIVATING CPTSOLO LUMIN OS MODE
echo ==============================================================================
echo.
echo [*] Initializing Port 8998 Telemetry Server (Ultra Hybrid HUD, Spotify, TAS.gg)...
echo [*] Initializing 24/7 ShadowPlay Replay Engine...
echo [*] Launching OBS Studio (Replay Buffer Active)...
echo.
"C:\Python314\python.exe" "C:\Users\Administrator\Desktop\ShadowPlay-Pro-OBS\tools\solomon_core.py" lumin

echo.
echo ==============================================================================
echo  [+] SUCCESS: CPTSOLO LUMIN OS BROADCAST SUITE ONLINE
echo  - Overlays Active on http://127.0.0.1:8998/ultra
echo  - Replay Buffer Activated (Hotkeys: Ctrl+Shift+C / Ctrl+X)
echo  - Auto-Exit Watchdog: Armed (Releases port 8998 when OBS exits)
echo ==============================================================================
echo.
ping -n 3 127.0.0.1 >nul
