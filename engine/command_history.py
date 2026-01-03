import os
import json
from datetime import datetime


def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "MavrickAI")


def _history_path():
    return os.path.join(_user_data_dir(), "command_history.jsonl")


def append_entry(text, source="voice"):
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "text": str(text)
    }
    try:
        os.makedirs(_user_data_dir(), exist_ok=True)
        with open(_history_path(), "a", encoding="utf-8") as file:
            json.dump(entry, file, ensure_ascii=True)
            file.write("\n")
    except Exception:
        pass


def read_entries(limit=200, source=None):
    path = _history_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()
        entries = []
        for line in lines[-limit:]:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if source and entry.get("source") != source:
                continue
            entries.append(entry)
        return entries
    except Exception:
        return []


def clear_entries():
    path = _history_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def get_history_path():
    return _history_path()
