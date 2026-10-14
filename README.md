# GestVox

Hands-free control for Windows. Control the mouse with hand gestures, or talk to a voice assistant that can run commands on your PC.

## Gesture control

Uses MediaPipe hand tracking and a pretrained gesture recognizer.

| Gesture | Action |
|---|---|
| Move index finger | Move the cursor |
| Quick pinch, thumb and index | Click (pinch twice for double click) |
| Hold pinch, thumb and index | Drag and drop |
| Pinch thumb and pinky | Right click |
| Pinch thumb and middle, move up or down | Scroll vertically |
| Pinch thumb and ring, move left or right | Scroll horizontally |
| Pinch with both hands, move apart or together | Zoom in or out |
| Swipe open palm left or right | Browser back or forward |
| Swipe open palm up or down | Switch window or show desktop |
| Hold a closed fist for about 1 second | Switch between gesture and voice mode |
| Hold an open palm still for about 1 second | Play or pause media |
| Thumbs up or down | Volume up or down |
| Victory sign | Screenshot |
| "I love you" sign, held for about 1.5 seconds | Lock the PC |

## Voice assistant

- Understands English, Urdu, Punjabi and Urdu mixed with English, detected per sentence
- Wake word ("hey vox") starts a session, and it keeps listening until you say "bye"
- Speech to text with Groq Whisper, or locally with faster-whisper for offline use
- Replies are spoken in the same language. Punjabi replies use the Urdu voice because no Punjabi neural voice is available.
- Replies stream sentence by sentence, and you can interrupt while it is speaking
- Remembers facts about you between runs
- PC control by voice:
  - Apps and windows: open, close, minimize, maximize, snap, switch, show desktop, tabs
  - Media and audio: volume, mute, play, pause, next, previous
  - System: lock, sleep, sign out, shutdown, restart, brightness, dark or light mode, Wi-Fi, Bluetooth
  - Info: battery, time, weather, CPU, memory, disk space, IP address
  - Editing shortcuts: copy, paste, cut, undo, redo, select all, save, find, print, zoom
  - Browsing: open sites, web search, YouTube search, back, forward, refresh
  - Productivity: timers, notes, clipboard, dictation, file search, screenshots
  - Anything else: the assistant writes and runs a PowerShell command
- Destructive actions such as deleting files, shutdown or turning Wi-Fi off ask for spoken confirmation first

## Multi-user

- Voice login: each person has their own voice profile
- Memory and data are kept separately for each user

## Setup

1. Create the environment: `conda env create -f environment.yml`, then `conda activate gestvox`. You can also use `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and add your Groq API key.
3. Run `python main.py`.

The gesture model (about 8 MB) is downloaded on the first run. The Groq chat model is set by `GROQ_MODEL` in `config.py`.

## Voice login

On startup, say a short phrase. A known voice logs in. For a new voice, say "my name is <name>" to create a profile. You can also say "create a profile for <name>" during a conversation.

## Remote camera

If the PC has no webcam, run `camera_server.py` on another device that has one, then set `CAMERA_SOURCE = "remote"` and `REMOTE_CAMERA_URL` in `config.py`.

Same network:

1. On the camera device, run `python camera_server.py`.
2. Find its local IP address with `ipconfig`.
3. Set `REMOTE_CAMERA_URL = "http://<ip>:8080/video"`.

Different networks (Tailscale):

1. Install Tailscale on both devices and sign in to the same account.
2. Get the camera device's Tailscale IP with `tailscale ip -4`.
3. Set `REMOTE_CAMERA_URL = "http://<tailscale-ip>:8080/video"`.

## Microphone problems

If you get a mic error on startup, run `python list_mics.py`, find the right device number and set `MIC_DEVICE_INDEX` in `config.py`.

## Notes

- Press Esc in the camera preview window to close it. The app keeps running.
- Close the overlay window to exit the app.
- On some Windows setups PyAudio needs `pip install pipwin` followed by `pipwin install pyaudio`.
