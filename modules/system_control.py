import os
import json
import difflib
import subprocess
import webbrowser
import ctypes
import pyautogui
import psutil
from datetime import datetime

pyautogui.PAUSE = 0

# Built-in Windows tools that have no Start Menu shortcut under a simple name
BUILTIN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "settings": "ms-settings:",
}

_app_cache = None


def _load_installed_apps():
    # Uses Windows' own Start apps list, which includes Microsoft Store apps
    # (e.g. Spotify) that have no .lnk shortcut. Maps lowercase name -> AppID.
    global _app_cache
    if _app_cache is None:
        _app_cache = {}
        try:
            output = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-StartApps | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15,
            ).stdout
            apps = json.loads(output) if output.strip() else []
            if isinstance(apps, dict):
                apps = [apps]
            for app in apps:
                name = (app.get("Name") or "").lower()
                if name and "uninstall" not in name:
                    _app_cache.setdefault(name, app.get("AppID"))
        except Exception as e:
            print(f"[System] Could not load installed apps: {e}")
    return _app_cache


def _find_app(app_name):
    apps = _load_installed_apps()
    if app_name in apps:
        return apps[app_name]
    starts = [n for n in apps if n.startswith(app_name)]
    words = [n for n in apps if app_name in n.split()]
    contains = [n for n in apps if app_name in n]
    candidates = starts or words or contains
    if candidates:
        return apps[min(candidates, key=len)]
    # Fuzzy match handles slight mishearings from speech-to-text
    close = difflib.get_close_matches(app_name, apps.keys(), n=1, cutoff=0.6)
    return apps[close[0]] if close else None


def _clean_name(app_name):
    return app_name.lower().strip(" .?!,")


def open_app(app_name):
    name = _clean_name(app_name)
    try:
        if name in BUILTIN_APPS:
            os.startfile(BUILTIN_APPS[name])
            return f"Opened {name}."
        app_id = _find_app(name)
        if app_id:
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
            return f"Opened {name}."
        if "." in name:
            return open_website(name)
    except Exception as e:
        return f"Couldn't open {name}: {e}"
    return f"I couldn't find an app called {name}."


def close_app(app_name):
    name = _clean_name(app_name)
    target = BUILTIN_APPS.get(name, "")
    search = name.replace(" ", "")
    killed = 0
    for proc in psutil.process_iter(["name"]):
        pname = (proc.info["name"] or "").lower()
        if (target and pname == target) or (not target and search in pname):
            try:
                proc.kill()
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    if killed:
        return f"Closed {name}."
    return f"{name} doesn't seem to be running."


def set_volume(action):
    # action: "up", "down", or "mute"
    key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}.get(action)
    if not key:
        return "Unknown volume action."
    presses = 5 if action in ("up", "down") else 1
    pyautogui.press(key, presses=presses)
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
    folder = os.path.join(os.path.expanduser("~"), "Pictures", "GestVox")
    os.makedirs(folder, exist_ok=True)
    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(folder, filename)
    pyautogui.screenshot().save(path)
    return "Screenshot saved in your Pictures folder, inside GestVox."


def open_website(url):
    url = url.strip(" .?!,")
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}."


def web_search(query):
    query = query.strip(" .?!,")
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searching the web for {query}."