# JARVIS SCREEN / GUI CONTROL AGENT
# Screen-aware interaction layer. No blind fixed coordinates by default.

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCREENSHOT_DIR = ROOT / "screen_captures"


def screenshot(path: str | None = None) -> tuple[bool, str, Any]:
    try:
        import pyautogui
    except ImportError:
        return False, "pyautogui is not installed.", None

    SCREENSHOT_DIR.mkdir(exist_ok=True)

    target = Path(path) if path else (
        SCREENSHOT_DIR / f"screen_{int(time.time() * 1000)}.png"
    )

    try:
        image = pyautogui.screenshot()
        image.save(target)
        return True, f"Screenshot saved: {target}", image
    except Exception as exc:
        return False, f"Screenshot failed: {exc}", None


def locate_text(text: str) -> list[Any]:
    """
    UI Automation first; OCR fallback can be added without changing callers.
    """
    query = str(text or "").strip().lower()
    if not query:
        return []

    try:
        from pywinauto import Desktop

        matches = []

        for window in Desktop(backend="uia").windows(visible_only=True):
            try:
                controls = window.descendants()
            except Exception:
                continue

            for control in controls:
                try:
                    name = str(
                        control.window_text()
                        or getattr(control.element_info, "name", "")
                        or ""
                    )
                    if query in name.lower() and control.is_visible():
                        matches.append(control)
                except Exception:
                    continue

        return matches
    except Exception:
        return []


def click_text(text: str) -> tuple[bool, str]:
    query = str(text or "").strip()
    matches = locate_text(query)
    if not matches:
        return False, f"UI element '{query}' nahi mila."

    def _name(control: Any) -> str:
        try:
            return str(
                getattr(control.element_info, "name", "")
                or control.window_text()
                or ""
            ).strip()
        except Exception:
            return ""

    exact = [control for control in matches if _name(control).casefold() == query.casefold()]
    candidates = exact if exact else matches
    if len(candidates) != 1:
        return False, f"'{query}' ke {len(candidates)} matching UI elements mile; galat click se bachne ke liye action cancel kiya."

    control = candidates[0]
    try:
        control.click_input()
    except Exception:
        try:
            control.invoke()
        except Exception as exc:
            return False, f"'{query}' mila tha lekin click nahi ho paaya: {exc}"

    # Basic, accessible-control verification only. If it remains visible, report
    # the click as dispatched but do not claim the requested app operation worked.
    time.sleep(0.25)
    still_visible = bool(locate_text(query))
    if still_visible:
        return True, f"'{query}' par click action bheja; element abhi visible hai, isliye final result confirm nahi hua."
    return True, f"'{query}' par click kiya aur element ab visible nahi hai."


def type_text(text: str, interval: float = 0.01) -> tuple[bool, str]:
    try:
        import pyautogui
        pyautogui.write(str(text), interval=interval)
        return True, "Text type kar diya."
    except Exception as exc:
        return False, f"Typing failed: {exc}"


def press(key: str) -> tuple[bool, str]:
    try:
        import pyautogui
        pyautogui.press(str(key))
        return True, f"Key '{key}' press ki."
    except Exception as exc:
        return False, f"Key press failed: {exc}"


def scroll(amount: int) -> tuple[bool, str]:
    try:
        import pyautogui
        pyautogui.scroll(int(amount))
        return True, f"Scroll complete: {amount}"
    except Exception as exc:
        return False, f"Scroll failed: {exc}"


def click_allow() -> tuple[bool, str]:
    """
    Example persistent UI task:
    whenever an accessible 'Allow' button is currently visible, click it.
    This function performs one verified interaction; a future watcher can
    call it periodically.
    """
    return click_text("Allow")


def verify_text(text: str) -> bool:
    return bool(locate_text(text))


def describe_capabilities() -> dict[str, Any]:
    import importlib.util
    import shutil
    import os
    available = lambda name: importlib.util.find_spec(name) is not None
    gui = available('pyautogui')
    uia = os.name == 'nt' and available('pywinauto')
    return {
        'screenshot': gui, 'uia_text_detection': uia,
        'click_by_text': uia, 'typing': gui, 'keyboard': gui,
        'scroll': gui, 'verification': uia, 'fixed_coordinate_only': False,
        'ocr': available('pytesseract') and shutil.which('tesseract') is not None,
        'runtime_verified': False,
    }


def read_visible_text() -> tuple[bool, str]:
    """On-demand local OCR. No screenshot persisted or sent to a cloud provider."""
    try:
        import pytesseract
        import screen_vision
        path = None
        try:
            path, *_ = screen_vision._capture()
            from PIL import Image, ImageOps
            with Image.open(path) as image:
                text = pytesseract.image_to_string(ImageOps.autocontrast(image.convert('L')), timeout=10)
            return (True, text.strip()) if text.strip() else (False, 'Readable text nahi mila.')
        finally:
            if path:
                path.unlink(missing_ok=True)
    except ImportError:
        return False, 'Optional OCR unavailable: install pytesseract and local Tesseract engine.'
    except Exception as exc:
        return False, f'OCR failed: {exc}'


def switch_window(title: str) -> tuple[bool, str]:
    try:
        from pywinauto import Desktop
        matches = [w for w in Desktop(backend='uia').windows(visible_only=True)
                   if str(title).casefold() in w.window_text().casefold()]
        if not title.strip() or len(matches) != 1:
            return False, 'Unique window nahi mili; exact title do.'
        matches[0].set_focus()
        return (True, 'Window focus verify hua.') if matches[0].has_focus() else (False, 'Window focus verify nahi hua.')
    except Exception as exc:
        return False, f'Window switch failed: {exc}'
