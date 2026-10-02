# ==============================================================================
# ShadowPlay-Pro-OBS: Master Service Starter
# Starts OBS and all companion daemons safely with zero duplicate instance risk.
# ==============================================================================
[CmdletBinding()]
param()

$root = "$PSScriptRoot\.."

# 1. Start OBS via Single-Instance Guard
& "$PSScriptRoot\launch_obs.ps1"

# 2. Start Background Daemons
Start-ScheduledTask -TaskName "OBS_ShadowPlay_Engine" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "OBS_Input_Overlay" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "OBS_BeepWatcher" -ErrorAction SilentlyContinue

Write-Host ">>> ShadowPlay-Pro-OBS broadcast & replay suite active." -ForegroundColor Green
