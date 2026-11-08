"""JARVIS local gateway: connects Chat Mode to the existing project brain.py."""
from __future__ import annotations
import json, os, sys, threading, urllib.request, urllib.error, importlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent
PROJECT_ROOT = Path(os.environ.get("JARVIS_PROJECT_ROOT", str(WORKSPACE_DIR.parent))).resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BRAIN_LOCK = threading.RLock()

class GatewayError(Exception):
    pass

def post_json(url: str, headers: dict, payload: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={**headers, "Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise GatewayError(f"Provider HTTP {e.code}: {e.read().decode(errors='replace')[:1000]}")
    except urllib.error.URLError as e:
        raise GatewayError(f"Provider connection failed: {e.reason}")

def load_brain():
    brain_file = PROJECT_ROOT / "brain.py"
    if not brain_file.is_file():
        raise GatewayError(f"brain.py not found in project folder: {PROJECT_ROOT}")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    module = importlib.import_module("brain")
    fn = getattr(module, "ask_ai", None)
    if not callable(fn):
        raise GatewayError("brain.py does not expose callable ask_ai(text)")
    return fn

def call_jarvis(messages: list[dict]) -> str:
    fn = load_brain()
    transcript = []
    for item in messages[-12:]:
        role = "User" if item.get("role") == "user" else "JARVIS"
        content = str(item.get("content", "")).strip()
        if content:
            transcript.append(f"{role}: {content}")
    if not transcript:
        raise GatewayError("No message text supplied")
    prompt = "CHAT WORKSPACE CONVERSATION (continue naturally; answer the latest user message):\n" + "\n".join(transcript)
    with BRAIN_LOCK:
        answer = fn(prompt)
    if not isinstance(answer, str):
        answer = str(answer)
    if not answer.strip():
        raise GatewayError("brain.ask_ai returned an empty response")
    return answer.strip()

def call_openai(model, messages):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise GatewayError("OPENAI_API_KEY missing from backend/.env")
    d = post_json("https://api.openai.com/v1/chat/completions",
                  {"Authorization": f"Bearer {key}"}, {"model": model, "messages": messages})
    return d["choices"][0]["message"]["content"]

def call_anthropic(model, messages):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise GatewayError("ANTHROPIC_API_KEY missing from backend/.env")
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    chat = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
    d = post_json("https://api.anthropic.com/v1/messages",
                  {"x-api-key": key, "anthropic-version": "2023-06-01"},
                  {"model": model, "max_tokens": 4096, "system": system, "messages": chat})
    return "".join(x.get("text", "") for x in d.get("content", []))

def call_gemini(model, messages):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise GatewayError("GEMINI_API_KEY missing from backend/.env")
    contents = [{"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
    d = post_json(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                  {}, {"contents": contents})
    return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])

class Handler(BaseHTTPRequestHandler):
    # Do not name this method "headers": BaseHTTPRequestHandler already uses
    # self.headers for the incoming request headers.
    def send_json_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        origin = self.headers.get("Origin", "")
        allowed = {"http://127.0.0.1:5174", "http://localhost:5174"}
        if origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def write_json(self, status, payload):
        self.send_json_headers(status)
        if status != 204:
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.write_json(204, {})

    def do_GET(self):
        if self.path.rstrip("/") == "/api/health":
            try:
                fn = load_brain()
                self.write_json(200, {
                    "ok": True, "service": "JARVIS Local Gateway",
                    "local_brain": True, "brain_function": fn.__name__,
                    "project_root": str(PROJECT_ROOT)
                })
            except Exception as e:
                self.write_json(503, {"ok": False, "local_brain": False, "error": str(e)})
        else:
            self.write_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/api/chat":
            self.write_json(404, {"error": "Not found"})
            return
        try:
            # BaseHTTPRequestHandler exposes incoming headers as self.headers.
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > 2_000_000:
                raise GatewayError("Request body missing or too large")
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            provider = payload.get("provider", "jarvis")
            model = payload.get("model", "")
            messages = payload.get("messages", [])
            if not isinstance(messages, list) or not messages:
                raise GatewayError("At least one chat message is required")
            for m in messages:
                if not isinstance(m, dict) or m.get("role") not in ("user", "assistant", "system") or not isinstance(m.get("content"), str):
                    raise GatewayError("Invalid chat message")
            if provider in ("jarvis", "brain", "local"):
                reply = call_jarvis(messages)
            elif provider == "openai":
                reply = call_openai(model, messages)
            elif provider == "anthropic":
                reply = call_anthropic(model, messages)
            elif provider == "gemini":
                reply = call_gemini(model, messages)
            else:
                raise GatewayError(f"Unsupported provider: {provider}")
            self.write_json(200, {"reply": reply, "provider": provider})
        except GatewayError as e:
            self.write_json(400, {"error": str(e)})
        except Exception as e:
            self.write_json(500, {"error": f"Gateway error: {type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        print("[JARVIS Gateway] " + fmt % args, flush=True)

if __name__ == "__main__":
    host = os.getenv("JARVIS_GATEWAY_HOST", "127.0.0.1")
    port = int(os.getenv("JARVIS_GATEWAY_PORT", "8766"))
    print(f"JARVIS Local Brain Gateway listening at http://{host}:{port}", flush=True)
    print(f"Project root: {PROJECT_ROOT}", flush=True)
    try:
        load_brain()
        print("PASS: brain.py ask_ai() loaded", flush=True)
    except Exception as e:
        print(f"WARNING: local brain not ready: {e}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
