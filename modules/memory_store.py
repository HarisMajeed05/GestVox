import json
import os

MEMORY_FILE = "gestvox_memory.json"
MAX_HISTORY_MESSAGES = 40  # keep file small, older turns get dropped


class MemoryStore:
    def __init__(self, path=MEMORY_FILE):
        self._path = path
        self._data = {"history": [], "facts": []}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {"history": [], "facts": []}

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get_history(self):
        return self._data.get("history", [])

    def add_turn(self, role, content):
        self._data.setdefault("history", []).append(
            {"role": role, "content": content}
        )
        self._data["history"] = self._data["history"][-MAX_HISTORY_MESSAGES:]
        self._save()

    def get_facts(self):
        return self._data.get("facts", [])

    def add_fact(self, fact):
        facts = self._data.setdefault("facts", [])
        if fact not in facts:
            facts.append(fact)
            self._save()

    def clear(self):
        self._data = {"history": [], "facts": []}
        self._save()