# JARVIS WhatsApp Phone Control (experimental)

This is the **existing JARVIS desktop assistant** extended for two-way
WhatsApp Web voice calls. It does not run a second WhatsApp account or
start a new browser login.

## What works in the call controller

- Dial only the verified exact **boss** contact, in the existing Edge CDP 9222 WhatsApp profile.
- Greet only after a verified advancing call timer.
- Keep listening after every answer without requiring another wake word.
- Play a short, varying pre-rendered acknowledgement immediately after an
  utterance ends while transcription runs in parallel.
- Open supported installed Windows apps and allowed sites.
- Read exact local computer time/date and fetch fresh online search headlines.
- End the call when the phone says **"Jarvis, cut the call"**, **"hang up"**,
  **"call band karo"**, or **"end this call"**.

### Example commands

- "Jarvis, open Chrome" / "Chrome kholo" / "Could you open VS Code?"
- "Open notepad" / "Open calculator" / "Open WhatsApp"
- "Open YouTube" / "Open Instagram" / "Open downloads folder"
- "What is the exact time now?" / "Aaj ki date batao"
- "Latest news" / "Search the web for space launches"
- "Jarvis, cut the call"

These are **verified, bounded actions**, not model-invented claims. Ordinary
conversation still goes to the configured Ollama model. If live search fails,
JARVIS says it cannot verify the news rather than inventing headlines.

## Audio setup from the user's verified call test

| WhatsApp device | Selection |
| --- | --- |
| Microphone | CABLE Output (VB-Audio Virtual Cable) |
| Speaker | CABLE Input (VB-Audio Virtual Cable) |
| Python outgoing audio | CABLE Input (VB-Audio Virtual Cable) |
| Incoming recognition | CABLE Input (VB-Audio Virtual Cable) [Loopback] |

Two-way conversational turns work in this sequential capture/playback setup.
It does **not** yet support true simultaneous full-duplex speech or reliable
barge-in, because the same virtual cable mixes in- and outbound signals.
Using separate virtual cable routes can improve echo isolation later.

## Launch for local Windows testing

From the original Tahrun directory, with test worktree in a sibling folder:

```powershell
git -c maintenance.auto=false -C ../Tahrun-Call-Sync pull --ff-only
python ../Tahrun-Call-Sync/jarvis_whatsapp_ai_call.py --confirm-distinct-accounts
```

The command actually dials **boss**. Check that Edge 9222 is running and both
WhatsApp accounts are different before testing.

The optional `GROQ_API_KEY` environment variable enables Whisper Large V3
phone transcription (with local Whisper fallback). Voice input is sent to
Groq when the key is configured. Set `JARVIS_CALL_STT=local` to keep STT local.
Cartesia TTS uses the existing primary/fallback keys, not repo secrets.

## Trust and safety

The caller can control **allowed** non-destructive desktop actions only.
Sending messages, modifying/deleting arbitrary files, running shell commands,
payment/transfer, and credential disclosure are **not** exposed over the
phone simply because someone speaks the wake word. An outgoing call to a
contact is not cryptographic speaker identity verification.

The hangup fallback is bounded to a previously connected, verified boss call.
If WhatsApp changes its controls and hangup cannot be confirmed, the assistant
will say so in the logs; manually end the phone call.

## Testing and known limits

```powershell
python -m unittest discover -s ../Tahrun-Call-Sync -p "test_jarvis*call*.py" -v
```

GitHub Actions checks Linux-isolated parsers and fake-device flows. Only an
actual Windows + Edge + WhatsApp call can verify desktop launching, Groq
connectivity, the device paths, audio latency, and reliable call hangup.
This feature is intentionally maintained on a draft PR until those pass.
