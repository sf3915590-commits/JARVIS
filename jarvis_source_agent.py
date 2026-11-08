from __future__ import annotations

"""JARVIS source-code repair agent using ChatGPT Classic as the reviewer.

Protocol:
READ/VALIDATE -> DISCUSS -> PROPOSE EXACT PATCH -> WAIT FOR USER -> BACKUP ->
APPLY -> VALIDATE -> ROLLBACK ON FAILURE.
"""

import ast
import json
import py_compile
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HUD = ROOT / "JARVIS_HUD_V2"
CORE = HUD / "src" / "Core.jsx"
ROOT = Path(__file__).resolve().parent
PENDING = ROOT / ".jarvis_pending_chatgpt_fix.json"
KEY_FILES = [
    "Tahrun.py",
    "windows_control.py",
    "brain.py",
    "voice.py",
    "actions.py",
    "music_agent.py",
    "youtube_agent.py",
    "jarvis_dashboard_runtime.py",
    str(CORE.relative_to(ROOT)).replace("\\", "/"),
]


def _stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _hud(payload):
    try:
        import websocket
        ws = websocket.create_connection("ws://127.0.0.1:8765", timeout=0.8)
        ws.send(json.dumps({"source": "JARVIS", **payload}, ensure_ascii=False))
        ws.close()
    except Exception:
        pass


def _desktop():
    from pywinauto import Desktop
    return Desktop(backend="uia")


def _chatgpt_window():
    windows = []
    try:
        windows = _desktop().windows(visible_only=True)
    except Exception:
        return None
    for win in windows:
        title = f"{win.window_text()} {win.element_info.name}".lower()
        if "chatgpt" in title:
            return win
    return None


def _focus_and_open():
    from windows_control import launch_chatgpt_classic
    result = launch_chatgpt_classic()
    if isinstance(result, tuple):
        ok, message = result
    else:
        ok, message = bool(result), "ChatGPT Classic focused."
    if not ok:
        raise RuntimeError(message)
    time.sleep(0.8)


def _click_composer():
    import pyautogui
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active:
            pyautogui.click(int(active.left + active.width * 0.52), int(active.top + active.height * 0.89))
            time.sleep(0.2)
            return
    except Exception:
        pass
    w, h = pyautogui.size()
    pyautogui.click(int(w * 0.52), int(h * 0.90))
    time.sleep(0.2)


def _send(text):
    import pyperclip
    import pyautogui
    pyperclip.copy(str(text))
    _click_composer()
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")


def _copy_latest_assistant():
    """Use the latest accessible Copy button in ChatGPT."""
    win = _chatgpt_window()
    if win is None:
        return None
    buttons = []
    try:
        buttons = [
            b for b in win.descendants(control_type="Button")
            if "copy" in str(b.window_text() or b.element_info.name or "").lower()
            and b.is_visible()
        ]
    except Exception:
        return None
    if not buttons:
        return None
    try:
        buttons[-1].click_input()
    except Exception:
        try:
            buttons[-1].invoke()
        except Exception:
            return None
    time.sleep(0.25)
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        return None


def _runtime_python_paths():
    """Return only live JARVIS runtime files; never scan backups/patch scripts."""
    names = [
        "windows_control.py",
        "Tahrun.py",
        "brain.py",
        "voice.py",
        "actions.py",
        "music_agent.py",
        "youtube_agent.py",
        "jarvis_dashboard_runtime.py",
        "jarvis_chatgpt_operator.py",
        "jarvis_source_agent.py",
    ]
    return [ROOT / name for name in names if (ROOT / name).exists()]


def _validate_python():
    errors = []
    checked = []
    for path in _runtime_python_paths():
        try:
            py_compile.compile(str(path), doraise=True)
            checked.append(str(path.relative_to(ROOT)))
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return checked, errors


def _validate_hud_build():
    package = HUD / "package.json"
    if not package.exists():
        return True, "HUD package.json not present; Python-only validation completed."
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(HUD),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            return True, "HUD Vite build: PASS"
        return False, "HUD Vite build failed:\n" + (result.stderr or result.stdout)[-5000:]
    except FileNotFoundError:
        return False, "npm was not found."
    except subprocess.TimeoutExpired:
        return False, "HUD Vite build timed out."
    except Exception as exc:
        return False, f"HUD build error: {exc}"


