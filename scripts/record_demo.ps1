param(
    [Parameter(Mandatory=$true)][string]$AudioDevice,
    [string]$Output = "demo_recording.mp4",
    [string]$VideoSize = "1280x720"
)

Write-Host "Starting Streamlit in background..."
Start-Process -FilePath "streamlit" -ArgumentList "run app.py" -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host "Recording to $Output with audio device '$AudioDevice' (size=$VideoSize)"
$ffmpeg = "ffmpeg"
$ffArgs = "-f gdigrab -framerate 30 -offset_x 0 -offset_y 0 -video_size $VideoSize -i desktop -f dshow -i audio=\"$AudioDevice\" -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k \"$Output\""

npx
& $ffmpeg $ffArgs
Write-Host "Recording stopped. File: $Output"