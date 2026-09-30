# ==============================================================================
# ShadowPlay-Pro-OBS: One-Click Turnkey Deployment Script
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Write-Host ">>> Initializing ShadowPlay-Pro-OBS Setup..." -ForegroundColor Cyan

# 1. Verify OBS Installation
$obsPath = "C:\Program Files\obs-studio\bin\64bit\obs64.exe"
if (-not (Test-Path $obsPath)) {
    Write-Error "OBS Studio 64-bit not found at '$obsPath'. Please install OBS Studio."
}

# 2. Verify Python Installation for Daemon
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw -and (Test-Path "C:\Python314\pythonw.exe")) {
    $pythonw = "C:\Python314\pythonw.exe"
}
if (-not $pythonw) {
    Write-Warning "pythonw.exe not found in PATH. Please install Python 3.10+."
}

# 3. Create Storage Directories
$clipsDir = "$env:USERPROFILE\Videos\Clips"
$archiveDir = "F:\Gameplay_Archive\Full_Sessions"
New-Item -ItemType Directory -Path $clipsDir -Force | Out-Null
if (Test-Path "F:\") {
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
}

# 4. Deploy Background Task for Daemon
Write-Host ">>> Registering 24/7 Background Engine..." -ForegroundColor Green
$daemonScript = "$PSScriptRoot\daemon\shadowplay_engine.py"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
$actionDaemon = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$daemonScript`"" -WorkingDirectory "$PSScriptRoot\daemon"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "OBS_ShadowPlay_Engine" -Action $actionDaemon -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName "OBS_ShadowPlay_Engine"

# 4b. Deploy Background Task for Input Overlay
Write-Host ">>> Registering 24/7 Input Overlay Daemon..." -ForegroundColor Green
$overlayDaemonScript = "$PSScriptRoot\daemon\input_overlay_daemon.py"
$actionOverlay = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$overlayDaemonScript`"" -WorkingDirectory "$PSScriptRoot\daemon"
Register-ScheduledTask -TaskName "OBS_Input_Overlay" -Action $actionOverlay -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName "OBS_Input_Overlay"

# 5. Register OBS 24/7 Autostart Task
Write-Host ">>> Registering OBS 24/7 Silent Background Task..." -ForegroundColor Green
$actionObs = New-ScheduledTaskAction -Execute $obsPath -Argument "--disable-shutdown-check --startreplaybuffer --minimize-to-tray" -WorkingDirectory "C:\Program Files\obs-studio\bin\64bit"
Register-ScheduledTask -TaskName "OBS_ShadowPlay" -Action $actionObs -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

# 6. Deploy Windows Startup & Desktop Shortcuts
$sh = New-Object -ComObject WScript.Shell
$startupObs = $sh.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\OBS ShadowPlay.lnk")
$startupObs.TargetPath = $obsPath
$startupObs.Arguments = "--disable-shutdown-check --startreplaybuffer --minimize-to-tray"
$startupObs.WorkingDirectory = "C:\Program Files\obs-studio\bin\64bit"
$startupObs.WindowStyle = 7
$startupObs.Save()

$desktopObs = $sh.CreateShortcut("$env:USERPROFILE\Desktop\OBS ShadowPlay.lnk")
$desktopObs.TargetPath = $obsPath
$desktopObs.Arguments = "--disable-shutdown-check --startreplaybuffer --minimize-to-tray"
$desktopObs.WorkingDirectory = "C:\Program Files\obs-studio\bin\64bit"
$desktopObs.WindowStyle = 7
$desktopObs.Save()

Write-Host "==============================================================================" -ForegroundColor Green
Write-Host " SUCCESS: ShadowPlay-Pro-OBS is installed and active 24/7!" -ForegroundColor Green
Write-Host " Replay Buffer Duration: 90 Seconds" -ForegroundColor Yellow
Write-Host " Hotkeys: Ctrl + Shift + C | Ctrl + X" -ForegroundColor Yellow
Write-Host " Clips Location: $clipsDir" -ForegroundColor Yellow
Write-Host " Long-term Archive: $archiveDir" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Green