def _read_sources():
    chunks = []
    for rel in KEY_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            # Keep individual files bounded so ChatGPT gets the full active
            # file when it is reasonably sized and a clear truncation marker otherwise.
            if len(text) > 60000:
                text = text[:60000] + "\n[TRUNCATED AFTER 60000 CHARACTERS]\n"
            chunks.append(f"\n===== FILE: {rel} =====\n{text}\n===== END FILE =====\n")
        except Exception as exc:
            chunks.append(f"===== FILE ERROR: {rel}: {exc} =====")
    return "".join(chunks)


def _parse_patches(response):
    """Parse strict SEARCH/REPLACE blocks produced by ChatGPT."""
    import re
    pattern = re.compile(
        r"FILE:\s*(?P<file>[^\n]+?)\s*\n"
        r"OLD:\s*\n<<<\n(?P<old>.*?)\n>>>\n"
        r"NEW:\s*\n<<<\n(?P<new>.*?)\n>>>",
        re.S,
    )
    patches = []
    for match in pattern.finditer(response or ""):
        rel = match.group("file").strip().replace("\\", "/")
        path = (ROOT / rel).resolve()
        if ROOT.resolve() not in path.parents:
            continue
        old = match.group("old")
        new = match.group("new")
        if not old.strip() or old == new:
            continue
        patches.append({"file": rel, "old": old, "new": new})
    return patches


