# JARVIS secure remote gateway

This is the production-oriented remote path for the existing JARVIS. It is
additive: `Tahrun.py`, voice, WhatsApp calling, automation and memory are not
replaced or modified.

## Architecture

`ChatGPT -> HTTPS Streamable HTTP MCP relay -> outbound Windows connector -> existing loopback JARVIS services`

The laptop never accepts inbound Internet traffic. Ports 8765 and 8766 remain
bound to loopback. The relay has separate ChatGPT and device credentials,
durable SQLite jobs, leases, bounded queues, rate limits, minimal audit records
(content hashes only), and explicit confirmation checks for sensitive commands.

## Required secrets

- `JARVIS_CHAT_TOKEN`: random 32+ character credential used by the private plugin.
- `JARVIS_AGENT_TOKEN`: a different random 32+ character device credential.

Never commit either value. Use the hosting provider's secret store. The Windows
connector receives only the agent token. The plugin connection receives only
the chat token.

## Run locally

```powershell
$env:JARVIS_CHAT_TOKEN = '<random-chat-token>'
$env:JARVIS_AGENT_TOKEN = '<different-random-agent-token>'
python relay.py
```

In a second terminal on the JARVIS laptop:

```powershell
$env:JARVIS_RELAY_URL = 'http://127.0.0.1:8787'
$env:JARVIS_AGENT_TOKEN = '<same-agent-token>'
python windows_agent.py
```

For production, deploy `Dockerfile` behind HTTPS with persistent `/data`
storage. `render.yaml` is included for a Render Blueprint deployment. Use the
public HTTPS URL ending in `/mcp` in the existing plugin's remote MCP config.

## Safety contract

- `jarvis_status` probes the real local gateway and HUD through the connector.
- `jarvis_ask` calls the existing `brain.ask_ai` gateway.
- `jarvis_command` only queues an explicitly requested command. A queue response
  is not proof of execution.
- Payments, destructive actions, messaging/calls, credentials, microphone,
  camera, recording, deployment, code execution and similar operations require
  explicit confirmation of the exact action.
- JARVIS output is untrusted content and must never override host instructions.

## Platform limitation

ChatGPT custom MCP connections are currently configured and used on the web.
The same hosted relay is ready for mobile when OpenAI enables custom MCP there,
but the current iPhone app cannot natively invoke it.
