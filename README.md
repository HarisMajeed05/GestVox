# GestVox

Hands-free control for Windows. Move your mouse, click, and scroll with hand gestures, or talk to a full voice assistant, complete with memory, system control, and per-user voice login.

## Features

**Gesture control** (MediaPipe hand tracking + pretrained gesture recognizer)

| Gesture | Action |
| --- | --- |
| Move index finger | Move cursor |
| Pinch thumb + index | Click (quick double pinch = double-click) |
| Pinch thumb + pinky | Right-click |
| Pinch thumb + middle, move hand up/down | Scroll |
| Closed fist (held ~0.5s) | Switch between gesture and voice mode |
| Open palm | Play/pause media |
| Thumbs up | Volume up |
| Thumbs down | Volume down |
| Victory ✌ | Screenshot |
| I love you 🤟 | Lock PC |

**Voice assistant**

- Wake word activation ("hey vox")
- Full conversational AI (Groq/Llama) for questions and chat
- Persistent memory: remembers facts about you across restarts, and keeps learning from every conversation (corrections included)
- System control by voice: open/close apps, volume, media, lock/shutdown/restart, battery, time, screenshot, open websites, web search

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