def _save_pending(report, patches, discussion):
    PENDING.write_text(
        json.dumps(
            {
                "created_at": _stamp(),
                "report": report,
                "patches": patches,
                "discussion": discussion,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def pending_exists():
    return PENDING.exists()


def cancel_pending():
    if PENDING.exists():
        PENDING.unlink()
    _hud({"type": "SOURCE_FIX_REPORT", "report": {"status": "cancelled"}})
    return True, "Pending fix cancelled."


def review(problem: str):
    checked, errors = _validate_python()
    build_ok, build_detail = _validate_hud_build()
    source = _read_sources()
    validation = {
        "python_checked": len(checked),
        "python_errors": errors,
        "hud_build": build_detail,
    }

    _focus_and_open()
    first_prompt = f"""
You are JARVIS's senior code-review partner.

USER PROBLEM:
{problem}

CURRENT VALIDATION:
{json.dumps(validation, indent=2, ensure_ascii=False)}

DISCUSSION ROUND 1:
Diagnose the problem from the validation and project context. Do not apply anything.
Explain which files matter and what evidence supports the diagnosis.
Then outline a safe fix and what should be validated after it.
""".strip()
    _send(first_prompt)
    time.sleep(5)
    discussion1 = _copy_latest_assistant() or ""
    if not discussion1:
        return False, "ChatGPT response could not be collected through the desktop UI."

    second_prompt = f"""
Continue the repair discussion.

Your previous review was:
{discussion1[-12000:]}

Now inspect the active source below and produce the exact proposed patch.
Do NOT claim it was applied.
Do NOT modify anything locally.
Use this exact machine-readable format for every change:

FILE: relative/path/to/file
OLD:
<<<
exact existing text
>>>
NEW:
<<<
exact replacement text
>>>

After the patch blocks, provide a compact VALIDATION PLAN section.
Do not output a full rewritten file unless absolutely necessary.

{source}
""".strip()
    _send(second_prompt)
    time.sleep(5)
    discussion2 = _copy_latest_assistant() or ""
    if not discussion2:
        return False, "ChatGPT second discussion response could not be collected."

    patches = _parse_patches(discussion2)
    if not patches:
        return False, "ChatGPT discussion completed, but no safe exact SEARCH/REPLACE patch was returned."

    report = {
        "status": "ready_for_confirmation",
        "problem": problem,
        "validation_before": validation,
        "files": [p["file"] for p in patches],
        "patch_count": len(patches),
        "discussion_round_1": discussion1[-8000:],
        "discussion_round_2": discussion2[-12000:],
        "patches": [{"file": p["file"], "old": p["old"], "new": p["new"]} for p in patches],
    }
    _save_pending(report, patches, [discussion1, discussion2])
    _hud({"type": "SOURCE_FIX_REPORT", "report": report})
    return True, report


def apply_pending():
    if not PENDING.exists():
        return False, "No pending ChatGPT source-code fix is waiting for approval."
    data = json.loads(PENDING.read_text(encoding="utf-8"))
    patches = data.get("patches", [])
    if not patches:
        return False, "Pending fix is empty."

    originals = {}
    backups = []
    try:
        for patch in patches:
            path = (ROOT / patch["file"]).resolve()
            if ROOT.resolve() not in path.parents or not path.exists():
                raise RuntimeError(f"Invalid patch target: {patch['file']}")
            current = path.read_text(encoding="utf-8", errors="replace")
            if patch["old"] not in current:
                raise RuntimeError(f"Expected source block not found in {patch['file']}")
            originals[str(path)] = current

        for patch in patches:
            path = (ROOT / patch["file"]).resolve()
            backup = path.with_name(f"{path.stem}.before_chatgpt_apply_{_stamp()}{path.suffix}")
            shutil.copy2(path, backup)
            backups.append(str(backup))
            current = path.read_text(encoding="utf-8", errors="replace")
            path.write_text(current.replace(patch["old"], patch["new"], 1), encoding="utf-8")

        _, py_errors = _validate_python()
        if py_errors:
            raise RuntimeError("Python validation failed:\n" + "\n".join(py_errors[:20]))
        build_ok, build_detail = _validate_hud_build()
        if not build_ok:
            raise RuntimeError(build_detail)

        report = data.get("report", {})
        report["status"] = "applied_and_validated"
        report["validation_after"] = {"python_errors": [], "hud_build": build_detail}
        report["backups"] = backups
        PENDING.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        _hud({"type": "SOURCE_FIX_REPORT", "report": report})
        return True, f"ChatGPT fix applied and validated. Backups: {len(backups)}"

    except Exception as exc:
        for path_text, old_text in originals.items():
            try:
                Path(path_text).write_text(old_text, encoding="utf-8")
            except Exception:
                pass
        return False, f"Fix failed validation; all changed files were restored. Reason: {exc}"


def show_pending():
    if not PENDING.exists():
        return False, "No pending ChatGPT source-code report is available."
    data = json.loads(PENDING.read_text(encoding="utf-8"))
    report = data.get("report", data)
    _hud({"type": "SOURCE_FIX_REPORT", "report": report})
    return True, report


def _is_apply(text):
    t = text.lower().strip()
    return any(x in t for x in ("yes apply", "haan apply", "apply it", "apply karo", "apply kar do", "haan kar do"))


def _is_show(text):
    t = text.lower().strip()
    return any(x in t for x in ("show me", "mujhe dikhao", "ek baar dikhao", "report dikhao", "changes dikhao"))


def _is_cancel(text):
    t = text.lower().strip()
    return any(x in t for x in ("cancel", "mat karo", "don't apply", "apply mat karo"))


def _is_source_request(text):
    t = text.lower().strip()
    source_words = ("source code", "apna code", "own code", "jarvis code", "source check", "debug yourself", "khud ko fix", "code fix")
    return any(word in t for word in source_words)


def handle_command(text):
    """Return (handled, status, detail)."""
    text = str(text or "").strip()
    if not text:
        return False, None, None

    if pending_exists() and _is_apply(text):
        ok, detail = apply_pending()
        return True, "apply_success" if ok else "apply_failed", detail
    if pending_exists() and _is_show(text):
        ok, detail = show_pending()
        return True, "show_report" if ok else "show_failed", detail
    if pending_exists() and _is_cancel(text):
        ok, detail = cancel_pending()
        return True, "cancelled" if ok else "cancel_failed", detail
    if _is_source_request(text):
        ok, detail = review(text)
        return True, "review_ready" if ok else "review_failed", detail
    return False, None, None
