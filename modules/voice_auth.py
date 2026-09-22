import os
import json
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

USERS_DIR = "users"
MATCH_THRESHOLD = 0.65   # cosine similarity; raise for stricter matching
UPDATE_WEIGHT = 0.2      # how much each successful login adapts the profile

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


def _embedding_path(username):
    return os.path.join(USERS_DIR, username, "voice_embedding.npy")


def _embed_from_wav(wav_path):
    wav = preprocess_wav(wav_path)
    return _get_encoder().embed_utterance(wav)


def _normalize(vec):
    return vec / (np.linalg.norm(vec) or 1)


def enroll_user(username, wav_paths):
    # Accepts one path or a list; averaging several samples gives a more
    # stable profile, especially with low-quality Bluetooth mics.
    if isinstance(wav_paths, str):
        wav_paths = [wav_paths]
    embeddings = [_embed_from_wav(p) for p in wav_paths]
    embedding = _normalize(np.mean(embeddings, axis=0))
    path = _user_dir(username)
    np.save(_embedding_path(username), embedding)
    settings_path = os.path.join(path, "settings.json")
    if not os.path.exists(settings_path):
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump({"username": username}, f, indent=2)
    return True


def update_profile(username, wav_path):
    # Blends a new sample into the stored profile so recognition improves over time
    stored = np.load(_embedding_path(username))
    sample = _embed_from_wav(wav_path)
    updated = _normalize((1 - UPDATE_WEIGHT) * stored + UPDATE_WEIGHT * sample)
    np.save(_embedding_path(username), updated)


def list_users():
    if not os.path.exists(USERS_DIR):
        return []
    return [
        name for name in os.listdir(USERS_DIR)
        if os.path.exists(_embedding_path(name))
    ]


def identify_user(wav_path):
    # Returns (username, similarity) of the best match above threshold,
    # or (None, best_similarity) if nobody matches closely enough.
    try:
        sample = _normalize(_embed_from_wav(wav_path))
    except Exception:
        return None, 0.0

    best_user, best_score = None, 0.0
    for username in list_users():
        stored = _normalize(np.load(_embedding_path(username)))
        score = float(np.dot(sample, stored))
        if score > best_score:
            best_user, best_score = username, score

    if best_score >= MATCH_THRESHOLD:
        return best_user, best_score
    return None, best_score