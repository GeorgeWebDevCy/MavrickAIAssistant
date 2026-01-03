import os
import sys
import json
import shutil
import datetime
import webbrowser
import psutil
import platform
from engine import vision
from engine import notes

_DEFAULT_PROTOCOLS = {
    "work mode": ["start chrome https://github.com", "code", "calc"],
    "entertainment": ["start chrome https://youtube.com", "calc"],
    "security": ["calc"],
    "focus": ["calc"]
}

_CONFIRM_CALLBACK = None
_AUDIT_CALLBACK = None
_SCHEDULER = None

def _app_base_dir():
    return getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def _default_protocols_path():
    return os.path.join(_app_base_dir(), "data", "protocols.json")

def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "MavrickAI")

def _protocols_path():
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(_user_data_dir(), "protocols.json")
    default_path = _default_protocols_path()
    if os.path.exists(default_path):
        return default_path
    return os.path.join(_user_data_dir(), "protocols.json")

def _normalize_protocols(data):
    if not isinstance(data, dict):
        return _DEFAULT_PROTOCOLS.copy()
    cleaned = {}
    for name, commands in data.items():
        if not isinstance(name, str):
            continue
        name = name.strip().lower()
        if not name or not isinstance(commands, list):
            continue
        clean_cmds = [str(cmd).strip() for cmd in commands if str(cmd).strip()]
        if clean_cmds:
            cleaned[name] = clean_cmds
    return cleaned if cleaned else _DEFAULT_PROTOCOLS.copy()

def _write_protocols(path, protocols):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(protocols, file, indent=2)

def _ensure_protocols_file():
    path = _protocols_path()
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    default_path = _default_protocols_path()
    if default_path != path and os.path.exists(default_path):
        shutil.copyfile(default_path, path)
    else:
        _write_protocols(path, _DEFAULT_PROTOCOLS)
    return path

def _load_protocols():
    path = _ensure_protocols_file()
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return _normalize_protocols(data)
    except Exception:
        return _DEFAULT_PROTOCOLS.copy()

def _save_protocols(protocols):
    normalized = _normalize_protocols(protocols)
    _write_protocols(_ensure_protocols_file(), normalized)
    return normalized

def _action_log_path():
    return os.path.join(_user_data_dir(), "actions.log")

def _set_confirm_callback(callback):
    global _CONFIRM_CALLBACK
    _CONFIRM_CALLBACK = callback

def _set_audit_callback(callback):
    global _AUDIT_CALLBACK
    _AUDIT_CALLBACK = callback

def _set_scheduler(scheduler):
    global _SCHEDULER
    _SCHEDULER = scheduler

def _confirm_action(action_type, detail):
    if _CONFIRM_CALLBACK:
        try:
            return bool(_CONFIRM_CALLBACK(action_type, detail))
        except Exception:
            return True
    return True

def _audit_action(action_type, detail, status):
    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "action": str(action_type),
        "detail": str(detail),
        "status": str(status)
    }

    try:
        os.makedirs(_user_data_dir(), exist_ok=True)
        with open(_action_log_path(), "a", encoding="utf-8") as file:
            json.dump(entry, file, ensure_ascii=True)
            file.write("\n")
    except Exception:
        pass

    if _AUDIT_CALLBACK:
        try:
            _AUDIT_CALLBACK(entry)
        except Exception:
            pass

def _read_action_log(limit=100):
    path = _action_log_path()
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
                continue
        return entries
    except Exception:
        return []

def _clear_action_log():
    path = _action_log_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

