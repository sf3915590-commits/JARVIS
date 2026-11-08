# JARVIS Workspace V1 — UI build scaffold

This is the first runnable implementation of the approved dark, premium JARVIS Chat Mode interface. It is a separate integration-ready workspace, not a replacement for the existing JARVIS Core or Music Core.

## Included now

- Three-mode shell: OS Mode / Chat Mode / Music Mode.
- Chat Mode interface with New Chat, local chat history, Projects, Library, Files, Schedules, Plugins, AI Models and Settings views.
- Local browser persistence for chat history.
- File selection and attachment display. This version stores attachment metadata and local preview references; it does **not** yet send binary file contents to AI providers.
- Browser speech input (where supported) and speech synthesis for received assistant replies.
- Mute / Unmute controls for the Chat Mode browser voice features.
- Activity log that records actual UI actions and clearly labels unavailable integrations.
- Local Python API gateway supporting OpenAI Chat Completions, Anthropic Messages and Gemini `generateContent` using environment variables.
- API keys stay in the Python backend, not in browser code.

## Not yet integrated (existing project source is required)

- The original primary JARVIS Core JSX/dashboard and its real computer-control bridge.
- The existing Music Core JSX/player.
- Windows application launch, browser/terminal/file automation, WhatsApp/Instagram connectors, wake-word background service, long-term memory/vector search, persistent scheduler and autonomous coding-agent file access.
- True token-by-token streamed responses and synchronized streaming TTS.
- Actual binary attachment upload/vision/document parsing.

The OS Mode and Music Mode buttons currently open clearly labelled integration slots. They do not pretend to operate the old modules until those exact modules are connected.

## Run on Windows

Requirements: Node.js 20+ and Python 3.10+.

### 1) Start the frontend

Open PowerShell in this folder:

```powershell
npm install
npm run dev
```

Open the local address shown by Vite (normally `http://127.0.0.1:5173`).

### 2) Configure the local AI gateway

Set the selected provider key in the terminal environment before starting the gateway. Supported variables are `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY`.

Keep credentials outside this repository. No `.env` file is included.

Start the gateway:

```powershell
python backend/server.py
```

In JARVIS Chat Mode, open **Settings**, keep the endpoint at `http://127.0.0.1:8765/api/chat`, choose your provider/model, then click **Test backend connection**.

Suggested model identifiers are provider-specific and can change. Use the exact model name available to your API account.

## Security and honest status

- The local gateway binds to `127.0.0.1` by default; it is not exposed to the network.
- Provider keys are read from the server process environment and are not sent to the frontend.
- The UI does not execute shell commands or edit project files.
- A visible status such as “Bridge pending” means that integration is genuinely not connected.
- Do not add unrestricted computer control. The eventual file/code agent should use explicit permission scopes and confirmation before consequential writes or destructive actions.

## Next integration step

Provide the existing JARVIS source project ZIP (excluding `.env`, API keys, credentials, certificates, databases, large model files, `node_modules`, `.venv`, caches and build output). Then merge this Chat Mode into the existing app while preserving the original Core JSX and Music Core JSX.


