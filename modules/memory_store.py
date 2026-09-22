import json
import os
from difflib import SequenceMatcher

SIMILARITY_REPLACE_THRESHOLD = 0.6

DEFAULT_MEMORY_FILE = "gestvox_memory.json"
MAX_HISTORY_MESSAGES = 40  # keep file small, older turns get dropped


class MemoryStore:
    def __init__(self, path=None):
        self._path = path or DEFAULT_MEMORY_FILE
        self._data = {"history": [], "facts": []}
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
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
        if fact in facts:
            return
        # A new fact similar to an old one is treated as a correction/update
        for i, existing in enumerate(facts):
            similarity = SequenceMatcher(None, existing.lower(), fact.lower()).ratio()
            if similarity >= SIMILARITY_REPLACE_THRESHOLD:
                facts[i] = fact
                self._save()
                return
        facts.append(fact)
        self._save()

    def clear(self):
        self._data = {"history": [], "facts": []}
        self._save()

    def switch_path(self, new_path):
        self._path = new_path
        self._data = {"history": [], "facts": []}
        self._load()