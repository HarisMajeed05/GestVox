import re
import json
from groq import Groq
import config
from modules.memory_store import MemoryStore
from modules.user_session import user_session
from modules import system_control as sc
from modules import auth_flow

BASE_SYSTEM_PROMPT = (
    "You are GestVox, a personal voice assistant running on the user's "
    "Windows PC, similar to Jarvis. Your replies are spoken aloud, so keep "
    "them short (1-3 sentences), plain text, no markdown, no lists, no "
    "emojis, unless the user asks for detail. Use the available tools "
    "whenever the user asks you to control the PC. You have full access to "
    "the PC through run_powershell: for anything without a dedicated tool "
    "(files, folders, settings, system info, processes, network, installed "
    "programs), write a Windows PowerShell 5.1 command and run it, then "
    "summarize the result in plain words. Prefer dedicated tools when one "
    "fits. If a tool result asks the user to say yes to confirm, pass that "
    "question to the user as is. Never make up live data such as weather, "
    "news, or prices: use get_weather for weather, and for other live info "
    "use web_search, which only opens results in the browser for the user "
    "to read, since you can't see them.\n\n"
    "After every reply, on a new line, output exactly one of:\n"
    "FACT: <a short, standalone fact worth remembering long-term about the "
    "user, their preferences, corrections they gave, or ongoing context>\n"
    "FACT: NONE\n"
    "Only save a real fact when something new and useful was actually "
    "said. Don't save small talk or one-off requests."
)

MAX_TOOL_ROUNDS = 5
SENTENCE_END = re.compile(r"(.+?[.!?])(\s|$)", re.S)


def _split_sentences(buffer):
    """Pulls complete sentences off the front of a growing text buffer so
    they can be spoken while the rest is still being generated."""
    sentences = []
    while True:
        match = SENTENCE_END.match(buffer)
        if not match:
            break
        sentences.append(match.group(1).strip())
        buffer = buffer[match.end():]
    return sentences, buffer


def _tool(name, description, properties=None, required=None):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {},
                       "required": required or []},
    }}


TOOLS = [
    _tool("open_app", "Open any installed app by name (e.g. brave, spotify, notepad).",
          {"app_name": {"type": "string"}}, ["app_name"]),
    _tool("close_app", "Close a running app by name.",
          {"app_name": {"type": "string"}}, ["app_name"]),
    _tool("set_volume", "Change system volume.",
          {"action": {"type": "string", "enum": ["up", "down", "mute"]}}, ["action"]),
    _tool("media_control", "Control media playback.",
          {"action": {"type": "string", "enum": ["play_pause", "next", "previous"]}}, ["action"]),
    _tool("lock_pc", "Lock the PC screen."),
    _tool("shutdown_pc", "Shut down the PC.",
          {"seconds": {"type": "integer", "description": "delay before shutdown"}}),
    _tool("cancel_shutdown", "Cancel a pending shutdown or restart."),
    _tool("restart_pc", "Restart the PC.", {"seconds": {"type": "integer"}}),
    _tool("get_battery", "Get battery percentage and charging status."),
    _tool("get_time", "Get the current date and time."),
    _tool("take_screenshot", "Take a screenshot and save it to Pictures/GestVox."),
    _tool("open_website", "Open a specific website by URL.",
          {"url": {"type": "string"}}, ["url"]),
    _tool("get_weather", "Get live current weather. Leave city empty for the user's location.",
          {"city": {"type": "string"}}),
    _tool("web_search", "Open a web search in the browser for the user to read. "
          "You cannot see the results.",
          {"query": {"type": "string"}}, ["query"]),
    _tool("run_powershell", "Run any Windows PowerShell command on the PC and get its output. "
          "Use for anything without a dedicated tool.",
          {"command": {"type": "string", "description": "PowerShell 5.1 command"}}, ["command"]),
    _tool("set_wifi", "Turn Wi-Fi on or off.",
          {"state": {"type": "string", "enum": ["on", "off"]}}, ["state"]),
    _tool("set_bluetooth", "Turn Bluetooth on or off.",
          {"state": {"type": "string", "enum": ["on", "off"]}}, ["state"]),
    _tool("window_action", "Control windows and tabs.",
          {"action": {"type": "string", "enum": list(sc.WINDOW_ACTIONS.keys())}}, ["action"]),
    _tool("press_keys", "Press a key or shortcut, e.g. 'ctrl+c', 'enter', 'win+e'.",
          {"keys": {"type": "string"}}, ["keys"]),
    _tool("type_text", "Type text into the focused window.",
          {"text": {"type": "string"}}, ["text"]),
    _tool("get_clipboard", "Read the clipboard text."),
    _tool("set_clipboard", "Copy text to the clipboard.",
          {"text": {"type": "string"}}, ["text"]),
    _tool("create_voice_profile", "Register a new user's voice profile for login.",
          {"username": {"type": "string"}}, ["username"]),
]

FUNCTION_MAP = {
    "open_app": lambda a: sc.open_app(a["app_name"]),
    "close_app": lambda a: sc.close_app(a["app_name"]),
    "set_volume": lambda a: sc.set_volume(a["action"]),
    "media_control": lambda a: sc.media_control(a["action"]),
    "lock_pc": lambda a: sc.lock_pc(),
    "shutdown_pc": lambda a: sc.shutdown_pc(a.get("seconds", 10)),
    "cancel_shutdown": lambda a: sc.cancel_shutdown(),
    "restart_pc": lambda a: sc.restart_pc(a.get("seconds", 10)),
    "get_battery": lambda a: sc.get_battery(),
    "get_time": lambda a: sc.get_time(),
    "take_screenshot": lambda a: sc.take_screenshot(),
    "open_website": lambda a: sc.open_website(a["url"]),
    "get_weather": lambda a: sc.get_weather(a.get("city", "")),
    "web_search": lambda a: sc.web_search(a["query"]),
    "run_powershell": lambda a: sc.run_powershell(a["command"]),
    "set_wifi": lambda a: sc.set_wifi(a["state"]),
    "set_bluetooth": lambda a: sc.set_bluetooth(a["state"]),
    "window_action": lambda a: sc.window_action(a["action"]),
    "press_keys": lambda a: sc.press_keys(a["keys"]),
    "type_text": lambda a: sc.type_text(a["text"]),
    "get_clipboard": lambda a: sc.get_clipboard(),
    "set_clipboard": lambda a: sc.set_clipboard(a["text"]),
    "create_voice_profile": lambda a: auth_flow.enroll_new_user(a["username"]),
}


