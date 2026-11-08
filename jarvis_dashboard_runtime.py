"""JARVIS dashboard runtime: bidirectional WebSocket + telemetry + BSE + focus."""
from __future__ import annotations

import asyncio
import json
import os
import queue
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any

HOST = os.getenv("JARVIS_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = 8765
DASHBOARD_URL = "http://127.0.0.1:5173"
PROJECT = Path(__file__).resolve().parent
HUD_DIR = PROJECT / "JARVIS_HUD_V2"

_COMMANDS: queue.Queue[str] = queue.Queue()
_SERVER_STARTED = False
_TELEMETRY_STARTED = False
_LOOP: asyncio.AbstractEventLoop | None = None
_CLIENTS: set[Any] = set()
_LOCK = threading.Lock()
_YOUTUBE_STATE_LOCK = threading.Lock()
_YOUTUBE_PLAYBACK: dict[str, Any] = {}


def get_youtube_playback_state(max_age: float = 10.0) -> dict[str, Any]:
    """Return fresh playback metadata sent by the optional local Chrome extension."""
    with _YOUTUBE_STATE_LOCK:
        state = dict(_YOUTUBE_PLAYBACK)
    if not state:
        return {}
    age = max(0.0, time.time() - float(state.get("updated_at", 0.0) or 0.0))
    if age > max(0.0, float(max_age)):
        return {}
    state["age_seconds"] = age
    return state


def _json(payload: dict[str, Any]) -> str:
    return json.dumps({"source": "JARVIS", **payload}, ensure_ascii=False)


async def _broadcast(payload: dict[str, Any]) -> None:
    if not _CLIENTS:
        return
    data = _json(payload)
    dead = []
    for ws in tuple(_CLIENTS):
        try:
            await ws.send(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _CLIENTS.discard(ws)


def publish(event_type: str, **data: Any) -> None:
    loop = _LOOP
    if loop is None:
        return
    payload = {"type": event_type, **data}
    try:
        asyncio.run_coroutine_threadsafe(_broadcast(payload), loop)
    except Exception:
        pass


async def _handler(ws, *_) -> None:
    _CLIENTS.add(ws)
    try:
        await ws.send(_json({"type": "SYSTEM", "online": True}))
        async for raw in ws:
            try:
                data = json.loads(raw or "{}")
            except Exception:
                continue

            source = str(data.get("source", ""))
            event_type = str(data.get("type", ""))

            if source == "YOUTUBE_EXTENSION" and event_type == "YOUTUBE_PROGRESS":
                raw_url = str(data.get("url") or "")[:2000]
                try:
                    parsed_url = urllib.parse.urlparse(raw_url)
                    host = (parsed_url.hostname or "").lower()
                    if parsed_url.scheme != "https" or host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
                        continue
                    video_id = str(data.get("video_id") or "")[:32]
                    if not video_id or not all(ch.isalnum() or ch in "-_" for ch in video_id):
                        continue
                    current_time = max(0.0, float(data.get("current_time", 0.0)))
                    duration = max(0.0, float(data.get("duration", 0.0)))
                except (TypeError, ValueError):
                    continue
                playback = {
                    "url": raw_url,
                    "video_id": video_id,
                    "title": str(data.get("title") or "YouTube video")[:300],
                    "current_time": current_time,
                    "duration": duration,
                    "paused": bool(data.get("paused", False)),
                    "updated_at": time.time(),
                }
                with _YOUTUBE_STATE_LOCK:
                    _YOUTUBE_PLAYBACK.clear()
                    _YOUTUBE_PLAYBACK.update(playback)
                publish("YOUTUBE_PROGRESS", **playback)
                continue

            if source == "HUD" and event_type == "COMMAND":
                command = str(data.get("command", "")).strip()
                if command:
                    _COMMANDS.put(command)
                    publish("COMMAND", command=command)
                    publish("ACTIVITY", text=f"YOU // {command}")
                continue

            # Runtime is also the relay for Tahrun's short-lived live-bridge sends.
            if source == "JARVIS":
                relay = dict(data)
                relay.pop("source", None)
                await _broadcast(relay)
                if False and event_type in {"RESULT", "SPEAKING"}:
                    threading.Thread(target=focus_dashboard, daemon=True).start()
    finally:
        _CLIENTS.discard(ws)


async def _server_main() -> None:
    global _LOOP
    _LOOP = asyncio.get_running_loop()
    try:
        import websockets
    except ImportError as exc:
        print(f"[JARVIS HUD] websockets package missing: {exc}", flush=True)
        return

    async with websockets.serve(_handler, HOST, PORT, ping_interval=20, ping_timeout=20):
        print(f"[JARVIS HUD] WebSocket server: ws://{HOST}:{PORT}", flush=True)
        await asyncio.Future()


def _server_thread() -> None:
    try:
        asyncio.run(_server_main())
    except Exception as exc:
        print(f"[JARVIS HUD] server error: {exc}", flush=True)


def start_server() -> None:
    global _SERVER_STARTED
    with _LOCK:
        if _SERVER_STARTED:
            return
        _SERVER_STARTED = True
    threading.Thread(target=_server_thread, name="JarvisHUDWebSocket", daemon=True).start()


def get_dashboard_command() -> str:
    try:
        return _COMMANDS.get_nowait()
    except queue.Empty:
        return ""


def _url_live() -> bool:
    try:
        with urllib.request.urlopen(DASHBOARD_URL, timeout=1.3):
            return True
    except Exception:
        return False


def _start_react() -> None:
    if _url_live():
        return
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm or not HUD_DIR.exists():
        print("[JARVIS HUD] React project or npm not found.", flush=True)
        return
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
            cwd=str(HUD_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except Exception as exc:
        print(f"[JARVIS HUD] React start error: {exc}", flush=True)
        return

    deadline = time.time() + 18
    while time.time() < deadline:
        if _url_live():
            return
        time.sleep(0.5)


def _chrome_path() -> str | None:
    candidates = [
        shutil.which("chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def focus_dashboard() -> None:
    """Bring the dashboard window back without forcing it permanently topmost."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "JARVIS REAL DASHBOARD")
        if hwnd:
            SW_MAXIMIZE = 3
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def start_real_dashboard() -> None:
    start_server()
    _start_react()

    def open_window() -> None:
        time.sleep(0.5)
        chrome = _chrome_path()
        try:
            if chrome:
                subprocess.Popen([chrome, f"--app={DASHBOARD_URL}", "--start-maximized"])
            else:
                os.startfile(DASHBOARD_URL)  # type: ignore[attr-defined]
        except Exception as exc:
            print(f"[JARVIS HUD] browser launch error: {exc}", flush=True)
            return
        time.sleep(2.2)
        focus_dashboard()

    threading.Thread(target=open_window, name="JarvisHUDWindow", daemon=True).start()


def _gpu_percent() -> float | None:
    try:
        p = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
        value = p.stdout.strip().splitlines()[0] if p.stdout.strip() else ""
        return float(value) if value else None
    except Exception:
        return None


def _internet_ok() -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=0.8):
            return True
    except Exception:
        return False


def _market_now() -> dict[str, Any]:
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    trading = now.weekday() < 5 and dt_time(9, 15) <= now.time() <= dt_time(15, 30)
    if not trading:
        return {"open": False, "symbol": "BSE", "sensex": None, "change": None, "percent": None}

    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EBSESN?range=1d&interval=1m"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = payload["chart"]["result"][0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        previous = meta.get("previousClose") or meta.get("chartPreviousClose")
        if price is None or previous is None:
            return {"open": False, "symbol": "BSE", "sensex": None, "change": None, "percent": None}
        change = float(price) - float(previous)
        percent = (change / float(previous) * 100.0) if previous else None
        return {
            "open": True,
            "symbol": "BSE / SENSEX",
            "sensex": round(float(price), 2),
            "change": round(change, 2),
            "percent": round(percent, 2) if percent is not None else None,
        }
    except Exception:
        # During an active market session, don't fabricate a quote.
        return {"open": False, "symbol": "BSE", "sensex": None, "change": None, "percent": None}


def _telemetry_loop() -> None:
    try:
        import psutil
    except Exception as exc:
        print(f"[JARVIS HUD] psutil unavailable: {exc}", flush=True)
        return

    while True:
        try:
            battery = None
            b = psutil.sensors_battery()
            if b is not None:
                battery = float(b.percent)
            wifi = any(info.isup for info in psutil.net_if_stats().values())
            payload = {
                "cpu": round(psutil.cpu_percent(interval=0.35), 1),
                "ram": round(psutil.virtual_memory().percent, 1),
                "gpu": _gpu_percent(),
                "battery": battery,
                "online": bool(wifi and _internet_ok()),
            }
            publish("SYSTEM", **payload)
            publish("MARKET", **_market_now())
        except Exception as exc:
            print(f"[JARVIS HUD] telemetry error: {exc}", flush=True)
        time.sleep(2.0)


def start_telemetry() -> None:
    global _TELEMETRY_STARTED
    with _LOCK:
        if _TELEMETRY_STARTED:
            return
        _TELEMETRY_STARTED = True
    start_server()
    threading.Thread(target=_telemetry_loop, name="JarvisHUDTelemetry", daemon=True).start()







