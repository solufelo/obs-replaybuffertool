Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function AwaitTask($WinRtTask, $ResultType) {
    try {
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(1500) | Out-Null
        return $netTask.Result
    } catch {
        return $null
    }
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType = WindowsRuntime] | Out-Null
$manager = AwaitTask ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])

while ($true) {
    try {
        if ($manager) {
            $session = $manager.GetCurrentSession()
            if (-not $session) {
                $sessions = $manager.GetSessions()
                if ($sessions -and $sessions.Count -gt 0) {
                    foreach ($s in $sessions) {
                        if ($s.GetPlaybackInfo().PlaybackStatus -eq [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus]::Playing) {
                            $session = $s
                            break
                        }
                    }
                    if (-not $session) { $session = $sessions[0] }
                }
            }

            if ($session) {
                $mediaProp = AwaitTask ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
                $playback = $session.GetPlaybackInfo()

                [PSCustomObject]@{
                    Active = $true
                    Status = $playback.PlaybackStatus.ToString()
                    Title = if ($mediaProp) { $mediaProp.Title } else { "Music Playing" }
                    Artist = if ($mediaProp) { $mediaProp.Artist } else { "System Audio" }
                    Album = if ($mediaProp) { $mediaProp.AlbumTitle } else { "" }
                    App = $session.SourceAppUserModelId
                } | ConvertTo-Json -Compress
            } else {
                [PSCustomObject]@{ Active = $false; Status = "NoSession" } | ConvertTo-Json -Compress
            }
        } else {
            [PSCustomObject]@{ Active = $false; Status = "NoManager" } | ConvertTo-Json -Compress
        }
    } catch {
        [PSCustomObject]@{ Active = $false; Status = "Error" } | ConvertTo-Json -Compress
    }

    [Console]::Out.Flush()
    Start-Sleep -Milliseconds 2000
}
