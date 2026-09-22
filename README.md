# GestVox

Gesture + voice controlled interface for Windows.

## Setup

1. `conda env create -f environment.yml`
2. `conda activate gestvox`
3. Copy `.env.example` to `.env` and paste your Groq API key.
4. Run: `python main.py`

Alternative (pip only, no conda):

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and paste your Groq API key.
3. Run: `python main.py`

## Controls

**Gesture mode (default)**

- Move index finger: moves cursor
- Pinch thumb + index: click (quick double pinch: double-click)
- Pinch thumb + middle, move hand up/down: scroll
- Hold a fist for 1 second: switch to voice mode

**Voice mode**

- Say a wake word ("hey air control") then speak your request or question
- Say "switch to gesture mode" any time to go back
- Say "exit" or "quit" to end a voice interaction

**Overlay window**

- Small always-on-top panel with a button to switch modes manually
- Shows current active mode

## Remote camera (PC has no webcam)

If the PC running `main.py` has no camera, run the camera on another
device (e.g. a laptop) on the same network:

1. On the laptop: `python camera_server.py`
2. Find the laptop's local IP (`ipconfig` on Windows).
3. On the PC, in `config.py`, set:
   - `CAMERA_SOURCE = "remote"`
   - `REMOTE_CAMERA_URL = "http://<laptop-ip>:8080/video"`
4. Run `main.py` on the PC as usual.

Both devices must be on the same local network. If the PC and laptop
are in different locations/networks, use Tailscale instead:

### Tailscale setup (PC and laptop in different locations)

1. Sign up free at <https://tailscale.com>
2. Install Tailscale on **both** the laptop and the PC:
   - Windows: download from <https://tailscale.com/download>
3. Run Tailscale on both machines and log in with the same account.
4. On the laptop, find its Tailscale IP:
   - Open Tailscale app, or run `tailscale ip -4` in terminal
   - Looks like `100.x.x.x`
5. On the laptop, run `python camera_server.py` as usual.
6. On the PC, in `config.py`, use the Tailscale IP instead of the local one:
   - `REMOTE_CAMERA_URL = "http://100.x.x.x:8080/video"`
7. Run `main.py` on the PC.

No router or firewall port forwarding needed. Both devices just need
Tailscale running and logged into the same account.

## Notes

- Press `Esc` in the camera preview window to close it (app keeps running).
- Close the overlay window to fully exit the app.
- PyAudio may need `pip install pipwin` then `pipwin install pyaudio` on some Windows setups if the normal install fails.
