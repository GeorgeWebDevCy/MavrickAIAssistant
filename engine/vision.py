import os
import sys
from datetime import datetime

try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None

try:
    import pytesseract
except Exception:
    pytesseract = None


def _app_base_dir():
    return getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "MavrickAI")


def _captures_dir():
    return os.path.join(_user_data_dir(), "captures")


def _ensure_tesseract_cmd():
    if not pytesseract:
        return
    cmd = os.getenv("TESSERACT_CMD", "").strip()
    if cmd and os.path.isfile(cmd):
        pytesseract.pytesseract.tesseract_cmd = cmd


def _coerce_region(region):
    if not isinstance(region, dict):
        return None
    try:
        x = int(region.get("x"))
        y = int(region.get("y"))
        width = int(region.get("width"))
        height = int(region.get("height"))
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None
    return (x, y, x + width, y + height)


def capture_screen(region=None, save=False):
    if ImageGrab is None:
        return None, "", "Error: Screen capture is unavailable."

    bbox = _coerce_region(region)
    try:
        image = ImageGrab.grab(bbox=bbox)
    except Exception as exc:
        return None, "", f"Error: Screen capture failed ({exc})."

    path = ""
    if save:
        os.makedirs(_captures_dir(), exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{stamp}.png"
        path = os.path.join(_captures_dir(), filename)
        try:
            image.save(path)
        except Exception:
            path = ""

    return image, path, ""


def screen_ocr(region=None, save=False):
    image, path, error = capture_screen(region=region, save=save)
    if error:
        return error
    if pytesseract is None:
        return "Error: OCR engine not available (pytesseract missing)."

    _ensure_tesseract_cmd()
    try:
        text = pytesseract.image_to_string(image).strip()
    except Exception as exc:
        return f"Error: OCR failed ({exc})."

    if not text:
        text = "No text detected."
    else:
        text = text[:800]

    if path:
        return f"Saved screenshot: {path}\nOCR: {text}"
    return f"OCR: {text}"
