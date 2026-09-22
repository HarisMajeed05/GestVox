import os
import subprocess
import webbrowser
import ctypes
import pyautogui
import psutil
from datetime import datetime

KNOWN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "brave": "brave.exe",
    "browser": "brave.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
}


def open_app(app_name):
    exe = KNOWN_APPS.get(app_name.lower().strip())
    if not exe:
        return f"I don't know how to open '{app_name}'."
    try:
        subprocess.Popen(exe, shell=True)
        return f"Opened {app_name}."
    except Exception as e:
        return f"Couldn't open {app_name}: {e}"


def close_app(app_name):
    exe = KNOWN_APPS.get(app_name.lower().strip())
    if not exe:
        return f"I don't know how to close '{app_name}'."
    try:
        subprocess.run(["taskkill", "/f", "/im", exe], check=False)
        return f"Closed {app_name}."
    except Exception as e:
        return f"Couldn't close {app_name}: {e}"


def set_volume(action):
    # action: "up", "down", or "mute"
    key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}.get(action)
    if not key:
        return "Unknown volume action."
    pyautogui.press(key)
    return f"Volume {action}."


def media_control(action):
    # action: "play_pause", "next", "previous"
    key = {
        "play_pause": "playpause", "next": "nexttrack", "previous": "prevtrack",
    }.get(action)
    if not key:
        return "Unknown media action."
    pyautogui.press(key)
    return f"Media {action.replace('_', ' ')}."


def lock_pc():
    ctypes.windll.user32.LockWorkStation()
    return "Locking the PC."


def shutdown_pc(seconds=10):
    os.system(f"shutdown /s /t {seconds}")
    return f"Shutting down in {seconds} seconds. Say 'cancel shutdown' to stop it."


def cancel_shutdown():
    os.system("shutdown /a")
    return "Shutdown cancelled."


def restart_pc(seconds=10):
    os.system(f"shutdown /r /t {seconds}")
    return f"Restarting in {seconds} seconds."


def get_battery():
    battery = psutil.sensors_battery()
    if not battery:
        return "No battery detected, likely a desktop."
    plugged = "charging" if battery.power_plugged else "on battery"
    return f"Battery is at {battery.percent} percent, {plugged}."

def get_time():
    return datetime.now().strftime("It's %I:%M %p on %A, %B %d.")


def take_screenshot():
    path = os.path.join(os.path.expanduser("~"), "Pictures", "gestvox_screenshot.png")
    pyautogui.screenshot().save(path)
    return f"Screenshot saved to {path}."


def open_website(url):
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}."


def web_search(query):
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searching the web for {query}."