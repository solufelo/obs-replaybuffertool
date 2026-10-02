Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function AwaitTask($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType = WindowsRuntime] | Out-Null
$manager = AwaitTask ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])

if ($manager) {
    # Check all sessions or current session
    $sessions = $manager.GetSessions()
    $session = $manager.GetCurrentSession()
    
    # If no current session or not playing, try to find a session from Spotify or any playing session
    if (-not $session -or $session.GetPlaybackInfo().PlaybackStatus -ne [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus]::Playing) {
        foreach ($s in $sessions) {
            $pb = $s.GetPlaybackInfo()
            if ($pb.PlaybackStatus -eq [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus]::Playing) {
                $session = $s
                break
            }
        }
    }
    
    if (-not $session -and $sessions.Count -gt 0) {
        $session = $sessions[0]
    }

    if ($session) {
        $mediaProp = AwaitTask ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
        $playback = $session.GetPlaybackInfo()
        
        $hasThumb = $false
        if ($mediaProp.Thumbnail) {
            try {
                $stream = AwaitTask ($mediaProp.Thumbnail.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
                if ($stream -and $stream.Size -gt 0) {
                    $netStream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
                    $bytes = New-Object byte[] $stream.Size
                    $netStream.Read($bytes, 0, $stream.Size) | Out-Null
                    $netStream.Close()
                    
                    $artDir = Join-Path $PSScriptRoot "..\overlay\assets"
                    if (-not (Test-Path $artDir)) { New-Item -ItemType Directory -Path $artDir -Force | Out-Null }
                    $artPath = Join-Path $artDir "now_playing_art.png"
                    [System.IO.File]::WriteAllBytes($artPath, $bytes)
                    $hasThumb = $true
                }
            } catch {
                # Thumbnail optional
            }
        }

        # Detect active esports game
        $detectedGame = "apex"
        $procs = (Get-Process r5apex, *rivals*, *valorant*, *finals*, discovery, overwatch, rocketleague, *tekken* -ErrorAction SilentlyContinue).ProcessName
        if ($procs) {
            foreach ($p in $procs) {
                $pl = $p.ToLower()
                if ($pl -match "r5apex") { $detectedGame = "apex"; break }
                if ($pl -match "rivals") { $detectedGame = "rivals"; break }
                if ($pl -match "valorant") { $detectedGame = "valorant"; break }
                if ($pl -match "finals" -or $pl -match "discovery") { $detectedGame = "finals"; break }
                if ($pl -match "overwatch") { $detectedGame = "overwatch"; break }
                if ($pl -match "rocketleague") { $detectedGame = "rl"; break }
                if ($pl -match "tekken") { $detectedGame = "tekken"; break }
            }
        }

        [PSCustomObject]@{
            Active = $true
            Status = $playback.PlaybackStatus.ToString()
            Title = $mediaProp.Title
            Artist = $mediaProp.Artist
            Album = $mediaProp.AlbumTitle
            TrackNumber = $mediaProp.TrackNumber
            App = $session.SourceAppUserModelId
            HasThumb = $hasThumb
            Game = $detectedGame
        } | ConvertTo-Json
    } else {
        # Check active game even if no media session
        $detectedGame = "apex"
        $procs = (Get-Process r5apex, *rivals*, *valorant*, *finals*, discovery, overwatch, rocketleague, *tekken* -ErrorAction SilentlyContinue).ProcessName
        if ($procs) {
            foreach ($p in $procs) {
                $pl = $p.ToLower()
                if ($pl -match "r5apex") { $detectedGame = "apex"; break }
                if ($pl -match "rivals") { $detectedGame = "rivals"; break }
                if ($pl -match "valorant") { $detectedGame = "valorant"; break }
                if ($pl -match "finals" -or $pl -match "discovery") { $detectedGame = "finals"; break }
                if ($pl -match "overwatch") { $detectedGame = "overwatch"; break }
                if ($pl -match "rocketleague") { $detectedGame = "rl"; break }
                if ($pl -match "tekken") { $detectedGame = "tekken"; break }
            }
        }

        [PSCustomObject]@{
            Active = $false
            Status = "NoSession"
            Game = $detectedGame
        } | ConvertTo-Json
    }
} else {
    [PSCustomObject]@{
        Active = $false
        Status = "NoManager"
        Game = "apex"
    } | ConvertTo-Json
}
