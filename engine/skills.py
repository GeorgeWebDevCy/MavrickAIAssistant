import json
import os
import sys
import re
import importlib.util


class SkillManager:
    def __init__(self):
        self.skills = {}
        self.errors = []
        self.load_skills()

    def load_skills(self):
        self.skills = {}
        self.errors = []
        for root in self._skill_roots():
            self._load_skills_from_root(root)

    def list_skills(self):
        return sorted(self.skills.keys())

    def get_tools(self):
        tools = []
        for name in sorted(self.skills.keys()):
            skill = self.skills[name]
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": skill.get("description", "Custom skill"),
                    "parameters": skill.get("parameters", {"type": "object", "properties": {}})
                }
            })
        return tools

    def execute(self, name, args):
        skill = self.skills.get(name)
        if not skill:
            return f"Skill '{name}' not found."
        handler = skill.get("handler")
        if not handler:
            return f"Skill '{name}' is missing a handler."
        try:
            try:
                result = handler(**args)
            except TypeError:
                result = handler(args)
            return str(result) if result is not None else ""
        except Exception as exc:
            return f"Skill '{name}' failed: {exc}"

    def _skill_roots(self):
        roots = []
        user_root = os.path.join(self._user_data_dir(), "skills")
        default_root = os.path.join(self._app_base_dir(), "skills")
        roots.append(user_root)
        roots.append(default_root)
        return roots

    def _load_skills_from_root(self, root):
        if not os.path.isdir(root):
            return
        for entry in os.listdir(root):
            skill_dir = os.path.join(root, entry)
            if not os.path.isdir(skill_dir):
                continue
            manifest_path = os.path.join(skill_dir, "skill.json")
            if not os.path.isfile(manifest_path):
                continue
            skill = self._load_skill_from_dir(skill_dir, manifest_path)
            if not skill:
                continue
            name = skill["name"]
            if name in self.skills:
                continue
            self.skills[name] = skill

    def _load_skill_from_dir(self, skill_dir, manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as file:
                manifest = json.load(file)
        except Exception as exc:
            self.errors.append(f"{manifest_path}: {exc}")
            return None

        if isinstance(manifest, dict) and manifest.get("enabled") is False:
            return None

        name = manifest.get("name") if isinstance(manifest, dict) else None
        if not isinstance(name, str) or not name.strip():
            name = os.path.basename(skill_dir)
        name = name.strip().lower()
        safe_name = re.sub(r"[^a-z0-9_]", "_", name)
        if not safe_name:
            self.errors.append(f"{manifest_path}: invalid skill name '{name}'")
            return None
        name = safe_name

        description = manifest.get("description", "Custom skill") if isinstance(manifest, dict) else "Custom skill"
        parameters = manifest.get("parameters") if isinstance(manifest, dict) else None
        if not isinstance(parameters, dict):
            parameters = {"type": "object", "properties": {}}

        entrypoint = manifest.get("entrypoint", "skill.py:run") if isinstance(manifest, dict) else "skill.py:run"
        if ":" not in entrypoint:
            self.errors.append(f"{manifest_path}: invalid entrypoint '{entrypoint}'")
            return None
        module_rel, func_name = entrypoint.split(":", 1)
        module_path = os.path.join(skill_dir, module_rel)
        if not os.path.isfile(module_path):
            self.errors.append(f"{manifest_path}: missing module '{module_rel}'")
            return None

        handler = self._load_handler(module_path, name, func_name)
        if not handler:
            return None

        return {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
            "path": skill_dir
        }

    def _load_handler(self, module_path, skill_name, func_name):
        safe_name = re.sub(r"[^a-z0-9_]", "_", skill_name.lower())
        module_id = f"mavrick_skill_{safe_name}"
        spec = importlib.util.spec_from_file_location(module_id, module_path)
        if spec is None or spec.loader is None:
            self.errors.append(f"{module_path}: cannot load module")
            return None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            self.errors.append(f"{module_path}: {exc}")
            return None
        handler = getattr(module, func_name, None)
        if not callable(handler):
            self.errors.append(f"{module_path}: missing callable '{func_name}'")
            return None
        return handler

    def _app_base_dir(self):
        return getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    def _user_data_dir(self):
        base = os.getenv("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "MavrickAI")
