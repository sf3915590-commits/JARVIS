# JARVIS Controller V1 — Local MCP Plugin

This is an additive integration for the existing JARVIS project. It does **not** replace `Tahrun.py`, `brain.py`, its voice engine, or HUD.

## Features
- `jarvis_status`: checks `http://127.0.0.1:8766/api/health` and the HUD WebSocket `ws://127.0.0.1:8765`.
- `jarvis_ask`: sends a question through the existing local gateway to `brain.ask_ai`.
- `jarvis_command`: forwards a specifically requested command to the HUD command queue; it does not confirm execution. Potentially sensitive operations require explicit confirmation.

## Setup
1. Ensure the existing JARVIS dashboard and chat workspace gateway are running.
2. Install the JARVIS project's `websocket-client` Python dependency.
3. Register the adjacent `mcp.json` with a compatible **local** MCP host. It runs `python server/bridge.py` as a stdio MCP server.
4. Smoke-test with the `jarvis_status` tool.

## Remote access
This V1 is **local only**. Registering a private plugin does not deploy a server, and ChatGPT on iPhone cannot connect to this Windows stdio process. A hosted, authenticated MCP relay plus an outbound Windows agent is required for iPhone access. Do **not** port-forward or publicly expose the existing 8765/8766 services: the HUD command WebSocket currently trusts local `source: HUD` messages and is not suitable as an Internet-facing endpoint.

## Security
No keys or .env files belong in the repository or plugin archive. Use per-device authentication, short-lived scoped grants, confirmation for high-risk actions, and logs when building the remote relay.
