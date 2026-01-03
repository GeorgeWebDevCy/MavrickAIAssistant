import os
import sys
import json
import shutil

_DEFAULT_PROFILE = {
    "user_name": "Sir",
    "persona": "mavrick",
    "voice": "onyx",
    "wake_words": ["computer", "hey computer", "mavrick", "maverick"],
    "summary": ""
}

def _app_base_dir():
    return getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def _default_profile_path():
    return os.path.join(_app_base_dir(), "data", "profile.json")

def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "MavrickAI")

def _profile_path():
    user_path = os.path.join(_user_data_dir(), "profile.json")
    if os.path.exists(user_path):
        return user_path
    if getattr(sys, "_MEIPASS", None):
        return user_path
    default_path = _default_profile_path()
    if os.path.exists(default_path):
        return default_path
    return user_path

def _normalize_profile(data):
    if not isinstance(data, dict):
        data = {}
    profile = _DEFAULT_PROFILE.copy()
    user_name = data.get("user_name")
    if isinstance(user_name, str) and user_name.strip():
        profile["user_name"] = user_name.strip()

    persona = data.get("persona")
    if isinstance(persona, str) and persona.strip():
        profile["persona"] = persona.strip().lower()

    voice = data.get("voice")
    if isinstance(voice, str) and voice.strip():
        profile["voice"] = voice.strip().lower()

    wake_words = data.get("wake_words")
    if isinstance(wake_words, list):
        cleaned = [str(word).strip().lower() for word in wake_words if str(word).strip()]
        if cleaned:
            profile["wake_words"] = cleaned

    summary = data.get("summary")
    if isinstance(summary, str) and summary.strip():
        profile["summary"] = summary.strip()

    return profile

def _write_profile(path, profile):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(profile, file, indent=2, ensure_ascii=True)

def load_profile():
    path = _profile_path()
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        default_path = _default_profile_path()
        if default_path != path and os.path.exists(default_path):
            shutil.copyfile(default_path, path)
        else:
            _write_profile(path, _DEFAULT_PROFILE)

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return _normalize_profile(data)
    except Exception:
        return _DEFAULT_PROFILE.copy()

def save_profile(profile):
    normalized = _normalize_profile(profile)
    path = os.path.join(_user_data_dir(), "profile.json")
    _write_profile(path, normalized)
    return normalized
