from modules.mode_manager import mode_manager
from modules.gesture_control import GestureControl
from modules.voice_control import VoiceControl
from modules.auth_flow import run_login_flow
from ui.overlay import Overlay
import config


def main():
    if not config.GROQ_API_KEY:
        print("Warning: GROQ_API_KEY not set. Add it to a .env file. "
              "Conversational replies will fail without it.")

    if config.VOICE_LOGIN_ENABLED:
        run_login_flow()

    gesture = GestureControl(toggle_callback=mode_manager.toggle_mode)
    voice = VoiceControl(toggle_callback=mode_manager.toggle_mode)

    gesture.start()
    voice.start()

    overlay = Overlay()
    overlay.run()  # blocks until window closed

    gesture.stop()
    voice.stop()


if __name__ == "__main__":
    main()