# ==============================================================================
# ShadowPlay-Pro-OBS: Single-Instance OBS Launcher & Scene Enforcer
# Guarantees OBS starts only once, with Replay Buffer active, and defaulted
# to the main face + game scene: "GAMEPLAY ULTRA (Active)".
# ==============================================================================
[CmdletBinding()]
param()

$obsPath = "C:\Program Files\obs-studio\bin\64bit\obs64.exe"
$obsDir = "C:\Program Files\obs-studio\bin\64bit"
$sceneName = "GAMEPLAY ULTRA (Active)"

# 1. Strict Single-Instance Guard (Prevents "OBS is already running" alert)
$runningObs = Get-Process -Name "obs64" -ErrorAction SilentlyContinue
if ($runningObs) {
    Write-Host ">>> OBS Studio is already running (PID $($runningObs.Id)). Skipping secondary launch to prevent duplicate instance error." -ForegroundColor Yellow
    exit 0
}

# 2. Clear stale crash / shutdown sentinels
$sentinelDir = "$env:APPDATA\obs-studio\.sentinel"
if (Test-Path $sentinelDir) {
    Get-ChildItem -Path $sentinelDir -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

# 3. Ensure global.ini has OBSWebSocket enabled
$globalIni = "$env:APPDATA\obs-studio\global.ini"
if (Test-Path $globalIni) {
    try {
        $ini = Get-Content $globalIni -Raw
        if ($ini -notmatch "ServerEnabled=true") {
            $ini = $ini -replace "\[OBSWebSocket\](\r?\n)?", "[OBSWebSocket]`r`nServerEnabled=true`r`nServerPort=4455`r`nAuthRequired=false`r`n"
            Set-Content -Path $globalIni -Value $ini -Encoding UTF8
        }
    } catch {}
}

# 4. Enforce "GAMEPLAY ULTRA (Active)" in Scene Collection JSON
$sceneJsonPath = "$env:APPDATA\obs-studio\basic\scenes\Optimaxx_Master_Gaming.json"
if (Test-Path $sceneJsonPath) {
    try {
        $json = Get-Content $sceneJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $json.current_scene = $sceneName
        $json.current_program_scene = $sceneName
        $json | ConvertTo-Json -Depth 32 | Set-Content $sceneJsonPath -Encoding UTF8
    } catch {}
}

# 5. Launch OBS with exact arguments
$obsArgs = "--startreplaybuffer --minimize-to-tray --scene `"$sceneName`""
Write-Host ">>> Starting OBS Studio (Single-Instance Mode) -> Scene: $sceneName" -ForegroundColor Cyan
Start-Process -FilePath $obsPath -ArgumentList $obsArgs -WorkingDirectory $obsDir

# 6. Verify Process Started
Start-Sleep -Seconds 3
$newObs = Get-Process -Name "obs64" -ErrorAction SilentlyContinue
if ($newObs) {
    Write-Host ">>> OBS Studio running successfully (PID $($newObs.Id))." -ForegroundColor Green
} else {
    Write-Warning "OBS Studio process did not start within expected time."
}
