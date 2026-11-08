# JARVIS / TAHRUN

A Windows-oriented voice assistant and dashboard project. The repository contains the Python assistant runtime, the React HUD, and a separate Chat Mode workspace.

## Project layout

- `Tahrun.py` is the desktop assistant entry point. Supporting Python modules provide voice, memory, browser, screen, messaging, music, image, and computer-control features.
- `JARVIS_HUD_V2/` contains the React/Vite HUD, its source components, and the small static assets used by the avatar, music view, and PWA.
- `JARVIS_CHAT_WORKSPACE/` contains a separate React chat interface and a local Python gateway. This workspace is not integrated into the legacy desktop runtime.

## Requirements

- Windows 10 or later for desktop automation and audio features.
- Python 3.10 or later.
- Node.js and npm for either frontend.
- Ollama is optional for local model responses. Some provider integrations require credentials supplied through environment variables, such as `GROQ_API_KEY`, `CARTESIA_API_KEY`, `POLLINATIONS_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`.

## Python assistant

From the repository root, create an environment and install the Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the assistant with:

```powershell
python .\Tahrun.py
```

Browser automation features may also need the Playwright Chromium browser installed with `python -m playwright install chromium`. OpenVINO GenAI is an optional, separate install for compatible local model setups.

## React HUD

```powershell
cd .\JARVIS_HUD_V2
npm ci
npm run dev
```

## Chat workspace

In a separate terminal, start the interface:

```powershell
cd .\JARVIS_CHAT_WORKSPACE
npm ci
npm run dev
```

To start its local gateway, set the desired provider key in the terminal environment, then run `python .\backend\server.py` from `JARVIS_CHAT_WORKSPACE`. Supported providers are OpenAI, Anthropic, and Gemini. The gateway uses the repository's root `brain.py` for the local JARVIS path.

## Credential and data handling

Set credentials in the local process or operating-system environment. Do not add API keys, passwords, tokens, `.env` files, session profiles, memory stores, logs, or generated output to Git. The repository ignore rules exclude these local files.

