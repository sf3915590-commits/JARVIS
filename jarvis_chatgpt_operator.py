from __future__ import annotations
import pyperclip

"""Reliable UI operator for the installed ChatGPT Classic app."""

import json
import os
import shutil
import time
from pathlib import Path

APP_ID = "OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0!ChatGPT"
ROOT = Path(__file__).resolve().parent
def _resolve_hud_root_name_local():
    for name in ("JARVIS_HUD_V2", "JARVIS_HUD_V3"):
        if (ROOT / name).exists():
            return name
    return "JARVIS_HUD_V2"

HUD_PUBLIC = ROOT / _resolve_hud_root_name_local() / "public" / "jarvis_results"
DOWNLOADS = Path.home() / "Downloads"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _require_gui():
    try:
        import pyautogui
        return pyautogui
    except Exception as exc:
        raise RuntimeError(
            "pyautogui is required for ChatGPT Classic UI control. "
            f"Import failed: {exc}"
        ) from exc


def _focus():
    from windows_control import launch_chatgpt_classic
    value = launch_chatgpt_classic()
    if isinstance(value, tuple):
        ok, msg = value
    else:
        ok, msg = bool(value), "ChatGPT Classic focused."
    if not ok:
        return False, msg
    time.sleep(0.55)
    return True, msg


def _clipboard_has_image():
    try:
        from PIL import ImageGrab
        return ImageGrab.grabclipboard() is not None
    except Exception:
        return False



def _click_composer():
    """Focus the actual ChatGPT composer using UIA first, then safe coordinate fallback."""
    pyautogui = _require_gui()
    candidates = []
    try:
        from pywinauto import Desktop
        for win in Desktop(backend="uia").windows(visible_only=True):
            try:
                title = str(win.window_text() or "").lower()
                if "chatgpt" not in title and "chatgpt" not in str(win.element_info.name or "").lower():
                    continue
                for control_type in ("Edit", "Document"):
                    for control in win.descendants(control_type=control_type):
                        try:
                            if not control.is_visible() or not control.is_enabled():
                                continue
                            rect = control.rectangle()
                            width = rect.right - rect.left
                            height = rect.bottom - rect.top
                            if width >= 120 and height >= 20:
                                candidates.append((rect.top, width * height, rect, control))
                        except Exception:
                            continue
            except Exception:
                continue
    except Exception:
        pass

    if candidates:
        # Largest top = lowest control on screen; area breaks ties.
        _, _, rect, control = max(candidates, key=lambda item: (item[0], item[1]))
        try:
            control.click_input()
            time.sleep(0.25)
            return True
        except Exception:
            pass

    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active:
            x = int(active.left + active.width * 0.52)
            y = int(active.top + active.height * 0.89)
            pyautogui.click(x, y)
            time.sleep(0.25)
            return True
    except Exception:
        pass

    w, h = pyautogui.size()
    pyautogui.click(int(w * 0.52), int(h * 0.90))
    time.sleep(0.25)
    return True

def _paste_text(text):
    gui = _require_gui()
    pyperclip.copy(str(text))
    gui.hotkey("ctrl", "v")
    time.sleep(0.5)

def _paste_image_from_clipboard():
    if not _clipboard_has_image():
        return False, "Selected Gallery image is not available in the Windows clipboard."
    _require_gui().hotkey("ctrl", "v")
    time.sleep(0.8)
    return True, "Selected Gallery image pasted into ChatGPT."


def _submit():
    # ONLY SEND LOGIC — do not touch prompt, launcher, or composer.
    for word in ("send", "submit"):
        buttons = _desktop_buttons_with_word(word)
        for button in buttons:
            try:
                if hasattr(button, "is_visible") and not button.is_visible():
                    continue
                if hasattr(button, "is_enabled") and not button.is_enabled():
                    continue

                try:
                    button.invoke()
                except Exception:
                    button.click_input()

                time.sleep(0.8)
                return
            except Exception:
                continue

    # ChatGPT/Electron fallback.
    gui = _require_gui()

    try:
        gui.hotkey("ctrl", "enter")
        time.sleep(0.8)
        return
    except Exception:
        pass

    try:
        gui.press("enter")
        time.sleep(0.8)
    except Exception:
        pass


def _image_request(prompt: str, forced: bool):
    if forced:
        return True
    p = prompt.lower()
    cues = (
        "this photo", "this image", "selected photo", "selected image",
        "background", "edit this", "enhance this", "change this", "remove background",
        "make the background", "is photo", "iss photo", "is image", "iss image"
    )
    return any(cue in p for cue in cues) and _clipboard_has_image()


