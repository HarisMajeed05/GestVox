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

## Notes

- Press `Esc` in the camera preview window to close it (app keeps running).
- Close the overlay window to fully exit the app.
- PyAudio may need `pip install pipwin` then `pipwin install pyaudio` on some Windows setups if the normal install fails.
