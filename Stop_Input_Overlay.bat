@echo off
title Stop Kinetic Telemetry Overlay
echo Stopping Input Overlay Daemon...

:: Find and terminate pythonw processes running input_overlay_daemon
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*input_overlay_daemon.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Input Overlay Terminated Cleanly.
timeout /t 1 >nul
