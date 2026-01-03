import customtkinter as ctk
import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
import psutil
import numpy as np
import pyaudio
from engine.actions import MavrickActions
from engine import session_log
from engine import command_history
from engine.weather import WeatherEngine
from ctypes import windll, c_int, byref, sizeof
import ctypes

def _asset_path(*parts):
    # Resolve assets for both source and PyInstaller builds.
    base_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return os.path.join(base_dir, *parts)

class MavrickUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MAVRICK HUD")
        
        # Set AppUserModelID for Taskbar Icon grouping
        try:
            myappid = 'mavrick.ai.assistant.hud.1.0' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass
        
        # Colors
        self.primary_cyan = "#00d2ff"
        self.secondary_teal = "#005f73"
        self.dim_cyan = "#003a47"
        self.alert_orange = "#ff9f1c"
        self.bg_black = "#050505"
        self.alert_red = "#ff4b2b"

        self.geometry("450x700")
        self.attributes("-alpha", 0.95)  # Slightly more opaque for premium feel
        self.attributes("-topmost", True)
        self.overrideredirect(True)      # Borderless HUD

        self._icon_path = _asset_path("assets", "icon.ico")
        self._taskbar_icon = None
        self._protocol_editor = None
        self._action_log_window = None
        self._action_log_text = None
        self._reminders_window = None
        self._reminders_text = None
        self._reminder_id_entry = None
        self._session_log_window = None
        self._session_log_text = None
        self._close_callback = self.destroy
        self._settings_window = None
        self._settings_name_entry = None
        self._settings_persona_var = None
        self._settings_voice_var = None
        self._settings_wake_text = None
        self._settings_summary_text = None
        self._profile_loader = None
        self._profile_saver = None
        self._text_command_callback = None
        self._command_entry = None
        self._command_send_btn = None
        self._command_history_window = None
        self._command_history_text = None
        self._command_history = []
        self._command_history_index = 0
        self._command_history_loaded = False
        self._protocols_cache = {}
        self._protocol_var = None
        self._protocol_menu = None
        self._protocol_name_entry = None
        self._protocol_commands_text = None
        self._apply_window_icon()

        MavrickActions.set_confirm_callback(self.confirm_action)
        MavrickActions.set_audit_callback(self.audit_action)
        
        # Taskbar Icon Fix for Overrideredirect
        # GWL_EXSTYLE = -20
        # WS_EX_APPWINDOW = 0x00040000
        # WS_EX_TOOLWINDOW = 0x00000080
        try:
            self.after(10, self._set_window_style)
        except Exception as e:
            print(f"Taskbar fix error: {e}")

        # Close Button (Top Right)
        self.btn_close = ctk.CTkButton(self, text="✕", width=30, height=30,
                                       fg_color="transparent", hover_color="#ff4b2b",
                                       text_color=self.primary_cyan,
                                       font=("Arial", 14),
                                       command=self._handle_close)
        self.btn_close.place(relx=0.92, rely=0.01)
        

        
        # Center the window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (450 // 2)
        y = (screen_height // 2) - (700 // 2)
        self.geometry(f"450x700+{x}+{y}")
        
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)
        self.bind("<Motion>", self.update_parallax_target)

        self.configure(fg_color=self.bg_black)
        
        # Animation variables
        self.angle_rings = [0, 180, 90, 270]
        self.pulse_val = 0
        self.scan_angle = 0
        self.bars = []
        self.hex_dots = []
        
        # Parallax variables
        self.p_x = 0
        self.p_y = 0
        self.target_p_x = 0
        self.target_p_y = 0
        
        # System Stats
        self.cpu_usage = 0
        self.ram_usage = 0
        self.net_down_bps = 0.0
        self.net_up_bps = 0.0
        self.disk_read_bps = 0.0
        self.disk_write_bps = 0.0
        
        # Audio Stream for Visualizer
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_running = False
        try:
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024)
            self.audio_running = True
        except Exception as e:
            print(f"Audio Input Error: {e}")
            self.audio_running = False

        self.setup_ui()
        self.start_monitor_thread()
        self.start_weather_thread()
        self.animate_hud()

    def setup_ui(self):
        # Header with futuristic font (Orbitron is common for sci-fi)
        title_font = ("Orbitron", 28, "bold")
        self.label_title = ctk.CTkLabel(self, text="MAVRICK", font=title_font, text_color=self.primary_cyan)
        self.label_title.pack(pady=(30, 10))
        
        self.sub_title = ctk.CTkLabel(self, text="ADVANCED ARTIFICIAL INTELLIGENCE", font=("Consolas", 10), text_color=self.secondary_teal)
        self.sub_title.pack(pady=(0, 20))

        # Main HUD Canvas - Increased size for more details
        self.canvas = ctk.CTkCanvas(self, width=300, height=320, bg=self.bg_black, highlightthickness=0)
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", lambda e: self.on_engage())
        
        # 1. Background Hex/Dot Grid (Simulated)
        for i in range(5):
            for j in range(5):
                start_x, start_y = 60 + i*45, 70 + j*45
                dot = self.canvas.create_oval(start_x, start_y, start_x+2, start_y+2, fill=self.dim_cyan, outline="")
                self.hex_dots.append(dot)

        # 2. Concentric Rotating Rings
        self.rings = []
        # Outer thick ring
        self.rings.append(self.canvas.create_arc(30, 30, 270, 270, outline=self.dim_cyan, width=1, style="arc", extent=359))
        self.rings.append(self.canvas.create_arc(35, 35, 265, 265, outline=self.primary_cyan, width=2, style="arc", start=0, extent=60))
        self.rings.append(self.canvas.create_arc(35, 35, 265, 265, outline=self.primary_cyan, width=2, style="arc", start=180, extent=60))
        
        # Middle ring
        self.rings.append(self.canvas.create_arc(60, 60, 240, 240, outline=self.secondary_teal, width=1, style="arc", start=90, extent=120))
        self.rings.append(self.canvas.create_arc(60, 60, 240, 240, outline=self.secondary_teal, width=1, style="arc", start=270, extent=120))
        
        # Inner scanning ring
        self.rings.append(self.canvas.create_arc(85, 85, 215, 215, outline=self.dim_cyan, width=1, style="arc", extent=359))
        self.scan_line = self.canvas.create_arc(85, 85, 215, 215, outline=self.primary_cyan, width=4, style="arc", start=0, extent=20)

        # 3. System Heatmap Arcs
        self.arc_cpu = self.canvas.create_arc(20, 20, 280, 280, outline=self.alert_orange, width=3, style="arc", start=135, extent=0)
        self.arc_ram = self.canvas.create_arc(15, 15, 285, 285, outline=self.secondary_teal, width=3, style="arc", start=225, extent=0)

        # 4. Core Pulse
        self.core_circle = self.canvas.create_oval(110, 110, 190, 190, outline=self.primary_cyan, width=2)
        self.inner_circle = self.canvas.create_oval(130, 130, 170, 170, fill=self.primary_cyan, outline="")
        
        # 5. Voice Visualizer Bars (HUD Position)
        for i in range(16):
            x = 70 + (i * 10)
            bar = self.canvas.create_rectangle(x, 260, x+6, 265, fill=self.primary_cyan, outline="")
            self.bars.append(bar)

        # 5. Peripheral Data Elements
        self.data_labels = []
        data_configs = [
            ("ENC: RSA-4096", 40, 120),
            ("BIT: 128-FLOAT", 40, 280),
            ("CPU: MONITOR", 340, 120),
            ("NET: D 0.0KB/s U 0.0KB/s", 340, 160),
            ("WTH: SCANNING...", 340, 200), # Weather Label
            ("DSK: R 0.0KB/s W 0.0KB/s", 340, 240),
            ("RAM: MONITOR", 340, 280)
        ]
        for text, x, y in data_configs:
            lbl = ctk.CTkLabel(self, text=text, font=("Consolas", 9), text_color=self.secondary_teal)
            lbl.place(x=x, y=y)
            self.data_labels.append(lbl)

        # Interaction Log - Refined look
        self.log_box = ctk.CTkTextbox(self, width=400, height=120, fg_color="#101010", text_color=self.primary_cyan, font=("Consolas", 12), border_width=1, border_color=self.dim_cyan)
        self.log_box.pack(pady=10)

        # Stats Section
        self.usage_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.usage_frame.pack(pady=5, fill="x", padx=30)
        
        self.stats_label = ctk.CTkLabel(self.usage_frame, text="COST: $0.0000 | TOKENS: 0", font=("Consolas", 10), text_color=self.secondary_teal)
        self.stats_label.pack(side="top", anchor="w")
        
        self.balance_label = ctk.CTkLabel(self.usage_frame, text="BALANCE: $0.00", font=("Consolas", 10), text_color=self.secondary_teal)
        self.balance_label.pack(side="top", anchor="w")

        # Bottom Controls
        self.status_label = ctk.CTkLabel(self, text="NETWORK STATUS: STANDBY", font=("Consolas", 11, "bold"), text_color=self.primary_cyan)
        self.status_label.pack(pady=5)

        self.command_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.command_frame.pack(pady=6, padx=40, fill="x")

        self._command_entry = ctk.CTkEntry(self.command_frame, placeholder_text="TYPE COMMAND...", height=32)
        self._command_entry.pack(side="left", fill="x", expand=True)
        self._command_entry.bind("<Return>", self._send_text_command)
        self._command_entry.bind("<Up>", self._history_prev)
        self._command_entry.bind("<Down>", self._history_next)

        self._command_send_btn = ctk.CTkButton(self.command_frame, text="SEND", width=70, height=32, command=self._send_text_command)
        self._command_send_btn.pack(side="left", padx=(8, 0))
        
        self.btn_listen = ctk.CTkButton(self, text="ENGAGE HYPERLINK", font=("Orbitron", 12, "bold"), fg_color=self.primary_cyan, text_color="black", hover_color="#00b8e6", corner_radius=5, height=40, command=self.on_engage)
        self.btn_listen.pack(pady=10, padx=40, fill="x")
        
        self.btn_protocols = ctk.CTkButton(self, text="PROTOCOLS", font=("Consolas", 10, "bold"), fg_color=self.secondary_teal, text_color="white", hover_color="#0a768f", corner_radius=5, height=34, command=self.open_protocol_editor)
        self.btn_protocols.pack(pady=5, padx=40, fill="x")

        self.btn_actions = ctk.CTkButton(self, text="ACTIONS LOG", font=("Consolas", 10, "bold"), fg_color=self.secondary_teal, text_color="white", hover_color="#0a768f", corner_radius=5, height=34, command=self.open_action_log)
        self.btn_actions.pack(pady=5, padx=40, fill="x")

        self.btn_session_log = ctk.CTkButton(self, text="SESSION LOG", font=("Consolas", 10, "bold"), fg_color=self.secondary_teal, text_color="white", hover_color="#0a768f", corner_radius=5, height=34, command=self.open_session_log)
        self.btn_session_log.pack(pady=5, padx=40, fill="x")

        self.btn_command_history = ctk.CTkButton(self, text="COMMAND HISTORY", font=("Consolas", 10, "bold"), fg_color=self.secondary_teal, text_color="white", hover_color="#0a768f", corner_radius=5, height=34, command=self.open_command_history)
        self.btn_command_history.pack(pady=5, padx=40, fill="x")

        self.btn_reminders = ctk.CTkButton(self, text="REMINDERS", font=("Consolas", 10, "bold"), fg_color=self.secondary_teal, text_color="white", hover_color="#0a768f", corner_radius=5, height=34, command=self.open_reminders)
        self.btn_reminders.pack(pady=5, padx=40, fill="x")

        self.btn_settings = ctk.CTkButton(self, text="SETTINGS", font=("Consolas", 10, "bold"), fg_color=self.secondary_teal, text_color="white", hover_color="#0a768f", corner_radius=5, height=34, command=self.open_settings)
        self.btn_settings.pack(pady=5, padx=40, fill="x")

        self.btn_exit = ctk.CTkButton(self, text="TERMINATE CONNECTION", font=("Consolas", 10), fg_color="transparent", border_width=1, border_color=self.alert_red, text_color=self.alert_red, command=self.destroy)
        self.btn_exit.pack(pady=5)

    def open_protocol_editor(self):
        if self._protocol_editor and self._protocol_editor.winfo_exists():
            self._protocol_editor.focus()
            return

        self._protocol_editor = ctk.CTkToplevel(self)
        self._protocol_editor.title("Protocol Builder")
        self._protocol_editor.geometry("520x420")
        self._protocol_editor.resizable(False, False)
        try:
            self._protocol_editor.iconbitmap(self._icon_path)
        except Exception:
            pass

        title = ctk.CTkLabel(self._protocol_editor, text="PROTOCOL BUILDER", font=("Orbitron", 16, "bold"), text_color=self.primary_cyan)
        title.pack(pady=(10, 6))

        selector_frame = ctk.CTkFrame(self._protocol_editor, fg_color="transparent")
        selector_frame.pack(fill="x", padx=12, pady=(4, 6))

        selector_label = ctk.CTkLabel(selector_frame, text="Select Protocol", font=("Consolas", 10), text_color=self.secondary_teal)
        selector_label.pack(side="left")

        self._protocols_cache = MavrickActions.get_protocols()
        protocol_names = sorted(self._protocols_cache.keys())
        self._protocol_var = tk.StringVar(value=protocol_names[0] if protocol_names else "")
        self._protocol_menu = ctk.CTkOptionMenu(
            selector_frame,
            values=protocol_names if protocol_names else ["(none)"],
            variable=self._protocol_var,
            command=self._on_protocol_select
        )
        self._protocol_menu.pack(side="left", padx=8)

        reload_btn = ctk.CTkButton(selector_frame, text="Reload", width=80, command=self._reload_protocols)
        reload_btn.pack(side="right")

        name_label = ctk.CTkLabel(self._protocol_editor, text="Protocol Name", font=("Consolas", 10), text_color=self.secondary_teal)
        name_label.pack(anchor="w", padx=12, pady=(6, 2))

        self._protocol_name_entry = ctk.CTkEntry(self._protocol_editor, width=360)
        self._protocol_name_entry.pack(fill="x", padx=12)

        commands_label = ctk.CTkLabel(self._protocol_editor, text="Commands (one per line)", font=("Consolas", 10), text_color=self.secondary_teal)
        commands_label.pack(anchor="w", padx=12, pady=(10, 2))

        self._protocol_commands_text = ctk.CTkTextbox(self._protocol_editor, height=180)
        self._protocol_commands_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        btn_frame = ctk.CTkFrame(self._protocol_editor, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        new_btn = ctk.CTkButton(btn_frame, text="New", width=90, command=self._new_protocol)
        new_btn.pack(side="left")

        save_btn = ctk.CTkButton(btn_frame, text="Save", width=90, command=self._save_protocol)
        save_btn.pack(side="left", padx=8)

        delete_btn = ctk.CTkButton(btn_frame, text="Delete", width=90, fg_color=self.alert_red, hover_color="#c23b24", command=self._delete_protocol)
        delete_btn.pack(side="left")

        close_btn = ctk.CTkButton(btn_frame, text="Close", width=90, command=self._protocol_editor.destroy)
        close_btn.pack(side="right")

        self._refresh_protocol_menu()

    def _on_protocol_select(self, selected_name):
        if selected_name and selected_name != "(none)":
            self._load_protocol_into_editor(selected_name)

    def _refresh_protocol_menu(self, select_name=None):
        self._protocols_cache = MavrickActions.get_protocols()
        protocol_names = sorted(self._protocols_cache.keys())

        if not protocol_names:
            self._protocol_menu.configure(values=["(none)"], state="disabled")
            if self._protocol_var:
                self._protocol_var.set("")
            self._clear_protocol_editor()
            return

        self._protocol_menu.configure(values=protocol_names, state="normal")
        name_to_load = select_name if select_name in protocol_names else protocol_names[0]
        if self._protocol_var:
            self._protocol_var.set(name_to_load)
        self._load_protocol_into_editor(name_to_load)

    def _load_protocol_into_editor(self, name):
        self._clear_protocol_editor()
        commands = self._protocols_cache.get(name, [])
        self._protocol_name_entry.insert(0, name)
        for cmd in commands:
            self._protocol_commands_text.insert("end", f"{cmd}\n")

    def _clear_protocol_editor(self):
        if self._protocol_name_entry:
            self._protocol_name_entry.delete(0, "end")
        if self._protocol_commands_text:
            self._protocol_commands_text.delete("1.0", "end")

    def _new_protocol(self):
        if self._protocol_var:
            self._protocol_var.set("")
        self._clear_protocol_editor()

    def _save_protocol(self):
        name = self._protocol_name_entry.get().strip().lower()
        if not name:
            messagebox.showwarning("Protocols", "Protocol name is required.")
            return

        raw_lines = self._protocol_commands_text.get("1.0", "end").splitlines()
        commands = [line.strip() for line in raw_lines if line.strip()]
        if not commands:
            messagebox.showwarning("Protocols", "Add at least one command.")
            return

        MavrickActions.upsert_protocol(name, commands)
        self._refresh_protocol_menu(select_name=name)

    def _delete_protocol(self):
        name = self._protocol_name_entry.get().strip().lower()
        if not name:
            messagebox.showwarning("Protocols", "Select a protocol to delete.")
            return
        if not messagebox.askyesno("Delete Protocol", f"Delete '{name}'?"):
            return

        MavrickActions.delete_protocol(name)
        self._refresh_protocol_menu()

    def _reload_protocols(self):
        self._refresh_protocol_menu()

    def confirm_action(self, action_type, detail):
        if not self.winfo_exists():
            return True

        title = "Confirm Action"
        message = f"{action_type}?\n\n{detail}"

        if threading.current_thread() is threading.main_thread():
            return messagebox.askyesno(title, message)

        result = {"value": False}
        done = threading.Event()

        def _ask():
            result["value"] = messagebox.askyesno(title, message)
            done.set()

        self.after(0, _ask)
        done.wait()
        return result["value"]

    def audit_action(self, entry):
        def _refresh():
            if self._action_log_window and self._action_log_window.winfo_exists():
                self._load_action_log()

        if threading.current_thread() is threading.main_thread():
            _refresh()
        else:
            self.after(0, _refresh)

    def open_action_log(self):
        if self._action_log_window and self._action_log_window.winfo_exists():
            self._action_log_window.focus()
            return

        self._action_log_window = ctk.CTkToplevel(self)
        self._action_log_window.title("Action Log")
        self._action_log_window.geometry("560x360")
        self._action_log_window.resizable(False, False)
        try:
            self._action_log_window.iconbitmap(self._icon_path)
        except Exception:
            pass

        title = ctk.CTkLabel(self._action_log_window, text="ACTION LOG", font=("Orbitron", 16, "bold"), text_color=self.primary_cyan)
        title.pack(pady=(10, 6))

        self._action_log_text = ctk.CTkTextbox(self._action_log_window, height=220)
        self._action_log_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        btn_frame = ctk.CTkFrame(self._action_log_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", width=90, command=self._load_action_log)
        refresh_btn.pack(side="left")

        clear_btn = ctk.CTkButton(btn_frame, text="Clear", width=90, fg_color=self.alert_red, hover_color="#c23b24", command=self._clear_action_log)
        clear_btn.pack(side="left", padx=8)

        close_btn = ctk.CTkButton(btn_frame, text="Close", width=90, command=self._action_log_window.destroy)
        close_btn.pack(side="right")

        self._load_action_log()

    def _load_action_log(self):
        if not self._action_log_text:
            return
        entries = MavrickActions.get_action_log(limit=200)
        lines = []
        for entry in entries:
            timestamp = entry.get("timestamp", "")
            status = entry.get("status", "")
            action = entry.get("action", "")
            detail = entry.get("detail", "")
            lines.append(f"{timestamp} | {status} | {action} | {detail}")
        if not lines:
            lines.append("No actions logged yet.")

        self._action_log_text.configure(state="normal")
        self._action_log_text.delete("1.0", "end")
        self._action_log_text.insert("end", "\n".join(lines))
        self._action_log_text.configure(state="disabled")

    def _clear_action_log(self):
        if not messagebox.askyesno("Clear Log", "Clear the action log?"):
            return
        MavrickActions.clear_action_log()
        self._load_action_log()

    def open_session_log(self):
        if self._session_log_window and self._session_log_window.winfo_exists():
            self._session_log_window.focus()
            return

        self._session_log_window = ctk.CTkToplevel(self)
        self._session_log_window.title("Session Log")
        self._session_log_window.geometry("620x380")
        self._session_log_window.resizable(False, False)
        try:
            self._session_log_window.iconbitmap(self._icon_path)
        except Exception:
            pass

        title = ctk.CTkLabel(self._session_log_window, text="SESSION LOG", font=("Orbitron", 16, "bold"), text_color=self.primary_cyan)
        title.pack(pady=(10, 6))

        self._session_log_text = ctk.CTkTextbox(self._session_log_window, height=220)
        self._session_log_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        btn_frame = ctk.CTkFrame(self._session_log_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", width=90, command=self._load_session_log)
        refresh_btn.pack(side="left")

        open_btn = ctk.CTkButton(btn_frame, text="Open File", width=90, command=self._open_session_log_file)
        open_btn.pack(side="left", padx=8)

        clear_btn = ctk.CTkButton(btn_frame, text="Clear", width=90, fg_color=self.alert_red, hover_color="#c23b24", command=self._clear_session_log)
        clear_btn.pack(side="left")

        close_btn = ctk.CTkButton(btn_frame, text="Close", width=90, command=self._session_log_window.destroy)
        close_btn.pack(side="right")

        self._load_session_log()

    def _load_session_log(self):
        if not self._session_log_text:
            return
        entries = session_log.read_entries(limit=250)
        lines = []
        for entry in entries:
            timestamp = entry.get("timestamp", "")
            kind = entry.get("kind", "")
            message = entry.get("message", "")
            lines.append(f"{timestamp} | {kind} | {message}")
        if not lines:
            lines.append("No session log entries yet.")

        self._session_log_text.configure(state="normal")
        self._session_log_text.delete("1.0", "end")
        self._session_log_text.insert("end", "\n".join(lines))
        self._session_log_text.configure(state="disabled")

    def _clear_session_log(self):
        if not messagebox.askyesno("Clear Log", "Clear the session log?"):
            return
        session_log.clear_entries()
        self._load_session_log()

    def _open_session_log_file(self):
        path = session_log.get_log_path()
        if not os.path.exists(path):
            messagebox.showinfo("Session Log", "No session log file yet.")
            return
        try:
            os.startfile(path)
        except Exception:
            messagebox.showwarning("Session Log", f"Could not open log file:\n{path}")

    def open_reminders(self):
        if self._reminders_window and self._reminders_window.winfo_exists():
            self._reminders_window.focus()
            return

        self._reminders_window = ctk.CTkToplevel(self)
        self._reminders_window.title("Reminders")
        self._reminders_window.geometry("600x380")
        self._reminders_window.resizable(False, False)
        try:
            self._reminders_window.iconbitmap(self._icon_path)
        except Exception:
            pass

        title = ctk.CTkLabel(self._reminders_window, text="REMINDERS", font=("Orbitron", 16, "bold"), text_color=self.primary_cyan)
        title.pack(pady=(10, 6))

        self._reminders_text = ctk.CTkTextbox(self._reminders_window, height=220)
        self._reminders_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        id_frame = ctk.CTkFrame(self._reminders_window, fg_color="transparent")
        id_frame.pack(fill="x", padx=12, pady=(0, 6))

        id_label = ctk.CTkLabel(id_frame, text="Reminder ID", font=("Consolas", 10), text_color=self.secondary_teal)
        id_label.pack(side="left")

        self._reminder_id_entry = ctk.CTkEntry(id_frame, width=160)
        self._reminder_id_entry.pack(side="left", padx=8)

        cancel_btn = ctk.CTkButton(id_frame, text="Cancel", width=90, command=self._cancel_reminder)
        cancel_btn.pack(side="left")

        btn_frame = ctk.CTkFrame(self._reminders_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", width=90, command=self._load_reminders)
        refresh_btn.pack(side="left")

        clear_btn = ctk.CTkButton(btn_frame, text="Clear All", width=90, fg_color=self.alert_red, hover_color="#c23b24", command=self._clear_reminders)
        clear_btn.pack(side="left", padx=8)

        close_btn = ctk.CTkButton(btn_frame, text="Close", width=90, command=self._reminders_window.destroy)
        close_btn.pack(side="right")

        self._load_reminders()

    def _load_reminders(self):
        if not self._reminders_text:
            return
        reminders = MavrickActions.get_reminders()
        lines = []
        for reminder in reminders:
            reminder_id = reminder.get("id", "")
            due_at = reminder.get("due_at", "")
            message = reminder.get("message", "")
            lines.append(f"{reminder_id} | {due_at} | {message}")
        if not lines:
            lines.append("No reminders scheduled.")

        self._reminders_text.configure(state="normal")
        self._reminders_text.delete("1.0", "end")
        self._reminders_text.insert("end", "\n".join(lines))
        self._reminders_text.configure(state="disabled")

    def _cancel_reminder(self):
        if not self._reminder_id_entry:
            return
        reminder_id = self._reminder_id_entry.get().strip()
        if not reminder_id:
            messagebox.showwarning("Reminders", "Enter a reminder id to cancel.")
            return
        MavrickActions.cancel_reminder(reminder_id)
        self._reminder_id_entry.delete(0, "end")
        self._load_reminders()

    def _clear_reminders(self):
        if not messagebox.askyesno("Clear Reminders", "Clear all reminders?"):
            return
        MavrickActions.clear_reminders()
        self._load_reminders()

    def set_profile_callbacks(self, load_callback, save_callback):
        self._profile_loader = load_callback
        self._profile_saver = save_callback

    def _voice_for_persona(self, persona):
        voices = {
            "mavrick": "onyx",
            "jarvis": "fable",
            "friday": "shimmer"
        }
        return voices.get(str(persona).lower(), "onyx")

    def open_settings(self):
        if self._settings_window and self._settings_window.winfo_exists():
            self._settings_window.focus()
            return

        self._settings_window = ctk.CTkToplevel(self)
        self._settings_window.title("Settings")
        self._settings_window.geometry("560x420")
        self._settings_window.resizable(False, False)
        try:
            self._settings_window.iconbitmap(self._icon_path)
        except Exception:
            pass

        profile = {}
        if self._profile_loader:
            try:
                profile = self._profile_loader()
            except Exception:
                profile = {}

        user_name = profile.get("user_name", "")
        persona = profile.get("persona", "mavrick")
        voice = profile.get("voice", "")
        wake_words = profile.get("wake_words", [])
        summary = profile.get("summary", "")

        title = ctk.CTkLabel(self._settings_window, text="SETTINGS", font=("Orbitron", 16, "bold"), text_color=self.primary_cyan)
        title.pack(pady=(10, 6))

        form = ctk.CTkFrame(self._settings_window, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        name_label = ctk.CTkLabel(form, text="User Name", font=("Consolas", 10), text_color=self.secondary_teal)
        name_label.pack(anchor="w")
        self._settings_name_entry = ctk.CTkEntry(form, width=300)
        self._settings_name_entry.pack(fill="x", pady=(0, 6))
        self._settings_name_entry.insert(0, user_name)

        persona_label = ctk.CTkLabel(form, text="Persona", font=("Consolas", 10), text_color=self.secondary_teal)
        persona_label.pack(anchor="w")
        persona_values = ["mavrick", "jarvis", "friday"]
        self._settings_persona_var = tk.StringVar(value=persona if persona in persona_values else "mavrick")
        persona_menu = ctk.CTkOptionMenu(form, values=persona_values, variable=self._settings_persona_var)
        persona_menu.pack(fill="x", pady=(0, 6))

        voice_label = ctk.CTkLabel(form, text="Voice (auto uses persona)", font=("Consolas", 10), text_color=self.secondary_teal)
        voice_label.pack(anchor="w")
        voice_values = ["auto", "alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        voice_choice = voice or "auto"
        if voice_choice == self._voice_for_persona(persona):
            voice_choice = "auto"
        self._settings_voice_var = tk.StringVar(value=voice_choice if voice_choice in voice_values else "auto")
        voice_menu = ctk.CTkOptionMenu(form, values=voice_values, variable=self._settings_voice_var)
        voice_menu.pack(fill="x", pady=(0, 6))

        wake_label = ctk.CTkLabel(form, text="Wake Words (one per line)", font=("Consolas", 10), text_color=self.secondary_teal)
        wake_label.pack(anchor="w")
        self._settings_wake_text = ctk.CTkTextbox(form, height=80)
        self._settings_wake_text.pack(fill="both", pady=(0, 6))
        if isinstance(wake_words, list):
            self._settings_wake_text.insert("end", "\n".join(wake_words))

        summary_label = ctk.CTkLabel(form, text="Memory Summary (read-only)", font=("Consolas", 10), text_color=self.secondary_teal)
        summary_label.pack(anchor="w")
        self._settings_summary_text = ctk.CTkTextbox(form, height=60)
        self._settings_summary_text.pack(fill="both", pady=(0, 6))
        self._settings_summary_text.insert("end", summary or "No summary yet.")
        self._settings_summary_text.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self._settings_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        save_btn = ctk.CTkButton(btn_frame, text="Save", width=90, command=self._save_settings)
        save_btn.pack(side="left")

        close_btn = ctk.CTkButton(btn_frame, text="Close", width=90, command=self._settings_window.destroy)
        close_btn.pack(side="right")

    def _save_settings(self):
        if not self._profile_saver:
            messagebox.showwarning("Settings", "Profile update is unavailable.")
            return

        user_name = self._settings_name_entry.get().strip() if self._settings_name_entry else ""
        persona = self._settings_persona_var.get() if self._settings_persona_var else "mavrick"
        voice = self._settings_voice_var.get() if self._settings_voice_var else "auto"

        wake_text = ""
        if self._settings_wake_text:
            wake_text = self._settings_wake_text.get("1.0", "end")
        wake_words = []
        for token in wake_text.replace(",", "\n").splitlines():
            token = token.strip()
            if token:
                wake_words.append(token)

        updates = {
            "user_name": user_name,
            "persona": persona,
            "voice": voice,
            "wake_words": wake_words
        }

        result = self._profile_saver(updates)
        messagebox.showinfo("Settings", result)

    def set_text_command_callback(self, callback):
        self._text_command_callback = callback

    def _send_text_command(self, event=None):
        if not self._text_command_callback or not self._command_entry:
            return
        text = self._command_entry.get().strip()
        if not text:
            return
        self._command_entry.delete(0, "end")
        self._remember_command(text)
        self._text_command_callback(text)

    def _remember_command(self, text):
        if self._command_history and self._command_history[-1] == text:
            self._command_history_index = len(self._command_history)
            return
        self._command_history.append(text)
        if len(self._command_history) > 200:
            self._command_history = self._command_history[-200:]
        self._command_history_index = len(self._command_history)
        self._command_history_loaded = True

    def _refresh_command_history_cache(self, force=False):
        if self._command_history_loaded and not force:
            return
        entries = command_history.read_entries(limit=200, source="text")
        self._command_history = [entry.get("text", "") for entry in entries if entry.get("text")]
        self._command_history_index = len(self._command_history)
        self._command_history_loaded = True

    def _history_prev(self, event=None):
        if not self._command_entry:
            return "break"
        self._refresh_command_history_cache()
        if not self._command_history:
            return "break"
        if self._command_history_index > 0:
            self._command_history_index -= 1
        text = self._command_history[self._command_history_index]
        self._command_entry.delete(0, "end")
        self._command_entry.insert(0, text)
        self._command_entry.icursor("end")
        return "break"

    def _history_next(self, event=None):
        if not self._command_entry:
            return "break"
        self._refresh_command_history_cache()
        if not self._command_history:
            return "break"
        if self._command_history_index < len(self._command_history) - 1:
            self._command_history_index += 1
            text = self._command_history[self._command_history_index]
        else:
            self._command_history_index = len(self._command_history)
            text = ""
        self._command_entry.delete(0, "end")
        if text:
            self._command_entry.insert(0, text)
            self._command_entry.icursor("end")
        return "break"

    def open_command_history(self):
        if self._command_history_window and self._command_history_window.winfo_exists():
            self._command_history_window.focus()
            return

        self._command_history_window = ctk.CTkToplevel(self)
        self._command_history_window.title("Command History")
        self._command_history_window.geometry("620x380")
        self._command_history_window.resizable(False, False)
        try:
            self._command_history_window.iconbitmap(self._icon_path)
        except Exception:
            pass

        title = ctk.CTkLabel(self._command_history_window, text="COMMAND HISTORY", font=("Orbitron", 16, "bold"), text_color=self.primary_cyan)
        title.pack(pady=(10, 6))

        self._command_history_text = ctk.CTkTextbox(self._command_history_window, height=220)
        self._command_history_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        btn_frame = ctk.CTkFrame(self._command_history_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", width=90, command=self._load_command_history)
        refresh_btn.pack(side="left")

        use_btn = ctk.CTkButton(btn_frame, text="Use Last", width=90, command=self._use_last_command)
        use_btn.pack(side="left", padx=8)

        open_btn = ctk.CTkButton(btn_frame, text="Open File", width=90, command=self._open_command_history_file)
        open_btn.pack(side="left")

        clear_btn = ctk.CTkButton(btn_frame, text="Clear", width=90, fg_color=self.alert_red, hover_color="#c23b24", command=self._clear_command_history)
        clear_btn.pack(side="left", padx=8)

        close_btn = ctk.CTkButton(btn_frame, text="Close", width=90, command=self._command_history_window.destroy)
        close_btn.pack(side="right")

        self._load_command_history()

    def _load_command_history(self):
        if not self._command_history_text:
            return
        entries = command_history.read_entries(limit=250)
        lines = []
        for entry in entries:
            timestamp = entry.get("timestamp", "")
            source = entry.get("source", "")
            text = entry.get("text", "")
            lines.append(f"{timestamp} | {source} | {text}")
        if not lines:
            lines.append("No commands logged yet.")

        self._command_history_text.configure(state="normal")
        self._command_history_text.delete("1.0", "end")
        self._command_history_text.insert("end", "\n".join(lines))
        self._command_history_text.configure(state="disabled")

        self._command_history_loaded = False
        self._refresh_command_history_cache(force=True)

    def _use_last_command(self):
        self._refresh_command_history_cache()
        if not self._command_entry:
            return
        if not self._command_history:
            messagebox.showinfo("Command History", "No recent commands.")
            return
        text = self._command_history[-1]
        self._command_entry.delete(0, "end")
        self._command_entry.insert(0, text)
        self._command_entry.icursor("end")

    def _clear_command_history(self):
        if not messagebox.askyesno("Clear History", "Clear command history?"):
            return
        command_history.clear_entries()
        self._command_history = []
        self._command_history_index = 0
        self._command_history_loaded = False
        self._load_command_history()

    def _open_command_history_file(self):
        path = command_history.get_history_path()
        if not os.path.exists(path):
            messagebox.showinfo("Command History", "No command history file yet.")
            return
        try:
            os.startfile(path)
        except Exception:
            messagebox.showwarning("Command History", f"Could not open history file:\n{path}")

    def set_close_action(self, callback):
        self._close_callback = callback or self.destroy

    def _handle_close(self):
        if self._close_callback:
            self._close_callback()

    def hide_to_tray(self):
        try:
            self.withdraw()
        except Exception:
            pass

    def show_from_tray(self):
        try:
            self.deiconify()
            self.attributes("-topmost", True)
            self._apply_window_icon()
        except Exception:
            pass

    def _format_rate(self, bytes_per_sec):
        try:
            rate = float(bytes_per_sec)
        except Exception:
            rate = 0.0
        if rate >= 1024 * 1024:
            return f"{rate / (1024 * 1024):.1f}MB/s"
        return f"{rate / 1024:.1f}KB/s"
        
    def log_message(self, message):
        session_log.append_entry(message, kind="hud")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")

    def clear_log(self):
        self.log_box.delete("0.0", "end")

    def update_stats(self, cost, tokens, balance):
        self.stats_label.configure(text=f"COST: ${cost:.4f} | TOKENS: {tokens}")
        self.balance_label.configure(text=f"BALANCE: ${balance:.2f}")
        if balance <= 0:
            self.balance_label.configure(text_color="#ff4b2b") # Red for alert
        else:
            self.balance_label.configure(text_color=self.secondary_teal)
        
    def start_monitor_thread(self):
        def monitor():
            last_net = psutil.net_io_counters()
            last_disk = psutil.disk_io_counters()
            last_time = time.time()
            while True:
                self.cpu_usage = psutil.cpu_percent()
                self.ram_usage = psutil.virtual_memory().percent
                now = time.time()
                elapsed = now - last_time
                if elapsed <= 0:
                    elapsed = 1.0
                try:
                    net = psutil.net_io_counters()
                    disk = psutil.disk_io_counters()
                    if net and last_net:
                        self.net_down_bps = max(0.0, (net.bytes_recv - last_net.bytes_recv) / elapsed)
                        self.net_up_bps = max(0.0, (net.bytes_sent - last_net.bytes_sent) / elapsed)
                        last_net = net
                    if disk and last_disk:
                        self.disk_read_bps = max(0.0, (disk.read_bytes - last_disk.read_bytes) / elapsed)
                        self.disk_write_bps = max(0.0, (disk.write_bytes - last_disk.write_bytes) / elapsed)
                        last_disk = disk
                except Exception:
                    pass
                last_time = now
                time.sleep(1)
        threading.Thread(target=monitor, daemon=True).start()

    def start_weather_thread(self):
        def update_weather():
            while True:
                w_data = WeatherEngine.get_weather()
                # Update UI from main thread ideally, but Tkinter usually handles text config in threads okay-ish, 
                # strictly we should use after(), but let's try direct update first or use a variable.
                # Safe way:
                if len(self.data_labels) > 4:
                     self.data_labels[4].configure(text=f"WTH: {w_data}")
                time.sleep(600) # Update every 10 mins
        threading.Thread(target=update_weather, daemon=True).start()

    def update_parallax_target(self, event):
        # Calculate center of the canvas relative to the window
        canvas_x = self.canvas.winfo_x() + self.canvas.winfo_width() / 2
        canvas_y = self.canvas.winfo_y() + self.canvas.winfo_height() / 2
        
        # Mouse position relative to the canvas center
        self.target_p_x = (event.x_root - (self.winfo_x() + canvas_x)) * 0.08
        self.target_p_y = (event.y_root - (self.winfo_y() + canvas_y)) * 0.08

    def animate_hud(self):
        self.pulse_val += 0.08
        self.scan_angle = (self.scan_angle + 5) % 360
        
        # Parallax smoothing
        self.p_x += (self.target_p_x - self.p_x) * 0.1
        self.p_y += (self.target_p_y - self.p_y) * 0.1
        
        # 1. Apply Parallax shifts to individual layers
        # Background dots (slowest)
        for i, dot in enumerate(self.hex_dots):
            # Original coordinates for dots are relative to canvas (0,0)
            # The canvas itself is centered, so we need to adjust for that if we want true window-relative parallax.
            # For simplicity, let's assume the canvas's (0,0) is the reference for parallax.
            # The original dot creation uses 60 + i*45, 70 + j*45.
            # We need to extract the original coordinates to apply the shift.
            # The hex_dots list stores the canvas item IDs. We need to get their original positions.
            # A more robust way would be to store original coords with the item ID.
            # For now, let's re-calculate based on the loop structure.
            
            # Assuming 5x5 grid, i is 0-24.
            # row = i // 5, col = i % 5
            original_x = 60 + (i % 5) * 45
            original_y = 70 + (i // 5) * 45
            
            self.canvas.coords(dot, 
                               original_x + self.p_x * 0.2, 
                               original_y + self.p_y * 0.2, 
                               original_x + 2 + self.p_x * 0.2, 
                               original_y + 2 + self.p_y * 0.2)
            
            # Flicker dots
            if math.sin(self.pulse_val + i) > 0.8:
                self.canvas.itemconfig(dot, fill=self.primary_cyan)
            else:
                self.canvas.itemconfig(dot, fill=self.dim_cyan)

        # 2. Ring Rotations and Parallax
        # The rings are drawn around the canvas center (150, 150).
        # We need to shift their bounding box.
        
        # Update arcs based on usage
        cpu_extent = -(self.cpu_usage * 0.9) # arc grows counter-clockwise from 135
        cpu_color = self.alert_orange if self.cpu_usage < 80 else self.alert_red
        self.canvas.itemconfig(self.arc_cpu, extent=cpu_extent, outline=cpu_color)
        
        ram_extent = -(self.ram_usage * 0.9) # arc grows counter-clockwise from 225
        ram_color = self.secondary_teal if self.ram_usage < 80 else self.alert_red
        self.canvas.itemconfig(self.arc_ram, extent=ram_extent, outline=ram_color)

        # Apply parallax to the rings and arcs by shifting their coordinates
        # The rings are defined with (x1, y1, x2, y2) bounding boxes.
        # The center of the canvas is (150, 150) for a 300x320 canvas.
        # Let's define a helper to shift coordinates for canvas items.
        
        # Shift for rings (medium shift)
        ring_shift_x = self.p_x * 0.5
        ring_shift_y = self.p_y * 0.5

        # Update ring coordinates
        # Original: (30, 30, 270, 270) -> center (150, 150), radius 120
        # New: (30+sx, 30+sy, 270+sx, 270+sy)
        ring_coords = [
            (30, 30, 270, 270), # rings[0]
            (35, 35, 265, 265), # rings[1]
            (35, 35, 265, 265), # rings[2]
            (60, 60, 240, 240), # rings[3]
            (60, 60, 240, 240), # rings[4]
            (85, 85, 215, 215)  # rings[5]
        ]
        for i, ring_id in enumerate(self.rings):
            x1, y1, x2, y2 = ring_coords[i]
            self.canvas.coords(ring_id, x1 + ring_shift_x, y1 + ring_shift_y, x2 + ring_shift_x, y2 + ring_shift_y)
        
        # Scan line
        x1, y1, x2, y2 = (85, 85, 215, 215)
        self.canvas.coords(self.scan_line, x1 + ring_shift_x, y1 + ring_shift_y, x2 + ring_shift_x, y2 + ring_shift_y)

        # CPU/RAM arcs
        arc_cpu_coords = (20, 20, 280, 280)
        self.canvas.coords(self.arc_cpu, arc_cpu_coords[0] + ring_shift_x, arc_cpu_coords[1] + ring_shift_y,
                           arc_cpu_coords[2] + ring_shift_x, arc_cpu_coords[3] + ring_shift_y)
        arc_ram_coords = (15, 15, 285, 285)
        self.canvas.coords(self.arc_ram, arc_ram_coords[0] + ring_shift_x, arc_ram_coords[1] + ring_shift_y,
                           arc_ram_coords[2] + ring_shift_x, arc_ram_coords[3] + ring_shift_y)

        # Ring rotations (these are still applied to the shifted rings)
        self.canvas.itemconfig(self.rings[1], start=(self.scan_angle * 0.5) % 360)
        self.canvas.itemconfig(self.rings[2], start=(self.scan_angle * 0.5 + 180) % 360)
        self.canvas.itemconfig(self.rings[3], start=(90 - self.scan_angle * 0.8) % 360)
        self.canvas.itemconfig(self.rings[4], start=(270 - self.scan_angle * 0.8) % 360)
        self.canvas.itemconfig(self.scan_line, start=self.scan_angle)

        # 3. Core Pulse (fastest shift)
        core_shift_x = self.p_x * 0.8
        core_shift_y = self.p_y * 0.8
        
        pulse_scale = 1 + (math.sin(self.pulse_val) * 0.15)
        core_r = 40 * pulse_scale
        
        # Original center of core pulse is (150, 150)
        self.canvas.coords(self.core_circle, 
                           110 + core_shift_x, 110 + core_shift_y, 
                           190 + core_shift_x, 190 + core_shift_y)
        self.canvas.coords(self.inner_circle, 
                           150 - core_r/1.5 + core_shift_x, 150 - core_r/1.5 + core_shift_y, 
                           150 + core_r/1.5 + core_shift_x, 150 + core_r/1.5 + core_shift_y)
        
        # 4. Visualizer Bars Animation (Smooth Sine)
        # Bars are defined relative to canvas (0,0)
        bar_shift_x = self.p_x * 0.4
        bar_shift_y = self.p_y * 0.4

        for i, bar in enumerate(self.bars):
            h = 5 + abs(math.sin(self.pulse_val + i*0.4) * 25)
            x_base = 70 + (i * 10)
            y_base = 280 # The bottom of the bars
            self.canvas.coords(bar, 
                               x_base + bar_shift_x, 
                               y_base - h + bar_shift_y, 
                               x_base + 6 + bar_shift_x, 
                               y_base + bar_shift_y)
            
        # 5. Dynamic Color Intensity for inner circle
        color_int = int(180 + 75 * math.sin(self.pulse_val))
        hex_color = f"#{0:02x}{color_int:02x}{255:02x}"
        self.canvas.itemconfig(self.inner_circle, fill=hex_color)

        # Update CPU/RAM/NET/DSK labels
        if len(self.data_labels) > 6: # Ensure labels exist
            self.data_labels[2].configure(text=f"CPU: {self.cpu_usage:.0f}%")
            self.data_labels[3].configure(text=f"NET: D {self._format_rate(self.net_down_bps)} U {self._format_rate(self.net_up_bps)}")
            self.data_labels[5].configure(text=f"DSK: R {self._format_rate(self.disk_read_bps)} W {self._format_rate(self.disk_write_bps)}")
            self.data_labels[6].configure(text=f"RAM: {self.ram_usage:.0f}%")

        self.update_visualizer()
        self.after(30, self.animate_hud)

    def update_visualizer(self):
        if self.audio_running and self.stream:
            try:
                data = np.frombuffer(self.stream.read(1024, exception_on_overflow=False), dtype=np.int16)
                # Compute FFT
                fft_data = np.fft.rfft(data)
                fft_mag = np.abs(fft_data)
                
                # Normalize and bin into 16 bars
                # We have 513 bins (1024/2 + 1). We need 16.
                step = len(fft_mag) // 16
                
                for i, bar in enumerate(self.bars):
                    # Average magnitude for this bin
                    mag = np.mean(fft_mag[i*step : (i+1)*step])
                    
                    # Scale factor - adjust experimental
                    h = min(50, int(mag / 100)) # improved scaling
                    
                    # Apply to bar
                    x_base = 70 + (i * 10)
                    y_base = 280 
                    bar_shift_x = self.p_x * 0.4
                    bar_shift_y = self.p_y * 0.4
                    
                    self.canvas.coords(bar, 
                                       x_base + bar_shift_x, 
                                       y_base - h + bar_shift_y, 
                                       x_base + 6 + bar_shift_x, 
                                       y_base + bar_shift_y)
            except Exception:
                pass
        else:
            # Fallback to simulation if no audio
            bar_shift_x = self.p_x * 0.4
            bar_shift_y = self.p_y * 0.4
            for i, bar in enumerate(self.bars):
                h = 5 + abs(math.sin(self.pulse_val + i*0.4) * 25)
                x_base = 70 + (i * 10)
                y_base = 280 
                self.canvas.coords(bar, 
                                   x_base + bar_shift_x, 
                                   y_base - h + bar_shift_y, 
                                   x_base + 6 + bar_shift_x, 
                                   y_base + bar_shift_y)

    def on_engage(self):
        self.log_message("ACCESSING SPEECH CHANNEL...")
        self.status_label.configure(text="NETWORK STATUS: LISTENING", text_color=self.alert_orange)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def _apply_window_icon(self):
        try:
            if os.path.exists(self._icon_path):
                self.iconbitmap(self._icon_path)
        except Exception:
            pass

        try:
            hwnd = windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            if not hwnd:
                return

            if os.path.exists(self._icon_path):
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                LR_DEFAULTSIZE = 0x00000040
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1

                hicon = windll.user32.LoadImageW(
                    None,
                    self._icon_path,
                    IMAGE_ICON,
                    0,
                    0,
                    LR_LOADFROMFILE | LR_DEFAULTSIZE,
                )
                if hicon:
                    self._taskbar_icon = hicon
                    windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
                    windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
        except Exception:
            pass

    def _set_window_style(self):
        try:
            hwnd = windll.user32.GetParent(self.winfo_id())
            # If GetParent returns 0, it might be the root itself or we need to wait
            if not hwnd:
                 hwnd = self.winfo_id()
                 
            # Force the window to be an app window
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            
            # Re-assert proper attributes
            self.wm_withdraw()
            self.wm_deiconify()
            self.attributes("-topmost", True)
            
            # Re-apply icon to ensure taskbar picks it up
            self._apply_window_icon()
        except Exception as e:
            print(f"Could not apply window style: {e}") 

if __name__ == "__main__":
    app = MavrickUI()
    app.mainloop()
