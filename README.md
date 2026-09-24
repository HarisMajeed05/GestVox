# GestVox

Hands-free control for Windows. Move your mouse, click, and scroll with hand gestures, or talk to a full voice assistant, complete with memory, system control, and per-user voice login.

## Features

**Gesture control** (MediaPipe hand tracking + pretrained gesture recognizer)

| Gesture | Action |
| --- | --- |
| Move index finger | Move cursor |
| Pinch thumb + index (quick) | Click (pinch twice = double-click) |
| Pinch thumb + index (hold) | Drag and drop |
| Pinch thumb + pinky | Right-click |
| Pinch thumb + middle, move up/down | Scroll vertically |
| Pinch thumb + ring, move left/right | Scroll horizontally |
| Pinch both hands, move apart/together | Zoom in / out |
| Swipe open palm left / right | Browser back / forward |
| Swipe open palm up / down | Switch window / show desktop |
| Closed fist (hold ~1s) | Switch between gesture and voice mode (works in both modes) |
| Open palm (hold still ~1s) | Play/pause media |
| Thumbs up | Volume up |
| Thumbs down | Volume down |
| Victory | Screenshot |
| I love you (hold ~1.5s) | Lock PC |

**Languages**

- Understands English, Urdu, Punjabi, and Urdu mixed with English, detected automatically per sentence
- Wake words and commands work in any of them ("hey vox", "سنو ووکس", "chrome kholo", "آواز بڑھاؤ")
- Replies are spoken back in the same language, using neural voices
- Punjabi has no neural voice available, so Punjabi replies use the Urdu voice

**Voice assistant**

- Wake word starts a session ("hey vox"), it keeps listening until you say "bye"
- Speech to text through Groq Whisper (best for Urdu and Punjabi), or locally with faster-whisper for no network delay and offline use
- Replies stream sentence by sentence, so it starts speaking before the full answer is ready, and you can interrupt it mid-sentence
- Full conversational AI (Groq) for questions and chat
- Persistent memory: remembers facts about you across restarts, and keeps learning from every conversation (corrections included)
- Full PC control by voice, either through built-in commands or PowerShell for anything else:
  - Apps and windows: open/close apps, minimize, maximize, snap, switch window, show desktop, tabs
  - Media and audio: volume, mute, play/pause, next/previous track
  - System: lock, sleep, sign out, shutdown, restart, brightness, dark/light mode, Wi-Fi, Bluetooth
  - Info: battery, time, weather (live), CPU/memory, disk space, IP address
  - Editing shortcuts: copy, paste, cut, undo, redo, select all, save, find, print, zoom
  - Browsing: open known sites, web search, YouTube search, back/forward, refresh
  - Productivity: timers, notes, clipboard read/write, dictation, file search, screenshots
  - Anything else: the assistant writes and runs a PowerShell command
- Destructive actions (deleting files, shutdown, Wi-Fi off) ask for spoken confirmation first

**Multi-user**

- Voice biometric login: each person gets their own recognized voice profile
- Separate memory/data per user, nobody sees anyone else's facts or history

**Other**

- Remote camera support: run the camera on a different device (e.g. a laptop) over local network or Tailscale, useful if the PC has no webcam
- Small always-on-top overlay to see/switch mode manually
- Live gesture detection log (console + on-screen label)

## Setup

1. `conda env create -f environment.yml` then `conda activate gestvox`
   (or `pip install -r requirements.txt`)
2. Copy `.env.example` to `.env` and add your Groq API key
3. Run `python main.py`

First run downloads the gesture recognition model (~8MB) automatically.

## Voice login

On startup, say a short phrase. Recognized voice → logs you in. Unknown voice → say "my name is <name>" to create a profile. You can also say "create a profile for <name>" any time during a conversation.

## Remote camera

If the PC has no webcam, run `camera_server.py` on another device with a camera, then set `CAMERA_SOURCE = "remote"` and `REMOTE_CAMERA_URL` in `config.py`. See below for same-network and cross-network (Tailscale) setup.

### Same local network

1. On the camera device: `python camera_server.py`
2. Find its local IP (`ipconfig`)
3. Set `REMOTE_CAMERA_URL = "http://<ip>:8080/video"`

### Different networks (Tailscale)

1. Install Tailscale on both devices, log into the same account
2. Get the camera device's Tailscale IP (`tailscale ip -4`)
3. Set `REMOTE_CAMERA_URL = "http://<tailscale-ip>:8080/video"`

## Mic issues

If you get a mic error on startup, run `python list_mics.py`, note the correct device number, and set `MIC_DEVICE_INDEX` in `config.py`.

## Notes

- Press `Esc` in the camera preview window to close it (app keeps running)
- Close the overlay window to fully exit
- PyAudio may need `pip install pipwin` then `pipwin install pyaudio` on some Windows setups