def _desktop_buttons_with_word(word: str):
    """Return visible UIA buttons whose accessible name contains word."""
    try:
        from pywinauto import Desktop
    except Exception:
        return []

    matches = []
    try:
        windows = Desktop(backend="uia").windows(visible_only=True)
        for win in windows:
            name = (win.window_text() or "").lower()
            if "chatgpt" not in name and not "chatgpt" in str(win.element_info.name).lower():
                # Still inspect if the window has ChatGPT child controls; this
                # keeps Electron accessibility quirks from blocking the scan.
                pass
            for control in win.descendants(control_type="Button"):
                try:
                    c_name = str(control.window_text() or control.element_info.name or "")
                    if word.lower() in c_name.lower() and control.is_visible():
                        matches.append(control)
                except Exception:
                    continue
    except Exception:
        return []
    return matches


def _click_latest_download_button():
    buttons = _desktop_buttons_with_word("download")
    if not buttons:
        return False
    try:
        buttons[-1].click_input()
        return True
    except Exception:
        try:
            buttons[-1].invoke()
            return True
        except Exception:
            return False


def _snapshot_downloads():
    if not DOWNLOADS.exists():
        return {}
    result = {}
    for path in DOWNLOADS.iterdir():
        try:
            if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
                stat = path.stat()
                result[path] = (stat.st_mtime_ns, stat.st_size)
        except Exception:
            pass
    return result


def _wait_for_new_download(before, timeout=240):
    deadline = time.time() + timeout
    stable = {}
    while time.time() < deadline:
        current = _snapshot_downloads()
        candidates = [
            path for path, sig in current.items()
            if path not in before or sig != before.get(path)
        ]
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
            latest = candidates[0]
            try:
                size = latest.stat().st_size
                old = stable.get(latest)
                stable[latest] = size
                if old is not None and old == size and size > 0:
                    return latest
            except Exception:
                pass
        time.sleep(1.0)
    return None


def _publish_to_hud(image_path: Path):
    HUD_PUBLIC.mkdir(parents=True, exist_ok=True)
    name = f"chatgpt_{int(time.time() * 1000)}{image_path.suffix.lower()}"
    target = HUD_PUBLIC / name
    shutil.copy2(image_path, target)

    payload = {
        "source": "JARVIS",
        "type": "CHATGPT_IMAGE_RESULT",
        "url": f"/jarvis_results/{name}",
        "filename": name,
        "message": "ChatGPT generated image returned to JARVIS HUD.",
    }

    try:
        import websocket
        ws = websocket.create_connection("ws://127.0.0.1:8765", timeout=0.8)
        ws.send(json.dumps(payload, ensure_ascii=False))
        ws.close()
    except Exception as exc:
        # The file is still published; HUD transport failure should not delete it.
        return False, f"Image saved but HUD event failed: {exc}"
    return True, str(target)


def execute(prompt: str, use_selected_image: bool = False):
    prompt = str(prompt or "").strip()
    if not prompt:
        return False, "ChatGPT prompt is empty."

    ok, msg = _focus()
    if not ok:
        return False, msg

    use_image = _image_request(prompt, use_selected_image)
    before_downloads = _snapshot_downloads()

    try:
        composer_ready = _click_composer()
        if not composer_ready:
            return False, 'ChatGPT composer could not be focused.'
        if use_image:
            ok, msg = _paste_image_from_clipboard()
            if not ok:
                return False, msg
            _paste_text(prompt)
        else:
            _paste_text(prompt)
        _submit()
    except Exception as exc:
        return False, f'ChatGPT composer operation failed: {exc}'


    if not use_image:
        return True, "Prompt entered and submitted to ChatGPT Classic."

    # Wait for the generated image to exist, then activate its accessible
    # Download button. We never pick an unrelated old file from Downloads.
    deadline = time.time() + 240
    clicked = False
    while time.time() < deadline:
        if _click_latest_download_button():
            clicked = True
            break
        time.sleep(1.0)

    if not clicked:
        return False, "ChatGPT generated the result, but the Download control was not accessible."

    result_path = _wait_for_new_download(before_downloads, timeout=60)
    if not result_path:
        return False, "Download was clicked, but the generated image file was not detected in Downloads."

    ok, detail = _publish_to_hud(result_path)
    if not ok:
        return False, detail
    return True, "ChatGPT generated image collected and returned to the JARVIS HUD."

