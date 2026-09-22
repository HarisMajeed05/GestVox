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


def installed_app_names():
    return list(_load_installed_apps().keys())


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


# ---------------------------------------------------------------------------
# Full PC access: PowerShell execution, radios, windows, keyboard, clipboard
# ---------------------------------------------------------------------------

import re as _re

# Commands matching these need a spoken "yes" before running
RISKY_PATTERNS = [
    r"\bremove-item\b", r"\bdel\b", r"\berase\b", r"\brm\b", r"\brmdir\b", r"\brd\b",
    r"\bformat\b", r"\bdiskpart\b", r"\bstop-computer\b", r"\brestart-computer\b",
    r"\bshutdown\b", r"\breg(?:\.exe)?\s+(?:delete|add)\b", r"\bremove-itemproperty\b",
    r"\bset-itemproperty\b", r"\bset-executionpolicy\b", r"\bbcdedit\b", r"\bcipher\b",
    r"\btakeown\b", r"\bicacls\b", r"\bnet\s+user\b", r"\buninstall", r"\bclear-recyclebin\b",
    r"\bdisable-netadapter\b", r"\bmove-item\b", r"\brename-item\b",
]

_pending_action = None  # (description, callable) waiting for spoken confirmation


def is_risky(command):
    lowered = command.lower()
    return any(_re.search(p, lowered) for p in RISKY_PATTERNS)


def request_confirmation(description, action):
    global _pending_action
    _pending_action = (description, action)
    return f"This will {description}. Say yes to confirm, or anything else to cancel."


def has_pending_action():
    return _pending_action is not None


def confirm_pending():
    global _pending_action
    if not _pending_action:
        return "Nothing is waiting for confirmation."
    _, action = _pending_action
    _pending_action = None
    return action()


def cancel_pending():
    global _pending_action
    _pending_action = None
    return "Cancelled."


def _powershell(script, timeout=30):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, timeout=timeout,
    )
    return (result.stdout or "").strip(), (result.stderr or "").strip()


def _execute_powershell(command):
    try:
        out, err = _powershell(command)
    except subprocess.TimeoutExpired:
        return "The command timed out."
    except Exception as e:
        return f"Command failed: {e}"
    text = out or err or "Done, no output."
    return text[:1500]  # keeps the AI context small for long outputs


def run_powershell(command, confirmed=False):
    # Runs any PowerShell command. Risky ones wait for spoken confirmation.
    if is_risky(command) and not confirmed:
        return request_confirmation(
            f"run the command: {command}", lambda: _execute_powershell(command)
        )
    return _execute_powershell(command)


# Windows radio control via WinRT, works without admin rights
_RADIO_SCRIPT = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}
[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$radio = $radios | ? { $_.Kind -eq '__KIND__' } | Select-Object -First 1
if (-not $radio) { Write-Output 'NOT_FOUND'; exit }
Await ($radio.SetStateAsync('__STATE__')) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
Write-Output 'OK'
"""


def _set_radio(kind, state):
    script = _RADIO_SCRIPT.replace("__KIND__", kind).replace("__STATE__", state)
    try:
        out, err = _powershell(script, timeout=20)
    except Exception as e:
        return f"Couldn't change {kind}: {e}"
    if "NOT_FOUND" in out:
        return f"No {kind} adapter found on this PC."
    if "OK" in out:
        return f"{kind} turned {state.lower()}."
    return f"Couldn't change {kind}. {err[:200]}"


def set_wifi(state):
    state = "On" if state.lower() == "on" else "Off"
    if state == "Off":
        # Voice control needs internet for speech recognition, so this is confirmed first
        return request_confirmation(
            "turn Wi-Fi off. Voice control will stop working until it's back on",
            lambda: _set_radio("WiFi", "Off"),
        )
    return _set_radio("WiFi", "On")


def set_bluetooth(state):
    state = "On" if state.lower() == "on" else "Off"
    return _set_radio("Bluetooth", state)


WINDOW_ACTIONS = {
    "show_desktop": (("win", "d"), "Showing the desktop."),
    "switch_window": (("alt", "tab"), "Switched window."),
    "maximize": (("win", "up"), "Maximized the window."),
    "minimize": (("win", "down"), "Minimized the window."),
    "snap_left": (("win", "left"), "Snapped the window left."),
    "snap_right": (("win", "right"), "Snapped the window right."),
    "close_window": (("alt", "f4"), "Closed the window."),
    "task_view": (("win", "tab"), "Opened task view."),
    "new_tab": (("ctrl", "t"), "Opened a new tab."),
    "close_tab": (("ctrl", "w"), "Closed the tab."),
}


def window_action(action):
    entry = WINDOW_ACTIONS.get(action)
    if not entry:
        return f"Unknown window action: {action}."
    keys, message = entry
    pyautogui.hotkey(*keys)
    return message


def press_keys(keys):
    # keys: combination like "ctrl+c" or a single key like "enter"
    parts = [k.strip().lower() for k in keys.replace(" ", "+").split("+") if k.strip()]
    if not parts:
        return "No keys given."
    pyautogui.hotkey(*parts)
    return f"Pressed {'+'.join(parts)}."


def get_clipboard():
    out, _ = _powershell("Get-Clipboard -Raw", timeout=10)
    return out[:1500] if out else "The clipboard is empty."


def set_clipboard(text):
    # Passing text through an environment variable avoids quoting problems
    env = dict(os.environ, GESTVOX_CLIP=text)
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $env:GESTVOX_CLIP"],
        env=env, capture_output=True, timeout=10,
    )
    return "Copied to clipboard."


def type_text(text):
    # Pastes through the clipboard, which handles any characters reliably
    set_clipboard(text)
    pyautogui.hotkey("ctrl", "v")
    return "Typed the text."


def get_weather(city=""):
    # wttr.in returns live weather as text; without a city it uses IP location
    import urllib.request
    import urllib.parse
    fmt = "%l: %C, %t (feels like %f), humidity %h, wind %w"
    url = f"https://wttr.in/{urllib.parse.quote(city.strip())}?format={urllib.parse.quote(fmt)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception as e:
        return f"Couldn't get the weather: {e}"