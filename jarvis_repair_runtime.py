"""Small, failure-safe runtime error reporter for JARVIS AutoRepair.

This module never edits code and never makes network requests. It appends sanitized
JSONL events for the independent repair manager to inspect.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
EVENT_FILE = BASE_DIR / "jarvis_repair_events.jsonl"
_LOCK = threading.Lock()

_SECRET_PATTERNS = (
    re.compile(r"(?i)([A-Z0-9_.-]*(?:API_KEY|ACCESS_TOKEN|REFRESH_TOKEN|TOKEN|PASSWORD|PASSWD|SECRET|_KEY))\s*([:=])\s*([^\s,;]+)"),
    re.compile(r"(?i)([?&](?:key|api_key|token|access_token|client_secret|password)=)[^&#\s]+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gsk_[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{25,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
)


def sanitize_text(value: Any, limit: int = 6000) -> str:
    text = str(value or "")
    text = _SECRET_PATTERNS[0].sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    text = _SECRET_PATTERNS[1].sub(lambda m: f"{m.group(1)}[REDACTED]", text)
    text = _SECRET_PATTERNS[2].sub("Bearer [REDACTED]", text)
    text = _SECRET_PATTERNS[3].sub("[REDACTED_SECRET]", text)
    return text[:limit]


def _relative_project_frame(frame: traceback.FrameSummary) -> dict[str, Any] | None:
    try:
        path = Path(frame.filename).resolve()
        relative = path.relative_to(BASE_DIR)
    except (OSError, ValueError):
        return None

    if path.suffix.lower() != ".py" or not path.is_file():
        return None
    rel_text = relative.as_posix()
    if rel_text == "jarvis_repair_manager.py" or rel_text == "jarvis_repair_runtime.py":
        return None
    lower_parts = [part.lower() for part in relative.parts]
    if any(token in part for part in lower_parts for token in ("backup", "before_", "autorepair")):
        return None

    return {
        "file": rel_text,
        "line": int(frame.lineno or 0),
        "function": sanitize_text(frame.name, 160),
    }


def record_exception(kind: str, error: BaseException) -> bool:
    """Append a sanitized exception event; never throw into JARVIS's main loop."""
    try:
        frames = traceback.extract_tb(error.__traceback__) if error.__traceback__ else []
        project_frames = [entry for frame in frames if (entry := _relative_project_frame(frame))]
        target = project_frames[-1] if project_frames else {}
        message = sanitize_text(str(error), 1600)
        exc_type = type(error).__name__
        fingerprint_source = "|".join((str(kind), exc_type, re.sub(r"\s+", " ", message).strip(), str(target.get("file", ""))))
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8", "replace")).hexdigest()[:24]

        formatted = sanitize_text("".join(traceback.format_exception(type(error), error, error.__traceback__)), 7000)
        event = {
            "event_id": uuid.uuid4().hex,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": sanitize_text(kind, 80),
            "exception_type": exc_type,
            "message": message,
            "traceback": formatted,
            "target_file": target.get("file", ""),
            "target_line": target.get("line", 0),
            "target_function": target.get("function", ""),
            "fingerprint": fingerprint,
        }
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with _LOCK:
            EVENT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with EVENT_FILE.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
        return True
    except Exception:
        # Error reporting must never become a second failure source.
        return False
