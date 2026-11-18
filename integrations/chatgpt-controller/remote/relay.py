"""Prototype authenticated MCP relay. Deploy behind HTTPS; no direct inbound laptop ports."""
import json, os, secrets, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8787"))
CHAT_TOKEN = os.environ["JARVIS_CHAT_TOKEN"]
AGENT_TOKEN = os.environ["JARVIS_AGENT_TOKEN"]
if len(CHAT_TOKEN) < 32 or len(AGENT_TOKEN) < 32 or CHAT_TOKEN == AGENT_TOKEN:
    raise SystemExit("Use distinct, random 32+ character tokens")
queue, results, lock = [], {}, threading.Lock()
TOOLS = [
 {"name":"jarvis_status","description":"Check if Windows JARVIS is connected to this relay.","inputSchema":{"type":"object","properties":{}}},
 {"name":"jarvis_ask","description":"Ask the existing Windows JARVIS brain.","inputSchema":{"type":"object","properties":{"question":{"type":"string"}},"required":["question"]}},
 {"name":"jarvis_command","description":"Queue an explicitly approved command for Windows JARVIS.","inputSchema":{"type":"object","properties":{"command":{"type":"string"},"confirmed":{"type":"boolean"}},"required":["command","confirmed"]}}
]
last_seen = [0.0]
def auth(given, expected):
    return secrets.compare_digest(given, "Bearer "+expected)
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, status, obj):
        raw=json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers();self.wfile.write(raw)
    def body(self):
        size=int(self.headers.get("Content-Length","0"))
        if size < 1 or size > 16384: raise ValueError("invalid body size")
        return json.loads(self.rfile.read(size))
    def do_GET(self):
        if not auth(self.headers.get("Authorization",""),AGENT_TOKEN):
            return self.send_json(401,{"error":"unauthorized"})
        if self.path != "/agent/next":return self.send_json(404,{"error":"not found"})
        with lock:
            last_seen[0]=time.time()
            task=queue.pop(0) if queue else None
        self.send_json(200,{"task":task})
    def do_POST(self):
        agent=self.path=="/agent/result"
        if self.path not in ("/agent/result","/mcp"):
            return self.send_json(404,{"error":"not found"})
        if not auth(self.headers.get("Authorization",""),AGENT_TOKEN if agent else CHAT_TOKEN):
            return self.send_json(401,{"error":"unauthorized"})
        try: msg=self.body()
        except (ValueError,TypeError,json.JSONDecodeError):
            return self.send_json(400,{"error":"invalid JSON"})
        if agent:
            ident=msg.get("id")
            if not isinstance(ident,str):return self.send_json(400,{"error":"invalid id"})
            with lock:
                if ident not in results:return self.send_json(404,{"error":"unknown task"})
                results[ident]=msg.get("result")
                last_seen[0]=time.time()
            return self.send_json(200,{"ok":True})
        ident=msg.get("id")
        method=msg.get("method")
        if method=="initialize":
            out={"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"jarvis-relay","version":"0.1.0"}}
        elif method=="ping":out={}
        elif method=="tools/list":out={"tools":TOOLS}
        elif method=="tools/call":
            p=msg.get("params") or {};name=p.get("name");args=p.get("arguments") or {}
            if not isinstance(args,dict):return self.send_json(400,{"error":"invalid arguments"})
            if name=="jarvis_status":
                out={"content":[{"type":"text","text":json.dumps({"agent_online":time.time()-last_seen[0]<15})}]}
            elif name in ("jarvis_ask","jarvis_command"):
                key="question" if name=="jarvis_ask" else "command"
                value=args.get(key)
                if not isinstance(value,str) or not value.strip() or len(value)> (4000 if name=="jarvis_ask" else 400):
                    return self.send_json(400,{"error":"invalid input"})
                if name=="jarvis_command" and args.get("confirmed") is not True:
                    out={"content":[{"type":"text","text":"Explicit user confirmation required."}],"isError":True}
                else:
                    job=str(uuid.uuid4())
                    with lock:
                        if len(queue)>=20:return self.send_json(429,{"error":"queue full"})
                        queue.append({"id":job,"name":name,"arguments":{key:value}})
                        results[job]=None
                    deadline=time.monotonic()+25
                    while time.monotonic()<deadline:
                        with lock:answer=results.get(job)
                        if answer is not None:break
                        time.sleep(.15)
                    with lock:results.pop(job,None)
                    out={"content":[{"type":"text","text":json.dumps(answer if answer is not None else {"error":"agent timeout"})}],"isError":answer is None}
            else:return self.send_json(400,{"error":"unknown tool"})
        else:return self.send_json(400,{"error":"unsupported MCP method"})
        self.send_json(200,{"jsonrpc":"2.0","id":ident,"result":out})
if __name__=="__main__":
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
