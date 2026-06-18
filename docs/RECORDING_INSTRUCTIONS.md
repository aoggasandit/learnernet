# Recording the Demo — Windows (ffmpeg) and OBS

This guide helps you record the demo video locally. I created two helper scripts in `scripts/` you can run.

Prerequisites
- Install ffmpeg (https://ffmpeg.org/download.html). Add `ffmpeg` to your PATH.
- (Optional) Use OBS Studio for a GUI-based recording.

Find your audio device name for ffmpeg (PowerShell)

```
ffmpeg -list_devices true -f dshow -i dummy
```

This prints available "DirectShow" devices — copy the exact name of your microphone.

Files I added
- `scripts/record_demo.bat` — Windows batch launcher (uses ffmpeg). Requires the audio device name as first arg.
- `scripts/record_demo.ps1` — PowerShell script variant with named params.
- `docs/NARRATION.txt` — full voiceover text to read while recording.

Quick steps (recommended)
1. Start Streamlit in a separate terminal:

```powershell
streamlit run app.py
```

2. In a second terminal, run the batch script (replace the audio device name):

```powershell
scripts\record_demo.bat "Your Microphone Device Name" demo.mp4 1280x720
```

or use PowerShell script:

```powershell
pwsh .\scripts\record_demo.ps1 -AudioDevice "Your Microphone Device Name" -Output demo.mp4 -VideoSize 1280x720
```

Notes about parameters
- `AudioDevice`: required — the exact name from `ffmpeg -list_devices` output.
- `Output`: optional filename, defaults to `demo_recording.mp4` in the current directory.
- `VideoSize`: optional (e.g., `1280x720` or `1920x1080`). The script will record that area of the desktop.

Stopping the recording
- In the terminal where ffmpeg runs, press `q` to stop cleanly, or use `Ctrl+C`.

OBS alternative (recommended for higher quality)
- Create a Scene with:
  - Display Capture: choose the monitor or window showing Streamlit.
  - Audio Input Capture: select your microphone.
  - Optional: Window Capture for the browser window.
- Use OBS to record or stream; export the recording as MP4.

Privacy tips for recording
- Use placeholder values when showing `.env` on-camera (do not show secrets).
- Show commands in the terminal rather than full secret contents.

Next steps I can do for you
- Generate a TTS audio file of the narration (I can create a WAV/MP3 you can mix into the recording). This requires me to run a TTS service (I can generate a local file if you want).
- Create an OBS scene collection export (I can generate a JSON/scene file template).

Run the scripts and tell me if you want the TTS audio generated.