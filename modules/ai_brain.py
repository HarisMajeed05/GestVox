from groq import Groq
import config
from modules.memory_store import MemoryStore

BASE_SYSTEM_PROMPT = (
    "You are GestVox, a personal voice assistant running on the user's "
    "Windows PC, similar to Jarvis. Keep spoken replies short (1-3 "
    "sentences) unless asked for detail.\n\n"
    "After every reply, on a new line, output exactly one of:\n"
    "FACT: <a short, standalone fact worth remembering long-term about the "
    "user, their preferences, corrections they gave, or ongoing context>\n"
    "FACT: NONE\n"
    "Only save a real fact when something new and useful about the user or "
    "a correction was actually said. Don't save small talk or one-off "
    "requests with no lasting relevance."
)


class AIBrain:
    def __init__(self):
        self._client = Groq(api_key=config.GROQ_API_KEY)
        self._memory = MemoryStore()

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
        # Splits the spoken reply from the trailing FACT: line
        if "FACT:" not in raw_reply:
            return raw_reply.strip(), None
        reply_part, _, fact_part = raw_reply.rpartition("FACT:")
        reply_part = reply_part.strip()
        fact_part = fact_part.strip()
        if not fact_part or fact_part.upper() == "NONE":
            return reply_part, None
        return reply_part, fact_part

    def ask(self, user_text):
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self._memory.get_history())
        messages.append({"role": "user", "content": user_text})

        try:
            response = self._client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=messages,
                temperature=0.6,
                max_tokens=350,
            )
            raw_reply = response.choices[0].message.content.strip()
        except Exception as e:
            self._memory.add_turn("user", user_text)
            return f"I couldn't reach the AI service. {e}"

        reply, fact = self._parse_reply(raw_reply)
        if fact:
            self._memory.add_fact(fact)

        self._memory.add_turn("user", user_text)
        self._memory.add_turn("assistant", reply)
        return reply

    def reset(self):
        self._memory.clear()


ai_brain = AIBrain()