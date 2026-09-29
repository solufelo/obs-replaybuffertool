# Starts OBS in silent 24/7 background mode with Replay Buffer and ShadowPlay Engine
Start-ScheduledTask -TaskName "OBS_ShadowPlay" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "OBS_ShadowPlay_Engine" -ErrorAction SilentlyContinue
Write-Host "ShadowPlay-Pro-OBS background services started." -ForegroundColor Green
