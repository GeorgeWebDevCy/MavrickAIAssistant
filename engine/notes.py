import os
import json
import uuid
from datetime import datetime


def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "MavrickAI")


def _notes_path():
    return os.path.join(_user_data_dir(), "notes.json")


def _load_notes():
    path = _notes_path()
    if not os.path.exists(path):
        os.makedirs(_user_data_dir(), exist_ok=True)
        _save_notes([])
        return []
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_notes(notes):
    os.makedirs(_user_data_dir(), exist_ok=True)
    with open(_notes_path(), "w", encoding="utf-8") as file:
        json.dump(notes, file, indent=2, ensure_ascii=True)


def add_note(text):
    text = str(text).strip()
    if not text:
        return "Note text is required."
    notes = _load_notes()
    note = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    notes.append(note)
    _save_notes(notes)
    return f"Note saved (id: {note['id']})."


def list_notes(limit=50):
    notes = _load_notes()
    notes = sorted(notes, key=lambda n: n.get("created_at", ""), reverse=True)
    return notes[:limit]


def delete_note(note_id):
    note_id = str(note_id).strip()
    if not note_id:
        return "Note id is required."
    notes = _load_notes()
    remaining = [note for note in notes if note.get("id") != note_id]
    if len(remaining) == len(notes):
        return f"No note found with id {note_id}."
    _save_notes(remaining)
    return f"Note {note_id} deleted."


def clear_notes():
    _save_notes([])
    return "All notes cleared."


def get_notes_path():
    return _notes_path()
