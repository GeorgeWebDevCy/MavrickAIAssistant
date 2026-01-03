# Mavrick AI Assistant Roadmap

This roadmap captures a prioritized set of feature ideas to implement later.
Each feature includes a small MVP definition so we can scope future work.

## Guiding goals
- Keep the assistant fast and low-friction.
- Prefer safe automation with clear confirmations for risky actions.
- Make the HUD feel alive but stay lightweight on system resources.
- Support offline or degraded modes when network services fail.

## Near-term (1-2 sprints)

### 1) Persistent profile + memory summary
- Value: Remembers user preferences (name, voice persona, wake word) across runs.
- MVP: Store a profile JSON and a rolling conversation summary.
- Status: Done (profile JSON + rolling summary persisted).
- Touchpoints: `engine/brain.py`, `engine/voice.py`, new `data/profile.json`.
- Risks: Prompt drift if summary is too aggressive.
- Done when: Restarting preserves preferences and the assistant can recall last session basics.

### 2) Protocol builder (custom workflows)
- Value: Users define their own "work mode" or "gaming mode" commands.
- MVP: JSON-driven protocol list with a simple editor window to add/edit/delete.
- Status: Done (protocol storage + editor UI + voice execution).
- Touchpoints: `engine/actions.py`, `gui/app.py`, new `data/protocols.json`.
- Risks: Misconfigured commands, security concerns for arbitrary shell calls.
- Done when: A new protocol can be created in the UI and executed by voice.

### 3) Tray mode + quick actions
- Value: Run in background with a taskbar tray menu (listen, mute, open HUD).
- MVP: Minimize-to-tray and a small menu with 3-5 actions.
- Status: Done (tray icon + listen/mute/open/exit actions).
- Touchpoints: `main.py`, `gui/app.py`, add dependency (likely `pystray`).
- Risks: Tray integration differences on Windows.
- Done when: Closing the HUD keeps the assistant alive and tray controls work.

### 4) Safe action confirmations + audit log
- Value: Avoid accidental launches or sensitive actions.
- MVP: Confirm dialog for app launches and protocol runs, plus a log list.
- Status: Done (confirm prompts + action log viewer wired).
- Touchpoints: `engine/actions.py`, `gui/app.py`.
- Risks: Too many confirmations can hurt UX.
- Done when: Risky actions require confirmation and are visible in a history list.

### 10) Settings panel + profile editor
- Value: In-app control over name, persona, voice, and wake words.
- MVP: A settings window that edits profile values and persists them.
- Status: Done (settings UI + profile updates wired).
- Touchpoints: `gui/app.py`, `main.py`, `engine/voice.py`, `engine/profile.py`.

### 11) Session log viewer + export
- Value: Keep a persistent transcript for debugging or review.
- MVP: Append HUD log messages to a file and provide a viewer to open/clear it.
- Status: Done (session log file + viewer window).
- Touchpoints: `gui/app.py`, new `engine/session_log.py`.

### 12) Typed command input
- Value: Allow keyboard-driven command execution without voice.
- MVP: A command entry field in the HUD that sends text to the brain.
- Status: Done (command entry + shared command pipeline).
- Touchpoints: `gui/app.py`, `main.py`.

### 13) Command history recall
- Value: Reuse recent commands with keyboard navigation and a history viewer.
- MVP: Up/Down history navigation and a log viewer for commands.
- Status: Done (history file + Up/Down recall + viewer).
- Touchpoints: `gui/app.py`, `main.py`, new `engine/command_history.py`.

### 14) Notes manager
- Value: Capture quick notes and recall them later.
- MVP: Notes file with add/list/delete/clear and a HUD window to manage them.
- Status: Done (notes storage + HUD notes manager + voice tools).
- Touchpoints: `engine/notes.py`, `engine/actions.py`, `engine/brain.py`, `gui/app.py`.

### 15) Keyboard shortcuts + shortcuts guide
- Value: Faster navigation and quick shortcut discovery.
- MVP: Global keyboard shortcuts for core HUD actions plus a shortcuts window (F1/Ctrl+/).
- Status: Done (global binds + help/shortcuts window + HUD button).
- Touchpoints: `gui/app.py`.

### 16) Help screen + app guide
- Value: Explain what the app can do and how to use it.
- MVP: A help window covering core capabilities, usage tips, and shortcuts.
- Status: Done (help window with features + shortcuts).
- Touchpoints: `gui/app.py`.

## Mid-term (1-3 months)

### 5) Scheduler and reminders
- Value: "Remind me at 3 PM" and timed workflows.
- MVP: Background scheduler with a UI list of upcoming reminders.
- Status: Done (persistent reminders + UI list + voice scheduling).
- Touchpoints: `main.py`, `gui/app.py`, new `engine/scheduler.py`.
- Risks: Time zone handling and persistence across restarts.
- Done when: Reminders can be created by voice and survive restarts.

### 6) Skills / plugin system
- Value: Extend Mavrick without editing core code.
- MVP: Load skills from a `skills/` folder with a small manifest format.
- Status: Done (skills loader + tool integration + sample skill).
- Touchpoints: `engine/brain.py`, new `engine/skills.py`.
- Risks: API stability and skill isolation.
- Done when: Dropping a new skill folder registers new commands.

### 7) HUD telemetry upgrade
- Value: More "sci-fi" and practical stats (network, GPU, disk, alerts).
- MVP: Add network throughput and disk activity to the HUD.
- Status: Done (network + disk throughput added to HUD).
- Touchpoints: `gui/app.py`, `engine/actions.py`.
- Risks: Polling cost and UI clutter.
- Done when: New stats render smoothly without affecting performance.

## Stretch ideas

### 8) Screen awareness (screenshot + OCR)
- Value: Answer "what is on my screen" and read alerts aloud.
- MVP: On command, take a screenshot and OCR a single region.
- Status: Done (screen OCR tool + optional region capture).
- Touchpoints: new `engine/vision.py`, `gui/app.py`.
- Risks: OCR accuracy and performance.
- Done when: A user can ask for on-screen text and get a useful summary.

### 9) Offline voice fallback
- Value: Basic use when network is down.
- MVP: Use local STT (Vosk) and local TTS (pyttsx3) when APIs fail.
- Status: Done (offline TTS + optional Vosk STT support).
- Touchpoints: `engine/voice.py`.
- Risks: Extra model downloads and larger installer size.
- Done when: Simple commands still work offline.
