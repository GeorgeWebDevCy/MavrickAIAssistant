import os
import sys
import threading

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:
    pystray = None
    Image = None
    ImageDraw = None


class TrayController:
    def __init__(self, icon_path, on_show=None, on_listen=None, on_toggle_mute=None, on_exit=None):
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_listen = on_listen
        self.on_toggle_mute = on_toggle_mute
        self.on_exit = on_exit
        self.icon = None
        self.thread = None
        self.is_muted = False
        self.available = pystray is not None and Image is not None

    def start(self):
        if not self.available:
            return False
        if self.thread and self.thread.is_alive():
            return True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

    def set_muted(self, muted):
        self.is_muted = bool(muted)
        if self.icon:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def _run(self):
        image = self._load_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Open HUD", self._handle_open),
            pystray.MenuItem("Listen", self._handle_listen),
            pystray.MenuItem("Mute", self._handle_toggle_mute, checked=self._is_muted),
            pystray.MenuItem("Exit", self._handle_exit)
        )
        self.icon = pystray.Icon("Mavrick", image, "Mavrick", menu)
        self.icon.run()

    def _load_icon_image(self):
        if Image is None:
            return None
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                return Image.open(self.icon_path)
            except Exception:
                pass
        image = Image.new("RGB", (64, 64), "#00d2ff")
        if ImageDraw:
            draw = ImageDraw.Draw(image)
            draw.rectangle([10, 10, 54, 54], outline="#003a47", width=4)
        return image

    def _is_muted(self, item):
        return self.is_muted

    def _handle_open(self, icon, item):
        if self.on_show:
            self.on_show()

    def _handle_listen(self, icon, item):
        if self.on_listen:
            self.on_listen()

    def _handle_toggle_mute(self, icon, item):
        if self.on_toggle_mute:
            try:
                self.set_muted(self.on_toggle_mute())
            except Exception:
                self.set_muted(not self.is_muted)
        else:
            self.set_muted(not self.is_muted)

    def _handle_exit(self, icon, item):
        if self.on_exit:
            self.on_exit()
        self.stop()
