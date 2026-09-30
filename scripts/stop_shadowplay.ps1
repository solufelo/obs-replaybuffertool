Stop-ScheduledTask -TaskName "OBS_Input_Overlay" -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName "OBS_ShadowPlay_Engine" -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName "OBS_ShadowPlay" -ErrorAction SilentlyContinue
Stop-Process -Name obs64 -Force -ErrorAction SilentlyContinue
Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*shadowplay_engine*" -or $_.CommandLine -like "*input_overlay_daemon*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "ShadowPlay-Pro-OBS background services stopped." -ForegroundColor Yellow
