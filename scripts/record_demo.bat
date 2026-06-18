@echo off
REM record_demo.bat
REM Usage: record_demo.bat "Audio Device Name" [output.mp4] [1280x720]

if "%1"=="" (
  echo Usage: record_demo.bat "Audio Device Name" [output.mp4] [VIDEO_SIZE]
  echo Example: record_demo.bat "Microphone (Realtek High Definition Audio)" demo.mp4 1280x720
  exit /b 1
)

set AUDIO_DEVICE=%1
set OUTPUT=%2
if "%OUTPUT%"=="" set OUTPUT=demo_recording.mp4
set VIDEO_SIZE=%3
if "%VIDEO_SIZE%"=="" set VIDEO_SIZE=1280x720

echo Starting Streamlit in a new window...
start cmd /k "streamlit run app.py"

echo Waiting 3 seconds for Streamlit to start...
timeout /t 3 /nobreak >nul

echo Recording screen to %OUTPUT% (size=%VIDEO_SIZE%) with audio device "%AUDIO_DEVICE%"
ffmpeg -f gdigrab -framerate 30 -offset_x 0 -offset_y 0 -video_size %VIDEO_SIZE% -i desktop -f dshow -i audio="%AUDIO_DEVICE%" -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k "%OUTPUT%"

necho Recording stopped. File: %OUTPUT%
pause