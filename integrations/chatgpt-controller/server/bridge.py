"""JARVIS local stdio MCP adapter. Existing JARVIS runtime is left unchanged."""
import json
import sys
import urllib.request

GATEWAY = "http://127.0.0.1:8766"
HUD = "ws://127.0.0.1:8765"
SENSITIVE = ("delete", "remove", "erase", "format", "shutdown", "restart",
             "payment", "pay ", "money", "password", "token", "api key",
             "message", "call", "email", "microphone", "camera", "record",
             "listen", "stream", "share screen", "upload", "publish",
             "deploy", "install", "terminal", "powershell", "script")
TOOLS = [
    {"name": "jarvis_status", "description": "Check the local JARVIS chat gateway and HUD service.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "jarvis_ask", "description": "Ask the existing JARVIS brain using local chat gateway.",
     "inputSchema": {"type": "object", "properties": {"question": {"type": "string", "maxLength": 4000}},
                     "required": ["question"], "additionalProperties": False}},
    {"name": "jarvis_command", "description": "Queue an explicit user command in the JARVIS HUD; does not prove execution.",
     "inputSchema": {"type": "object",
                     "properties": {"command": {"type": "string", "maxLength": 400},
                                    "confirmed": {"type": "boolean"}},
                     "required": ["command"], "additionalProperties": False}},
]

def http(path, body=None, timeout=3):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(GATEWAY + path, data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read(65536).decode("utf-8"))

def ws_connect():
    import websocket
    ws = websocket.create_connection(HUD, timeout=2)
    ws.settimeout(2)
    ws.recv()
    return ws

def call(name, args):
    if name == "jarvis_status":
        status = {"gateway": {"online": False}, "hud": {"online": False},
                  "remote_relay": "not_configured"}
        try:
            data = http("/api/health")
            status["gateway"] = {"online": bool(data.get("ok")),
                                 "local_brain": bool(data.get("local_brain"))}
        except Exception as e:
            status["gateway"]["error"] = str(e)[:160]
        try:
            ws = ws_connect()
            status["hud"]["online"] = True
            ws.close()
        except Exception as e:
            status["hud"]["error"] = str(e)[:160]
        return status
    if name == "jarvis_ask":
        question = str(args.get("question") or "").strip()
        if not question or len(question) > 4000:
            raise ValueError("Invalid question length")
        return http("/api/chat", {"provider": "jarvis",
                    "messages": [{"role": "user", "content": question}]}, timeout=95)
    if name == "jarvis_command":
        command = str(args.get("command") or "").strip()
        if not command or len(command) > 400:
            raise ValueError("Invalid command length")
        if any(word in command.casefold() for word in SENSITIVE) and args.get("confirmed") is not True:
            return {"queued": False, "requires_confirmation": True}
        ws = ws_connect()
        try:
            ws.send(json.dumps({"source": "HUD", "type": "COMMAND", "command": command}))
        finally:
            ws.close()
        return {"queued": True, "executed": "unknown", "command": command}
    raise ValueError("Unknown tool")

def reply(ident, result=None, error=None):
    data = {"jsonrpc": "2.0", "id": ident}
    data["error" if error else "result"] = error if error else result
    print(json.dumps(data, ensure_ascii=False), flush=True)

def process(msg):
    ident = msg.get("id")
    if ident is None:
        return
    method = msg.get("method")
    if method == "initialize":
        reply(ident, {"protocolVersion": (msg.get("params") or {}).get("protocolVersion") or "2024-11-05",
                      "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "jarvis-local", "version": "0.1.0"}})
    elif method == "ping":
        reply(ident, {})
    elif method == "tools/list":
        reply(ident, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params") or {}
        try:
            args = params.get("arguments") or {}
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
            output = call(str(params.get("name") or ""), args)
            reply(ident, {"content": [{"type": "text", "text": json.dumps(output)}],
                          "isError": False})
        except Exception as e:
            reply(ident, {"content": [{"type": "text", "text": str(e)[:300]}],
                          "isError": True})
    else:
        reply(ident, error={"code": -32601, "message": "Method not found"})

if __name__ == "__main__":
    for line in sys.stdin:
        try:
            msg = json.loads(line)
            if isinstance(msg, dict):
                process(msg)
        except Exception as e:
            print("[jarvis-local] malformed input: " + type(e).__name__, file=sys.stderr)
