import os
import json
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

USERS_DIR = "users"
MATCH_THRESHOLD = 0.75  # cosine similarity; raise for stricter matching

_encoder = None


def _get_encoder():
    # Loaded lazily so the model only loads once actually needed
    global _encoder
    if _encoder is None:
        _encoder = VoiceEncoder()
    return _encoder


def _user_dir(username):
    path = os.path.join(USERS_DIR, username)
    os.makedirs(path, exist_ok=True)
    return path


def _embed_from_wav(wav_path):
    wav = preprocess_wav(wav_path)
    return _get_encoder().embed_utterance(wav)


def enroll_user(username, wav_path):
    embedding = _embed_from_wav(wav_path)
    path = _user_dir(username)
    np.save(os.path.join(path, "voice_embedding.npy"), embedding)
    settings_path = os.path.join(path, "settings.json")
    if not os.path.exists(settings_path):
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump({"username": username}, f, indent=2)
    return True


def list_users():
    if not os.path.exists(USERS_DIR):
        return []
    return [
        name for name in os.listdir(USERS_DIR)
        if os.path.exists(os.path.join(USERS_DIR, name, "voice_embedding.npy"))
    ]


def identify_user(wav_path):
    # Returns (username, similarity) of the best match above threshold,
    # or (None, best_similarity) if nobody matches closely enough.
    try:
        sample_embedding = _embed_from_wav(wav_path)
    except Exception:
        return None, 0.0

    best_user, best_score = None, 0.0
    for username in list_users():
        stored = np.load(os.path.join(USERS_DIR, username, "voice_embedding.npy"))
        score = float(np.dot(sample_embedding, stored) /
                       (np.linalg.norm(sample_embedding) * np.linalg.norm(stored)))
        if score > best_score:
            best_user, best_score = username, score

    if best_score >= MATCH_THRESHOLD:
        return best_user, best_score
    return None, best_score