"""Persistent local Study Mode memory for JARVIS.

All files are written locally under ./Study.  This module also exposes the
legacy API used by Tahrun.py so that older call sites remain compatible.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent / "Study"
MEMORY_FILE = ROOT / "Study_Memory.json"
DEFAULT_LEVEL = "Diploma Computer Science"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _slug(value: Any, fallback: str = "General") -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(value or "")).strip()
    value = re.sub(r"\s+", "_", value)
    return value[:70] or fallback


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def load_memory() -> dict[str, Any]:
    data = _read(MEMORY_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 2)
    data.setdefault("created_at", _now())
    data.setdefault("updated_at", _now())
    data.setdefault("active_subject", "")
    data.setdefault("study_mode", False)
    data.setdefault("level", DEFAULT_LEVEL)
    if not isinstance(data.get("subjects"), dict):
        data["subjects"] = {}
    return data


def _subject_key(memory: dict[str, Any], subject: str) -> str:
    display = str(subject or "General").strip() or "General"
    key = _slug(display)
    subjects = memory.get("subjects", {})
    # Keep existing data made by older builds whose whitespace normalization
    # accidentally left spaces in the dictionary key and folder name.
    legacy = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", display).strip()[:70]
    if isinstance(subjects, dict) and key not in subjects and legacy in subjects:
        return legacy
    return key


def _ensure_subject(memory: dict[str, Any], subject: str) -> tuple[str, dict[str, Any]]:
    display = str(subject or "General").strip() or "General"
    key = _subject_key(memory, display)
    subjects = memory.setdefault("subjects", {})
    entry = subjects.setdefault(
        key,
        {
            "display_name": display,
            "topics": [],
            "sessions": [],
            "weak_topics": [],
            "learning_log": [],
        },
    )
    for field in ("topics", "sessions", "weak_topics", "learning_log"):
        if not isinstance(entry.get(field), list):
            entry[field] = []

    folder = ROOT / key
    folder.mkdir(parents=True, exist_ok=True)
    notes = folder / f"Study_{key}.txt"
    history = folder / "Revision_History.json"
    entry["notes_file"] = str(notes.relative_to(ROOT))
    entry["revision_history_file"] = str(history.relative_to(ROOT))
    if not notes.exists():
        notes.write_text(f"# Study Notes: {display}\n", encoding="utf-8")
    if not history.exists():
        _write(history, {"attempts": []})
    return key, entry


def set_mode(enabled: bool, subject: str | None = None) -> dict[str, Any]:
    memory = load_memory()
    memory["study_mode"] = bool(enabled)
    if subject:
        memory["active_subject"] = str(subject).strip()
        _ensure_subject(memory, subject)
    memory["updated_at"] = _now()
    _write(MEMORY_FILE, memory)
    return current()


def add_notes(subject: str, notes: str, topic: str = "") -> str:
    text = str(notes or "").strip()
    if not text:
        raise ValueError("Study notes are empty.")
    memory = load_memory()
    key, entry = _ensure_subject(memory, subject)
    stamp = _now()
    path = ROOT / key / f"Study_{key}.txt"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"\n\n## {str(topic or '').strip() or 'Notes'} — {stamp}\n\n{text}\n")
    clean_topic = str(topic or "").strip()
    if clean_topic and clean_topic not in entry["topics"]:
        entry["topics"].append(clean_topic)
    entry["updated_at"] = stamp
    memory["active_subject"] = str(subject or "General").strip() or "General"
    memory["updated_at"] = stamp
    _write(MEMORY_FILE, memory)
    return str(path)


def save_session(
    subject: str,
    *,
    video_url: str = "",
    video_title: str = "",
    timestamp_seconds: float | None = None,
    screenshot_path: str = "",
    topic: str = "",
    progress: str = "",
) -> dict[str, Any]:
    """Save study/video metadata. Timestamp must come from actual playback data."""
    memory = load_memory()
    _, entry = _ensure_subject(memory, subject)
    stamp = _now()
    timestamp = None
    if timestamp_seconds is not None:
        try:
            candidate = float(timestamp_seconds)
            if math.isfinite(candidate) and candidate >= 0:
                timestamp = round(candidate, 3)
        except (TypeError, ValueError):
            timestamp = None
    session = {
        "saved_at": stamp,
        "video_url": str(video_url or ""),
        "video_title": str(video_title or ""),
        "timestamp_seconds": timestamp,
        "screenshot_path": str(screenshot_path or ""),
        "topic": str(topic or ""),
        "progress": str(progress or ""),
    }
    entry["sessions"].append(session)
    entry["updated_at"] = stamp
    memory["active_subject"] = str(subject or "General").strip() or "General"
    memory["updated_at"] = stamp
    _write(MEMORY_FILE, memory)
    return session


def latest_session(subject: str | None = None) -> dict[str, Any] | None:
    memory = load_memory()
    name = subject or memory.get("active_subject", "") or "General"
    entry = memory.get("subjects", {}).get(_subject_key(memory, name), {})
    sessions = entry.get("sessions", []) if isinstance(entry, dict) else []
    return sessions[-1] if sessions else None


def record_learning(subject: str, topic: str, understood: bool, detail: str = "") -> dict[str, Any]:
    memory = load_memory()
    _, entry = _ensure_subject(memory, subject)
    topic = str(topic or "").strip() or "General"
    stamp = _now()
    item = {
        "at": stamp,
        "topic": topic,
        "understood": bool(understood),
        "detail": str(detail or ""),
    }
    entry["learning_log"].append(item)
    weak = entry["weak_topics"]
    if not understood and topic not in weak:
        weak.append(topic)
    elif understood and topic in weak:
        weak.remove(topic)
    entry["updated_at"] = stamp
    memory["active_subject"] = str(subject or "General").strip() or "General"
    memory["updated_at"] = stamp
    _write(MEMORY_FILE, memory)
    return item


def record_revision(
    subject: str, question: str, answer: str, correct: bool, topic: str = ""
) -> dict[str, Any]:
    memory = load_memory()
    key, entry = _ensure_subject(memory, subject)
    path = ROOT / key / "Revision_History.json"
    history = _read(path, {"attempts": []})
    if not isinstance(history, dict):
        history = {"attempts": []}
    if not isinstance(history.get("attempts"), list):
        history["attempts"] = []
    stamp = _now()
    attempt = {
        "at": stamp,
        "topic": str(topic or "").strip() or "General",
        "question": str(question or ""),
        "answer": str(answer or ""),
        "correct": bool(correct),
    }
    history["attempts"].append(attempt)
    _write(path, history)
    weak = entry["weak_topics"]
    if attempt["correct"] and attempt["topic"] in weak:
        weak.remove(attempt["topic"])
    elif not attempt["correct"] and attempt["topic"] not in weak:
        weak.append(attempt["topic"])
    entry["updated_at"] = stamp
    memory["active_subject"] = str(subject or "General").strip() or "General"
    memory["updated_at"] = stamp
    _write(MEMORY_FILE, memory)
    return attempt


def set_pending_quiz(subject: str, topic: str, question: str, expected_answer: str) -> dict[str, Any]:
    """Persist a single unanswered quiz question and its private grading rubric."""
    memory = load_memory()
    subject_name = str(subject or "General").strip() or "General"
    _ensure_subject(memory, subject_name)
    pending = {
        "subject": subject_name,
        "topic": str(topic or "General").strip() or "General",
        "question": str(question or "").strip(),
        "expected_answer": str(expected_answer or "").strip(),
        "asked_at": _now(),
    }
    if not pending["question"] or not pending["expected_answer"]:
        raise ValueError("Quiz question and expected answer are required.")
    memory["pending_quiz"] = pending
    memory["active_subject"] = subject_name
    memory["study_mode"] = True
    memory["updated_at"] = _now()
    _write(MEMORY_FILE, memory)
    return pending


def pending_quiz() -> dict[str, Any] | None:
    memory = load_memory()
    item = memory.get("pending_quiz")
    if not isinstance(item, dict) or not item.get("question") or not item.get("expected_answer"):
        return None
    return dict(item)


def clear_pending_quiz() -> None:
    memory = load_memory()
    memory.pop("pending_quiz", None)
    memory["updated_at"] = _now()
    _write(MEMORY_FILE, memory)


def current() -> dict[str, Any]:
    """Return the combined current + legacy Study Mode status shape."""
    memory = load_memory()
    subject = str(memory.get("active_subject") or "General")
    entry = memory.get("subjects", {}).get(_subject_key(memory, subject), {})
    if not isinstance(entry, dict):
        entry = {}
    weak_topics = list(entry.get("weak_topics", []))
    strong_topics = []
    for item in entry.get("learning_log", []):
        if isinstance(item, dict) and item.get("understood"):
            topic = str(item.get("topic") or "").strip()
            if topic and topic not in strong_topics:
                strong_topics.append(topic)
    return {
        **memory,
        "active": bool(memory.get("study_mode")),
        "level": str(memory.get("level") or DEFAULT_LEVEL),
        "subject": subject,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
    }


def professor_system_prompt() -> str:
    return (
        "You are JARVIS Study Mode, a careful personal Computer Science tutor. "
        "Teach in natural Roman Urdu/Hinglish unless the user asks otherwise. "
        "Use structured explanations, intuition, step-by-step mechanisms, practical examples, "
        "code where useful, common mistakes, a recap, and checkpoint questions. "
        "For quiz/test requests ask one question at a time and wait for the learner's answer. "
        "Do not claim the learner understood a topic unless they demonstrate it. "
        "For screen-derived material, distinguish what is visible from any explanation you add."
    )


# Legacy entry points expected by older Tahrun.py code.
def start(*args: Any, **kwargs: Any) -> dict[str, Any]:
    subject = kwargs.get("subject")
    level = kwargs.get("level")
    if len(args) >= 2 and not subject:
        level = str(args[0])
        subject = str(args[1])
    elif subject is None:
        for value in args:
            if isinstance(value, str) and value.strip().lower() not in {
                "start", "study_mode", "on", "true", "science"
            }:
                subject = value
                break
    memory = load_memory()
    if level:
        memory["level"] = str(level)
        _write(MEMORY_FILE, memory)
    return set_mode(True, str(subject).strip() if subject else None)


def stop(*args: Any, **kwargs: Any) -> dict[str, Any]:
    state = set_mode(False)
    memory = load_memory()
    memory.pop("pending_quiz", None)
    memory["updated_at"] = _now()
    _write(MEMORY_FILE, memory)
    return current()