class MavrickActions:
    @staticmethod
    def set_confirm_callback(callback):
        _set_confirm_callback(callback)

    @staticmethod
    def set_audit_callback(callback):
        _set_audit_callback(callback)

    @staticmethod
    def set_scheduler(scheduler):
        _set_scheduler(scheduler)

    @staticmethod
    def schedule_reminder(message, when_text):
        if not _SCHEDULER:
            return "Scheduler is not available."
        return _SCHEDULER.add_reminder(message, when_text)

    @staticmethod
    def list_reminders():
        if not _SCHEDULER:
            return "Scheduler is not available."
        reminders = _SCHEDULER.list_reminders()
        if not reminders:
            return "No reminders scheduled."
        lines = []
        for reminder in reminders[:20]:
            lines.append(f"{reminder.get('id')} | {reminder.get('due_at')} | {reminder.get('message')}")
        return "Upcoming reminders:\n" + "\n".join(lines)

    @staticmethod
    def get_reminders():
        if not _SCHEDULER:
            return []
        return _SCHEDULER.list_reminders()

    @staticmethod
    def cancel_reminder(reminder_id):
        if not _SCHEDULER:
            return "Scheduler is not available."
        return _SCHEDULER.cancel_reminder(reminder_id)

    @staticmethod
    def clear_reminders():
        if not _SCHEDULER:
            return "Scheduler is not available."
        return _SCHEDULER.clear_reminders()

    @staticmethod
    def get_action_log(limit=100):
        return _read_action_log(limit)

    @staticmethod
    def clear_action_log():
        _clear_action_log()
        return "Action log cleared."

    @staticmethod
    def get_time():
        return datetime.datetime.now().strftime("%H:%M")

    @staticmethod
    def get_date():
        return datetime.datetime.now().strftime("%A, %B %d, %Y")

    @staticmethod
    def open_app(app_name):
        app_name = str(app_name)
        # Basic mapping for Windows
        apps = {
            "browser": "start chrome",
            "notepad": "calc",
            "calculator": "calc",
            "code": "code"
        }
        cmd = apps.get(app_name.lower(), app_name)
        if not _confirm_action("Open application", f"{app_name} -> {cmd}"):
            _audit_action("open_app", cmd, "blocked")
            return "Action canceled."
        try:
            os.system(cmd)
            _audit_action("open_app", cmd, "executed")
            return f"Opening {app_name}."
        except Exception:
            _audit_action("open_app", cmd, "failed")
            return f"I could not find {app_name} in my protocols."

    @staticmethod
    def search_web(query):
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        _audit_action("web_search", query, "executed")
        return f"Searching the web for {query}."

    @staticmethod
    def run_protocol(protocol_name):
        protocols = _load_protocols()
        normalized_name = protocol_name.lower()
        commands = protocols.get(normalized_name)
        if commands:
            preview = "\n".join(commands[:6])
            if len(commands) > 6:
                preview += "\n..."
            detail = f"{normalized_name} ({len(commands)} commands)\n{preview}"
            if not _confirm_action("Run protocol", detail):
                _audit_action("protocol", normalized_name, "blocked")
                return f"Protocol {protocol_name} canceled."
            for cmd in commands:
                os.system(cmd)
            _audit_action("protocol", normalized_name, "executed")
            return f"Initiating {protocol_name} protocol. All systems authorized."
        _audit_action("protocol", protocol_name, "missing")
        return f"Protocol {protocol_name} not found in my database."

    @staticmethod
    def list_protocols():
        return sorted(_load_protocols().keys())

    @staticmethod
    def get_protocols():
        return _load_protocols()

    @staticmethod
    def save_protocols(protocols):
        _save_protocols(protocols)
        return "Protocols updated."

    @staticmethod
    def upsert_protocol(protocol_name, commands):
        protocols = _load_protocols()
        normalized_name = protocol_name.strip().lower()
        protocols[normalized_name] = commands
        _save_protocols(protocols)
        return f"Protocol '{normalized_name}' saved."

    @staticmethod
    def delete_protocol(protocol_name):
        protocols = _load_protocols()
        normalized_name = protocol_name.strip().lower()
        if normalized_name in protocols:
            del protocols[normalized_name]
            _save_protocols(protocols)
            return f"Protocol '{normalized_name}' deleted."
        return f"Protocol '{normalized_name}' not found."

    @staticmethod
    def media_control(action):
        # Using PowerShell to simulate key presses for media
        actions = {
            "volume up": "175",
            "volume down": "174",
            "mute": "173",
            "play pause": "179",
            "next": "176",
            "previous": "177"
        }
        key_code = actions.get(action.lower())
        if key_code:
            cmd = f'powershell -Command "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]{key_code})"'
            os.system(cmd)
            _audit_action("media_control", action, "executed")
            return f"Executing {action}."
        _audit_action("media_control", action, "blocked")
        return f"Unknown media action: {action}."

    @staticmethod
    def screen_ocr(region=None, save=False):
        detail = "Full screen"
        if isinstance(region, dict):
            detail = f"Region {region}"
        if not _confirm_action("Capture screen", detail):
            _audit_action("screen_ocr", detail, "blocked")
            return "Action canceled."
        result = vision.screen_ocr(region=region, save=bool(save))
        status = "executed"
        if isinstance(result, str) and result.startswith("Error:"):
            status = "failed"
        _audit_action("screen_ocr", detail, status)
        return result

    @staticmethod
    def add_note(text):
        return notes.add_note(text)

    @staticmethod
    def list_notes():
        items = notes.list_notes(limit=20)
        if not items:
            return "No notes yet."
        lines = []
        for item in items:
            lines.append(f"{item.get('id')} | {item.get('created_at')} | {item.get('text')}")
        return "Notes:\n" + "\n".join(lines)

    @staticmethod
    def get_notes():
        return notes.list_notes(limit=200)

    @staticmethod
    def delete_note(note_id):
        return notes.delete_note(note_id)

    @staticmethod
    def clear_notes():
        return notes.clear_notes()

    @staticmethod
    def get_system_stats():
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        bat_str = f"{battery.percent}%" if battery else "N/A"
        return f"CPU: {cpu}%, RAM: {ram}%, Battery: {bat_str}"

if __name__ == "__main__":
    print(MavrickActions.get_system_stats())
