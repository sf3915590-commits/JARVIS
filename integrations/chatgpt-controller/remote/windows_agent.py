"""Outbound-only Windows connector. Uses existing JARVIS loopback services."""
import json, os, time, urllib.request
RELAY=os.environ["JARVIS_RELAY_URL"].rstrip("/")
TOKEN=os.environ["JARVIS_AGENT_TOKEN"]
if not RELAY.startswith("https://") and not RELAY.startswith("http://127.0.0.1:"):
    raise SystemExit("Relay must use HTTPS (except local development)")
LOCAL="http://127.0.0.1:8766"
def req(url,token,body=None):
    data=json.dumps(body).encode() if body is not None else None
    headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"}
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers),timeout=30) as r:
        return json.loads(r.read(65536))
def execute(task):
    name=task["name"];args=task["arguments"]
    if name=="jarvis_ask":
        return req_local({"provider":"jarvis","messages":[{"role":"user","content":args["question"]}]})
    if name=="jarvis_command":
        # Remote commands intentionally disabled until an on-device consent UI exists.
        return {"queued":False,"error":"Remote commands require an on-device approval interface (not implemented)"}
    return {"error":"unsupported task"}
def req_local(payload):
    data=json.dumps(payload).encode()
    with urllib.request.urlopen(urllib.request.Request(LOCAL+"/api/chat",data=data,headers={"Content-Type":"application/json"}),timeout=95) as r:
        return json.loads(r.read(65536))
if __name__=="__main__":
    while True:
        try:
            task=req(RELAY+"/agent/next",TOKEN).get("task")
            if task:
                try: result=execute(task)
                except Exception as e: result={"error":type(e).__name__}
                req(RELAY+"/agent/result",TOKEN,{"id":task["id"],"result":result})
        except Exception as e:
            print("Relay unavailable:",type(e).__name__,flush=True)
        time.sleep(2)
