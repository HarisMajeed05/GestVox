import re
from modules import system_control as sc

FILLER_PREFIX = re.compile(
    r"^(?:(?:hey|ok|okay|so|please|can you|could you|would you|will you|"
    r"i want you to|i want to|go ahead and|just|zara|ذرا|acha|اچھا)\s+)+"
)
FILLER_SUFFIX = re.compile(
    r"(?:\s+(?:please|for me|now|right now|karo|کرو|kar do|کر دو|de|دو))+$")


def normalize(text):
    # Lowercases, drops punctuation (keeps dots inside words like youtube.com)
    text = text.lower()
    text = re.sub(r"\.(?=\s|$)", " ", text)
    text = re.sub(r"[^\w\s.'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_fillers(text):
    text = FILLER_PREFIX.sub("", text).strip()
    return FILLER_SUFFIX.sub("", text).strip()



# Roman Urdu, Urdu script and Punjabi equivalents of the common commands.
# They map to the same handlers as the English ones.
URDU_PATTERNS = [
    (r"^(.+?) (?:kholo|kholain|khol do|open karo)$|^(?:kholo|open karo) (.+)$",
     lambda m: sc.open_app(m.group(1) or m.group(2))),
    (r"^(.+?) (?:کھولو|کھولیں|کھول دو)$", lambda m: sc.open_app(m.group(1))),
    (r"^(.+?) (?:band karo|band kar do|close karo)$", lambda m: sc.close_app(m.group(1))),
    (r"^(.+?) (?:بند کرو|بند کر دو)$", lambda m: sc.close_app(m.group(1))),
    (r"^(?:awaz|awaaz|volume) (?:barhao|barha do|tez karo|zyada karo)$|^آواز (?:بڑھاؤ|تیز کرو)$",
     lambda m: sc.set_volume("up")),
    (r"^(?:awaz|awaaz|volume) (?:kam karo|ghata do|halka karo)$|^آواز (?:کم کرو|گھٹا دو)$",
     lambda m: sc.set_volume("down")),
    (r"^(?:awaz|awaaz) (?:band karo|khatam karo)$|^چپ|^آواز بند$", lambda m: sc.set_volume("mute")),
    (r"^(?:screenshot|screen shot) (?:lo|le lo|karo)$|^اسکرین شاٹ", lambda m: sc.take_screenshot()),
    (r"^(?:wifi|wi-fi) (?:chalu karo|on karo)$|^وائی فائی (?:چالو|آن)", lambda m: sc.set_wifi("on")),
    (r"^(?:wifi|wi-fi) (?:band karo|off karo)$|^وائی فائی (?:بند|آف)", lambda m: sc.set_wifi("off")),
    (r"^(?:screen |pc |computer )?lock karo$|^(?:اسکرین |پی سی )?لاک کرو$", lambda m: sc.lock_pc()),
    (r"^(?:waqt|time) kya (?:hai|hoya)$|^کیا (?:وقت|ٹائم) ہے$|^وقت کیا ہے$", lambda m: sc.get_time()),
    (r"^(?:mausam|mosam) (?:kaisa hai|kya hai)$|^موسم (?:کیسا|کیا) ہے$", lambda m: sc.get_weather()),
    (r"^battery kitni hai$|^بیٹری (?:کتنی|کیا) ہے$", lambda m: sc.get_battery()),
    (r"^(?:gana|music) (?:chalao|lagao)$|^گانا (?:چلاؤ|لگاؤ)$", lambda m: sc.media_control("play_pause")),
    (r"^(?:agla|next) gana$|^اگلا گانا$", lambda m: sc.media_control("next")),
    (r"^(?:pichla|previous) gana$|^پچھلا گانا$", lambda m: sc.media_control("previous")),
    (r"^copy karo$|^کاپی کرو$", lambda m: sc.hotkey_action("copy")),
    (r"^paste karo$|^پیسٹ کرو$", lambda m: sc.hotkey_action("paste")),
    (r"^(?:wapas jao|peeche jao)$|^(?:واپس|پیچھے) جاؤ$", lambda m: sc.hotkey_action("back")),
    (r"^(?:youtube (?:par|pe) )?(.+?) (?:chalao|lagao)$", lambda m: sc.youtube_search(m.group(1))),
    (r"^(\d+) minute ka timer (?:lagao|set karo)$|^(\d+) منٹ کا ٹائمر",
     lambda m: sc.set_timer(m.group(1) or m.group(2))),
]

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
    (r"^(?:copy|copy that|copy it)$", lambda m: sc.hotkey_action("copy")),
    (r"^paste$", lambda m: sc.hotkey_action("paste")),
    (r"^cut$", lambda m: sc.hotkey_action("cut")),
    (r"^undo(?: that)?$", lambda m: sc.hotkey_action("undo")),
    (r"^redo$", lambda m: sc.hotkey_action("redo")),
    (r"^select all$", lambda m: sc.hotkey_action("select_all")),
    (r"^save(?: (?:it|this|the file))?$", lambda m: sc.hotkey_action("save")),
    (r"^(?:find|search) (?:on |in )?(?:this )?page$", lambda m: sc.hotkey_action("find")),
    (r"^print(?: this| it)?$", lambda m: sc.hotkey_action("print")),
    (r"^(?:refresh|reload)(?: (?:the )?page)?$", lambda m: sc.hotkey_action("refresh")),
    (r"^(?:go )?back$", lambda m: sc.hotkey_action("back")),
    (r"^(?:go )?forward$", lambda m: sc.hotkey_action("forward")),
    (r"^zoom in$", lambda m: sc.hotkey_action("zoom_in")),
    (r"^zoom out$", lambda m: sc.hotkey_action("zoom_out")),
    (r"^reset (?:the )?zoom$", lambda m: sc.hotkey_action("zoom_reset")),
    (r"^(?:open )?(?:a )?new window$", lambda m: sc.hotkey_action("new_window")),
    (r"^reopen (?:the )?(?:last )?tab$", lambda m: sc.hotkey_action("reopen_tab")),
    (r"^(?:next|switch) tab$", lambda m: sc.hotkey_action("next_tab")),
    (r"^press enter$|^enter$", lambda m: sc.hotkey_action("enter")),
    (r"^press escape$|^escape$", lambda m: sc.hotkey_action("escape")),
    (r"^(?:play|search) (.+) on youtube$", lambda m: sc.youtube_search(m.group(1))),
    (r"^(?:search )?youtube (?:for )?(.+)$", lambda m: sc.youtube_search(m.group(1))),
    (r"^set (?:a )?timer (?:for )?(\d+(?:\.\d+)?) ?(?:minutes?|mins?)(?: for (.+))?$",
     lambda m: sc.set_timer(m.group(1), m.group(2) or "")),
    (r"^(?:take|make|write) (?:a )?note[:,]? (.+)$", lambda m: sc.take_note(m.group(1))),
    (r"^(?:read|what are) (?:my )?(?:latest )?notes$", lambda m: sc.read_notes()),
    (r"^(?:system|pc) (?:info|status|usage)$|^how(?:'s| is) my (?:pc|system)$",
     lambda m: sc.system_info()),
    (r"^(?:disk|drive|storage) space$|^how much (?:disk |storage )?space", lambda m: sc.disk_space()),
    (r"^(?:what(?:'s| is) )?my ip(?: address)?$", lambda m: sc.get_ip()),
    (r"^(?:set )?brightness (?:to )?(\d+)(?: percent)?$", lambda m: sc.set_brightness(m.group(1))),
    (r"^(?:switch to |turn on )?(dark|light) mode$", lambda m: sc.toggle_dark_mode(m.group(1))),
    (r"^(?:go to )?sleep$|^sleep (?:the )?(?:pc|computer)$", lambda m: sc.sleep_pc()),
    (r"^(?:log|sign) (?:me )?(?:off|out)$", lambda m: sc.log_off()),
    (r"^empty (?:the )?(?:recycle bin|trash)$", lambda m: sc.empty_recycle_bin()),
    (r"^find (?:the )?file (.+)$", lambda m: sc.find_file(m.group(1))),
    (r"^open settings$", lambda m: sc.open_settings_page()),
    (r"^(?:what(?:'s| is) the )?weather(?: in (.+)| today| now)?$",
     lambda m: sc.get_weather(m.group(1) or "")),
    (r"^(?:read|what(?:'s| is) (?:on|in)) (?:my )?clipboard$", lambda m: sc.get_clipboard()),
    (r"^(?:open|go to) (youtube|gmail|google|github|chatgpt|whatsapp|linkedin|netflix|amazon|reddit|maps|drive)$",
     lambda m: sc.open_site(m.group(1))),
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
PATTERNS = [(re.compile(p), h) for p, h in PATTERNS + URDU_PATTERNS]


def try_handle(text):
    """Returns a result string if a known command matched, otherwise None
    so the caller can fall back to the AI."""
    cleaned = _strip_fillers(normalize(text))
    for pattern, handler in PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return handler(match)
    return None