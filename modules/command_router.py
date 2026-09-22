import re
from modules import system_control as sc

FILLER_PREFIX = re.compile(
    r"^(?:(?:hey|ok|okay|so|please|can you|could you|would you|will you|"
    r"i want you to|i want to|go ahead and|just)\s+)+"
)
FILLER_SUFFIX = re.compile(r"(?:\s+(?:please|for me|now|right now))+$")


def normalize(text):
    # Lowercases, drops punctuation (keeps dots inside words like youtube.com)
    text = text.lower()
    text = re.sub(r"\.(?=\s|$)", " ", text)
    text = re.sub(r"[^\w\s.'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_fillers(text):
    text = FILLER_PREFIX.sub("", text).strip()
    return FILLER_SUFFIX.sub("", text).strip()


# Order matters: specific patterns are checked before the generic open/close ones
PATTERNS = [
    (r"^(?:search|google)(?: for)? (.+)$", lambda m: sc.web_search(m.group(1))),
    (r"^(?:open|go to|visit) (?:the )?(?:website )?(\S+\.\S+)$", lambda m: sc.open_website(m.group(1))),
    (r"^cancel (?:the )?(?:shutdown|restart)$", lambda m: sc.cancel_shutdown()),
    (r"^(?:shut ?down|turn off)(?: the)?(?: pc| computer)?$", lambda m: sc.shutdown_pc()),
    (r"^restart(?: the)?(?: pc| computer)?$", lambda m: sc.restart_pc()),
    (r"^lock(?: the)?(?: pc| computer| screen)?$", lambda m: sc.lock_pc()),
    (r"^(?:volume up|increase (?:the )?volume|turn (?:the )?volume up|turn up (?:the )?volume|louder)$",
     lambda m: sc.set_volume("up")),
    (r"^(?:volume down|decrease (?:the )?volume|lower (?:the )?volume|turn (?:the )?volume down|turn down (?:the )?volume|quieter)$",
     lambda m: sc.set_volume("down")),
    (r"^(?:mute|unmute)(?: (?:the )?(?:volume|sound|audio))?$", lambda m: sc.set_volume("mute")),
    (r"^(?:play|pause|resume)(?: (?:the )?(?:music|media|song|video))?$", lambda m: sc.media_control("play_pause")),
    (r"^(?:next|skip)(?: (?:track|song))?$", lambda m: sc.media_control("next")),
    (r"^(?:previous|last) (?:track|song)$", lambda m: sc.media_control("previous")),
    (r"^(?:what(?:'s| is) (?:the |my )?)?battery(?: level| percentage| status)?$", lambda m: sc.get_battery()),
    (r"^(?:what(?:'s| is) the time|what time is it|current time|time)$", lambda m: sc.get_time()),
    (r"^(?:take (?:a )?)?screenshot$|^capture (?:the )?screen$", lambda m: sc.take_screenshot()),
    (r"^turn (on|off) (?:the )?wi-?fi$|^wi-?fi (on|off)$",
     lambda m: sc.set_wifi(m.group(1) or m.group(2))),
    (r"^turn (on|off) (?:the )?bluetooth$|^bluetooth (on|off)$",
     lambda m: sc.set_bluetooth(m.group(1) or m.group(2))),
    (r"^(?:show (?:the )?desktop|minimize (?:all|everything))$", lambda m: sc.window_action("show_desktop")),
    (r"^(?:switch|change) (?:the )?(?:window|app)$", lambda m: sc.window_action("switch_window")),
    (r"^maximize(?: (?:the |this )?window)?$", lambda m: sc.window_action("maximize")),
    (r"^minimize(?: (?:the |this )?window)?$", lambda m: sc.window_action("minimize")),
    (r"^snap (?:the )?(?:window )?(left|right)$", lambda m: sc.window_action(f"snap_{m.group(1)}")),
    (r"^close (?:the |this )?window$", lambda m: sc.window_action("close_window")),
    (r"^(?:open )?(?:a )?new tab$", lambda m: sc.window_action("new_tab")),
    (r"^close (?:the |this )?tab$", lambda m: sc.window_action("close_tab")),
    (r"^(?:type|write) (.+)$", lambda m: sc.type_text(m.group(1))),
    (r"^(?:close|quit|exit|kill) (.+)$", lambda m: sc.close_app(m.group(1))),
    (r"^(?:open|launch|start|run) (.+)$", lambda m: sc.open_app(m.group(1))),
]
PATTERNS = [(re.compile(p), h) for p, h in PATTERNS]


def try_handle(text):
    """Returns a result string if a known command matched, otherwise None
    so the caller can fall back to the AI."""
    cleaned = _strip_fillers(normalize(text))
    for pattern, handler in PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return handler(match)
    return None