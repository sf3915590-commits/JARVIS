import asyncio
import json

HOST = "127.0.0.1"
PORT = 8765
_clients = set()
_loop = None

try:
    import websockets
except Exception:
    websockets = None

async def _handler(ws):
    _clients.add(ws)
    try:
        async for _ in ws:
            pass
    except Exception:
        pass
    finally:
        _clients.discard(ws)

async def _broadcast(payload):
    if not _clients:
        return
    raw = json.dumps(payload, ensure_ascii=False)
    for ws in list(_clients):
        try:
            await ws.send(raw)
        except Exception:
            _clients.discard(ws)

def broadcast(payload):
    if _loop is None:
        return False
    try:
        asyncio.run_coroutine_threadsafe(_broadcast(payload), _loop)
        return True
    except Exception:
        return False

async def _main():
    global _loop
    _loop = asyncio.get_running_loop()
    if websockets is None:
        print("[JARVIS HUD] Package 'websockets' is missing.", flush=True)
        return
    await websockets.serve(_handler, HOST, PORT)
    print(f"[JARVIS HUD] Bridge listening on ws://{HOST}:{PORT}", flush=True)
    await asyncio.Future()

def run():
    asyncio.run(_main())

if __name__ == "__main__":
    run()
