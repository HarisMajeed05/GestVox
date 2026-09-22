from groq import Groq
import config

SYSTEM_PROMPT = (
    "You are GestVox, a concise voice assistant running on the user's "
    "Windows PC. Keep answers short and spoken-friendly (1-3 sentences) "
    "unless the user asks for detail. If asked to perform a system action "
    "you cannot do, say so briefly."
)


class AIBrain:
    def __init__(self):
        self._client = Groq(api_key=config.GROQ_API_KEY)
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask(self, user_text):
        self._history.append({"role": "user", "content": user_text})
        # Keep history bounded so requests stay small and fast
        if len(self._history) > 20:
            self._history = [self._history[0]] + self._history[-18:]

        try:
            response = self._client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=self._history,
                temperature=0.6,
                max_tokens=300,
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            reply = f"I couldn't reach the AI service. {e}"

        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]


ai_brain = AIBrain()
