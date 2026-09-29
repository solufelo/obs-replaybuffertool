# Gracefully stops OBS and background engine
Stop-Process -Name obs64 -Force -ErrorAction SilentlyContinue
Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*shadowplay_engine*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "ShadowPlay-Pro-OBS background services stopped." -ForegroundColor Yellow