class _ToolFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    # Matches the shape of a non-streamed tool call, so both paths share code
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = _ToolFunction(name, arguments)


class AIBrain:
    def __init__(self):
        self._client = Groq(api_key=config.GROQ_API_KEY)
        self._memory = MemoryStore(user_session.memory_path())
        user_session.on_change(lambda _user: self._memory.switch_path(user_session.memory_path()))

    def _build_system_prompt(self):
        prompt = BASE_SYSTEM_PROMPT
        username = user_session.get_user()
        if username:
            prompt += (f"\n\nThe current user was identified by voice login. "
                       f"Their name is {username.capitalize()}.")
        facts = self._memory.get_facts()
        if facts:
            facts_block = "\n".join(f"- {f}" for f in facts)
            prompt += f"\n\nKnown facts about the user so far, treat these as true:\n{facts_block}"
        return prompt

    def _parse_reply(self, raw_reply):
        # Splits off the trailing "FACT:" line (any case) so it's never spoken
        raw_reply = (raw_reply or "").strip()
        matches = list(re.finditer(r"fact\s*:", raw_reply, flags=re.I))
        if not matches:
            return raw_reply, None
        cut = matches[-1]
        reply_part = raw_reply[:cut.start()].strip()
        fact_part = raw_reply[cut.end():].strip().strip(".")
        if not fact_part or fact_part.upper().startswith("NONE"):
            return reply_part, None
        return reply_part, fact_part

    def _complete(self, messages, stream=False):
        # reasoning_effort goes through extra_body so it works on any SDK version.
        # Tools are passed on every round, since gpt-oss errors if it tries to
        # call a tool on a request that has none.
        return self._client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.5,
            max_tokens=1024,
            stream=stream,
            extra_body={"reasoning_effort": config.GROQ_REASONING_EFFORT,
                        "include_reasoning": False},
        )

    def _run_tool_calls(self, tool_calls):
        results = []
        for call in tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = FUNCTION_MAP.get(name)
            try:
                output = handler(args) if handler else f"Unknown tool: {name}"
            except Exception as e:
                output = f"Tool {name} failed: {e}"
            print(f"[AI] Tool {name}({args}) -> {output}")
            results.append({"role": "tool", "tool_call_id": call.id,
                            "name": name, "content": str(output)})
        return results

    def _stream_round(self, messages, on_sentence):
        """Streams one reply, speaking each finished sentence as it arrives.
        Returns (text, tool_calls, spoken_chars)."""
        content, buffer, spoken = "", "", 0
        calls = {}
        for chunk in self._complete(messages, stream=True):
            delta = chunk.choices[0].delta
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    entry = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        entry["id"] = tc.id
                    if tc.function and tc.function.name:
                        entry["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        entry["args"] += tc.function.arguments
            if not delta.content:
                continue
            content += delta.content
            buffer += delta.content
            # The trailing FACT line is internal, so nothing is spoken once it starts
            if re.search(r"fact\s*:", buffer, re.I):
                continue
            sentences, buffer = _split_sentences(buffer)
            for sentence in sentences:
                on_sentence(sentence)
                spoken += len(sentence)
        return content, calls, spoken

    def ask(self, user_text, on_sentence=None):
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self._memory.get_history())
        messages.append({"role": "user", "content": user_text})

        raw_reply, spoken_chars = "", 0
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                if on_sentence:
                    raw_reply, calls, spoken_chars = self._stream_round(messages, on_sentence)
                    tool_calls = [
                        _ToolCall(c["id"], c["name"], c["args"])
                        for c in calls.values() if c["name"]
                    ]
                else:
                    msg = self._complete(messages).choices[0].message
                    raw_reply = (msg.content or "").strip()
                    tool_calls = msg.tool_calls or []

                if not tool_calls:
                    break
                messages.append({
                    "role": "assistant",
                    "content": raw_reply,
                    "tool_calls": [
                        {"id": c.id, "type": "function",
                         "function": {"name": c.function.name,
                                      "arguments": c.function.arguments or "{}"}}
                        for c in tool_calls
                    ],
                })
                messages.extend(self._run_tool_calls(tool_calls))
        except Exception as e:
            print(f"[AI] Request failed: {e}")
            message = "Sorry, I couldn't reach the AI service."
            if on_sentence:
                on_sentence(message)
            return message

        reply, fact = self._parse_reply(raw_reply)
        if not reply:
            reply = "Done."
        # Speaks whatever was left over after the last complete sentence
        if on_sentence:
            remainder = reply[spoken_chars:].strip() if spoken_chars else reply
            if remainder:
                on_sentence(remainder)
        if fact:
            self._memory.add_fact(fact)

        self.record_exchange(user_text, reply)
        return reply

    def record_exchange(self, user_text, reply):
        # Saves locally handled commands too, so follow-up questions have context
        self._memory.add_turn("user", user_text)
        self._memory.add_turn("assistant", reply)

    def reset(self):
        self._memory.clear()


ai_brain = AIBrain()