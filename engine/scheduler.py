import os
import sys
import json
import threading
import uuid
import re
from datetime import datetime, timedelta


class ReminderScheduler:
    def __init__(self, on_trigger=None, poll_seconds=2):
        self._on_trigger = on_trigger
        self._poll_seconds = poll_seconds
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = None
        self._reminders = []
        self._load_reminders()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def add_reminder(self, message, when_text):
        message = str(message).strip()
        when_text = str(when_text).strip()
        if not message:
            return "Reminder message is required."
        if not when_text:
            return "Reminder time is required."

        due_at = self._parse_when(when_text)
        if not due_at:
            return "I couldn't understand that reminder time."

        if due_at <= datetime.now():
            return "Reminder time must be in the future."

        reminder = {
            "id": uuid.uuid4().hex[:8],
            "message": message,
            "due_at": due_at.isoformat(timespec="seconds"),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        with self._lock:
            self._reminders.append(reminder)
            self._save_reminders()

        return f"Reminder set for {due_at.strftime('%Y-%m-%d %H:%M')} (id: {reminder['id']})."

    def list_reminders(self):
        with self._lock:
            upcoming = sorted(self._reminders, key=lambda r: r.get("due_at", ""))
        return upcoming

    def cancel_reminder(self, reminder_id):
        reminder_id = str(reminder_id).strip()
        if not reminder_id:
            return "Reminder id is required."

        with self._lock:
            before = len(self._reminders)
            self._reminders = [r for r in self._reminders if r.get("id") != reminder_id]
            after = len(self._reminders)
            if after == before:
                return f"No reminder found with id {reminder_id}."
            self._save_reminders()

        return f"Reminder {reminder_id} canceled."

    def clear_reminders(self):
        with self._lock:
            self._reminders = []
            self._save_reminders()
        return "All reminders cleared."

    def _run_loop(self):
        while not self._stop_event.is_set():
            now = datetime.now()
            due = []
            with self._lock:
                remaining = []
                for reminder in self._reminders:
                    try:
                        due_at = datetime.fromisoformat(reminder.get("due_at", ""))
                    except Exception:
                        due_at = None
                    if due_at and due_at <= now:
                        due.append(reminder)
                    else:
                        remaining.append(reminder)
                if due:
                    self._reminders = remaining
                    self._save_reminders()
            for reminder in due:
                if self._on_trigger:
                    try:
                        self._on_trigger(reminder)
                    except Exception:
                        pass
            self._stop_event.wait(self._poll_seconds)

    def _parse_when(self, text):
        now = datetime.now()
        raw = text.strip().lower()

        match = re.match(r"^in\s+(\d+)\s+(minute|minutes|hour|hours|day|days)$", raw)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if "hour" in unit:
                return now + timedelta(hours=amount)
            if "day" in unit:
                return now + timedelta(days=amount)
            return now + timedelta(minutes=amount)

        try:
            return datetime.fromisoformat(text)
        except Exception:
            pass

        match = re.match(r"^(\d{1,2}):(\d{2})(\s*(am|pm))?$", raw)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            meridiem = match.group(4)
            if meridiem:
                if meridiem == "pm" and hour != 12:
                    hour += 12
                if meridiem == "am" and hour == 12:
                    hour = 0
            if hour > 23 or minute > 59:
                return None
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        return None

    def _load_reminders(self):
        path = _ensure_reminders_file()
        reminders = _load_reminders_from(path)
        with self._lock:
            self._reminders = reminders

    def _save_reminders(self):
        path = _ensure_reminders_file()
        with self._lock:
            _save_reminders_to(path, self._reminders)


def _app_base_dir():
    return getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _default_reminders_path():
    return os.path.join(_app_base_dir(), "data", "reminders.json")


def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "MavrickAI")


def _reminders_path():
    user_path = os.path.join(_user_data_dir(), "reminders.json")
    if os.path.exists(user_path):
        return user_path
    if getattr(sys, "_MEIPASS", None):
        return user_path
    default_path = _default_reminders_path()
    if os.path.exists(default_path):
        return default_path
    return user_path


def _load_reminders_from(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_reminders_to(path, reminders):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(reminders, file, indent=2, ensure_ascii=True)


def _ensure_reminders_file():
    path = _reminders_path()
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    default_path = _default_reminders_path()
    if default_path != path and os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        _save_reminders_to(path, data if isinstance(data, list) else [])
    else:
        _save_reminders_to(path, [])
    return path
