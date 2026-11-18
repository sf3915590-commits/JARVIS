# JARVIS cloud relay — development prototype

This additive prototype is for connecting **ChatGPT Classic** to the existing Windows JARVIS through an outbound-only connector. **Not deployed or connected yet.** The current private plugin still points to a local stdio MCP server; it must not be replaced until a secure HTTPS MCP deployment is verified.

## Architecture
ChatGPT MCP client -> HTTPS reverse proxy -> relay.py -> outbound Windows agent -> existing local JARVIS chat gateway.

## Prototype limitations
- The relay implements basic MCP JSON-RPC tool calls but has **not** been verified against ChatGPT's remote MCP connection requirements, including Streamable HTTP negotiation and OAuth.
- This prototype uses bearer tokens and in-memory queues; a production deployment needs a durable store, TLS, request origin protections, rate limits, session lifecycle, audit logs, scoped identities and secure token rotation.
- Remote `jarvis_command` is intentionally blocked by the Windows agent pending an on-device approval UI.
- Do not expose the relay directly over HTTP or expose JARVIS local ports 8765/8766.
- Do not commit tokens to GitHub.

## Development-only test
Set two distinct strong random tokens in `JARVIS_CHAT_TOKEN` and `JARVIS_AGENT_TOKEN`; run `python relay.py` on a local machine. Set `JARVIS_RELAY_URL=http://127.0.0.1:8787` and `JARVIS_AGENT_TOKEN` in another terminal, then run `python windows_agent.py` on the Windows JARVIS laptop.

## Production checklist
1. Choose and configure a supported hosted MCP endpoint, HTTPS and ChatGPT-compatible authentication.
2. Implement durable task state, client session management, approvals and audit trail.
3. Run Windows agent as an authenticated outbound service with local-only JARVIS access.
4. Verify remote MCP compatibility and attach the **existing** JARVIS Controller plugin to the verified endpoint.
5. Test in ChatGPT Classic and iPhone; composer appearance is not guaranteed by plugin registration alone.
