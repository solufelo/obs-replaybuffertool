# ==============================================================================
# Captain Solo Theme Switcher
# Usage: .\switch_theme.ps1 [solo | octane | stealth]
# ==============================================================================
param(
    [ValidateSet("solo", "octane", "stealth")]
    [string]$Theme = "solo"
)

$overlayDir = "$PSScriptRoot\..\overlay"
$themeFile = "$overlayDir\theme.js"

$content = "// Captain Solo Broadcast Theme Configuration`r`nwindow.ACTIVE_THEME = `"$Theme`";`r`n"
Set-Content -Path $themeFile -Value $content -Encoding UTF8

Write-Host ">>> Theme switched to: $Theme" -ForegroundColor Cyan

# Refresh OBS browser sources via tools/obs_client.py
$pyScript = @"
import sys
sys.path.insert(0, r'$PSScriptRoot\..\tools')
from obs_client import call_obs

sources = [
    'Webcam Pro Frame',
    'Apex Movement Input Overlay',
    'Creator Social Ticker',
    'Just Chatting Frame',
    'Starting Soon Screen',
    'BRB Screen'
]

for src in sources:
    try:
        call_obs('PressInputPropertiesButton', {
            'inputName': src,
            'propertyName': 'refreshnocache'
        })
    except Exception:
        pass
print('OBS Overlays refreshed live.')
"@

$pyFile = "$env:TEMP\refresh_obs_theme.py"
Set-Content -Path $pyFile -Value $pyScript -Encoding UTF8
python $pyFile 2>$null
Remove-Item $pyFile -ErrorAction SilentlyContinue

Write-Host ">>> Done! Active preset: $Theme" -ForegroundColor Green
