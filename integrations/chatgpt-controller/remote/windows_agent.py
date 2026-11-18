"""Outbound-only connector between the hosted relay and existing JARVIS."""
from __future__ import annotations

import json
import os
import random
import ssl
import time
import urllib.error
import urllib.request

RELAY = os.environ["JARVIS_RELAY_URL"].rstrip("/")
TOKEN = os.environ["JARVIS_AGENT_TOKEN"]
LOCAL_GATEWAY = os.getenv("JARVIS_LOCAL_GATEWAY", "http://127.0.0.1:8766").rstrip("/")
LOCAL_HUD = os.getenv("JARVIS_LOCAL_HUD", "ws://127.0.0.1:8765")
SITE_BYPASS_TOKEN = os.getenv("JARVIS_SITE_BYPASS_TOKEN", "")
MAX_COMMAND = 400

if len(TOKEN) < 32:
    raise SystemExit("JARVIS_AGENT_TOKEN must be at least 32 characters")
if not RELAY.startswith("https://") and not RELAY.startswith("http://127.0.0.1:"):
    raise SystemExit("JARVIS_RELAY_URL must use HTTPS (loopback HTTP is allowed only for tests)")

SENSITIVE = (
    "delete", "remove", "erase", "format", "shutdown", "restart", "power off",
    "message", "whatsapp", "call ", "email", "payment", "pay ", "transfer",
    "buy ", "purchase", "order ", "microphone", "camera", "record", "listen",
    "stream", "share screen", "password", "api key", "token", "credential",
    "upload", "publish", "deploy", "install", "uninstall", "terminal",
    "powershell", "cmd.exe", "shell", "script", "run code", "execute code",
)


def _request(url: str, body: dict | None = None, timeout: float = 35) -> dict:
    data = json.dumps(body, separators=(",", ":")).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "JARVIS-Windows-Connector/1.0",
    }
    if SITE_BYPASS_TOKEN:
        headers["OAI-Sites-Authorization"] = "Bearer " + SITE_BYPASS_TOKEN
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as response:
        return json.loads(response.read(65536).decode("utf-8"))


def _local_json(path: str, body: dict | None = None, timeout: float = 4) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        LOCAL_GATEWAY + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read(65536).decode("utf-8"))


def _hud_probe() -> bool:
    import websocket
    ws = websocket.create_connection(LOCAL_HUD, timeout=2)
    try:
        ws.settimeout(2)
        return json.loads(ws.recv()).get("type") == "SYSTEM"
    finally:
        ws.close()


def _status() -> dict:
    gateway = {"online": False, "local_brain": False}
    hud = {"online": False}
    try:
        health = _local_json("/api/health")
        gateway = {"online": bool(health.get("ok")), "local_brain": bool(health.get("local_brain"))}
    except Exception as exc:
        gateway["error"] = type(exc).__name__
    try:
        hud["online"] = _hud_probe()
    except Exception as exc:
        hud["error"] = type(exc).__name__
    return {"connector_online": True, "gateway": gateway, "hud": hud}


def _ask(question: str) -> dict:
    question = str(question or "").strip()
    if not question or len(question) > 4000:
        raise ValueError("invalid question")
    response = _local_json(
        "/api/chat",
        {"provider": "jarvis", "messages": [{"role": "user", "content": question}]},
        timeout=100,
    )
    return {"reply": str(response.get("reply", "")), "provider": response.get("provider", "jarvis")}


def _command(command: str, confirmed: bool) -> dict:
    command = str(command or "").strip()
    if not command or len(command) > MAX_COMMAND:
        raise ValueError("invalid command")
    if any(term in command.casefold() for term in SENSITIVE) and confirmed is not True:
        return {"queued": False, "requires_confirmation": True}
    import websocket
    ws = websocket.create_connection(LOCAL_HUD, timeout=3)
    try:
        ws.settimeout(2)
        ws.recv()
        ws.send(json.dumps({"source": "HUD", "type": "COMMAND", "command": command}))
    finally:
        ws.close()
    return {"queued": True, "executed": "unknown", "command": command}


def execute(task: dict) -> dict:
    if not isinstance(task, dict) or not isinstance(task.get("arguments"), dict):
        raise ValueError("invalid task")
    name, arguments = task.get("name"), task["arguments"]
    if name == "jarvis_status":
        return _status()
    if name == "jarvis_ask":
        return _ask(arguments.get("question"))
    if name == "jarvis_command":
        return _command(arguments.get("command"), arguments.get("confirmed") is True)
    raise ValueError("unsupported task")


def run() -> None:
    failures = 0
    print("JARVIS remote connector started (outbound HTTPS only).", flush=True)
    while True:
        try:
            packet = _request(RELAY + "/agent/next?wait=20", timeout=30)
            task = packet.get("task")
            failures = 0
            if not task:
                continue
            try:
                payload = {"id": task["id"], "result": execute(task)}
            except Exception as exc:
                payload = {"id": task.get("id", ""), "result": None, "error": type(exc).__name__}
            _request(RELAY + "/agent/result", payload, timeout=35)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures = min(failures + 1, 8)
            delay = min(30.0, (2 ** failures) * 0.5) + random.random()
            print(f"Relay unavailable ({type(exc).__name__}); retrying in {delay:.1f}s", flush=True)
            time.sleep(delay)


if __name__ == "__main__":
    run()
