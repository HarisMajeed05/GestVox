import json
from groq import Groq
import config
from modules.memory_store import MemoryStore
from modules.user_session import user_session
from modules import system_control as sc
from modules import auth_flow

BASE_SYSTEM_PROMPT = (
    "You are GestVox, a personal voice assistant running on the user's "
    "Windows PC, similar to Jarvis. Keep spoken replies short (1-3 "
    "sentences) unless asked for detail. Use the available tools whenever "
    "the user asks you to control the PC (open/close apps, volume, media, "
    "lock, shutdown, restart, battery, time, screenshot, open a website, "
    "web search). Don't ask for confirmation on reversible actions; only "
    "confirm before shutdown or restart if the request is ambiguous.\n\n"
    "After every reply, on a new line, output exactly one of:\n"
    "FACT: <a short, standalone fact worth remembering long-term about the "
    "user, their preferences, corrections they gave, or ongoing context>\n"
    "FACT: NONE\n"
    "Only save a real fact when something new and useful was actually "
    "said. Don't save small talk or one-off requests with no lasting "
    "relevance."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "open_app", "description": "Open a known desktop app.",
        "parameters": {"type": "object", "properties": {
            "app_name": {"type": "string", "description": "e.g. notepad, chrome, calculator, explorer, paint, task manager, cmd"}
        }, "required": ["app_name"]},
    }},
    {"type": "function", "function": {
        "name": "close_app", "description": "Close a known running app.",
        "parameters": {"type": "object", "properties": {
            "app_name": {"type": "string"}
        }, "required": ["app_name"]},
    }},
    {"type": "function", "function": {
        "name": "set_volume", "description": "Change system volume.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["up", "down", "mute"]}
        }, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "media_control", "description": "Control media playback.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["play_pause", "next", "previous"]}
        }, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "lock_pc", "description": "Lock the PC screen.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "shutdown_pc", "description": "Shut down the PC.",
        "parameters": {"type": "object", "properties": {
            "seconds": {"type": "integer", "description": "delay before shutdown"}
        }},
    }},
    {"type": "function", "function": {
        "name": "cancel_shutdown", "description": "Cancel a pending shutdown or restart.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "restart_pc", "description": "Restart the PC.",
        "parameters": {"type": "object", "properties": {
            "seconds": {"type": "integer"}
        }},
    }},
    {"type": "function", "function": {
        "name": "get_battery", "description": "Get battery percentage and charging status.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_time", "description": "Get the current date and time.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "take_screenshot", "description": "Take a screenshot and save it.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "open_website", "description": "Open a specific website by URL.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}
        }, "required": ["url"]},
    }},
    {"type": "function", "function": {
        "name": "web_search", "description": "Search the web for a query.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}
        }, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "create_voice_profile", "description": "Register a new user's voice profile for login.",
        "parameters": {"type": "object", "properties": {
            "username": {"type": "string"}
        }, "required": ["username"]},
    }},
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
    "web_search": lambda a: sc.web_search(a["query"]),
    "create_voice_profile": lambda a: auth_flow.enroll_new_user(a["username"]),
}


class AIBrain:
    def __init__(self):
        self._client = Groq(api_key=config.GROQ_API_KEY)
        self._memory = MemoryStore(user_session.memory_path())
        user_session.on_change(lambda _user: self._memory.switch_path(user_session.memory_path()))

    def _build_system_prompt(self):
        facts = self._memory.get_facts()
        if not facts:
            return BASE_SYSTEM_PROMPT
        facts_block = "\n".join(f"- {f}" for f in facts)
        return (
            f"{BASE_SYSTEM_PROMPT}\n\n"
            f"Known facts about the user so far, treat these as true:\n"
            f"{facts_block}"
        )

    def _parse_reply(self, raw_reply):
        if not raw_reply or "FACT:" not in raw_reply:
            return (raw_reply or "").strip(), None
        reply_part, _, fact_part = raw_reply.rpartition("FACT:")
        reply_part = reply_part.strip()
        fact_part = fact_part.strip()
        if not fact_part or fact_part.upper() == "NONE":
            return reply_part, None
        return reply_part, fact_part

    def _run_tool_calls(self, tool_calls):
        results = []
        for call in tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = FUNCTION_MAP.get(name)
            output = handler(args) if handler else f"Unknown tool: {name}"
            results.append({
                "tool_call_id": call.id, "role": "tool",
                "name": name, "content": str(output),
            })
        return results

    def ask(self, user_text):
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self._memory.get_history())
        messages.append({"role": "user", "content": user_text})

        try:
            response = self._client.chat.completions.create(
                model=config.GROQ_MODEL, messages=messages,
                tools=TOOLS, tool_choice="auto", temperature=0.5, max_tokens=350,
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg)
                messages.extend(self._run_tool_calls(msg.tool_calls))
                follow_up = self._client.chat.completions.create(
                    model=config.GROQ_MODEL, messages=messages,
                    temperature=0.5, max_tokens=200,
                )
                raw_reply = follow_up.choices[0].message.content.strip()
            else:
                raw_reply = (msg.content or "").strip()
        except Exception as e:
            self._memory.add_turn("user", user_text)
            return f"I couldn't reach the AI service. {e}"

        reply, fact = self._parse_reply(raw_reply)
        if fact:
            self._memory.add_fact(fact)

        self._memory.add_turn("user", user_text)
        self._memory.add_turn("assistant", reply)
        return reply

    def record_exchange(self, user_text, reply):
        # Saves locally handled commands so follow-up questions have context
        self._memory.add_turn("user", user_text)
        self._memory.add_turn("assistant", reply)

    def reset(self):
        self._memory.clear()


ai_brain = AIBrain()