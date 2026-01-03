import os
import json
from datetime import datetime


def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "MavrickAI")


def _log_path():
    return os.path.join(_user_data_dir(), "session.log")


def append_entry(message, kind="log"):
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "kind": str(kind),
        "message": str(message)
    }
    try:
        os.makedirs(_user_data_dir(), exist_ok=True)
        with open(_log_path(), "a", encoding="utf-8") as file:
            json.dump(entry, file, ensure_ascii=True)
            file.write("\n")
    except Exception:
        pass


def read_entries(limit=200):
    path = _log_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except Exception:
                entries.append({"timestamp": "", "kind": "raw", "message": line})
        return entries
    except Exception:
        return []


def clear_entries():
    path = _log_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def get_log_path():
    return _log_path()
