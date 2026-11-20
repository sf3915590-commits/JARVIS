# Continuous JARVIS WhatsApp call conversations (integration contract)

This change adds `jarvis_call_conversation.py` as a **standalone session loop**
with no desktop/global-audio changes. It is deliberately not enabled in
`Tahrun.py` yet: the new `[AI CALL] DIALING / CONNECTED / SPEAKING / LISTENING`
controller in the current Windows logs is **not present on the remote GitHub
main branch**. The old `jarvis_whatsapp_controls.perform_call()` only clicks
the call button and does not verify the receiver's answer or provide remote
audio/STT callbacks. Starting an AI session from that function would be unsafe
and could create a second competing call controller.

## Connect the actual Windows AI-call controller

On `CONNECTED` **only after receiver answer is verified**:

```python
from jarvis_call_conversation import ContinuousCallSession, CallConfig

session = ContinuousCallSession(
    is_connected=call.is_connected,              # existing verified state
    listen_utterance=call.listen_remote_utterance,# VAD -> STT, never wake mic
    reply_to=call.brain_and_action_reply,         # existing router + authorizations
    speak_to_call=call.speak_to_cable,            # blocking Cartesia playback
    greeting=lambda: call.scheduled_greeting
        or "Hello Boss! Kya haal chaal? Batao kya chal raha hai?",
    config=CallConfig(filler_after_seconds=1.35),
    log_event=lambda event, payload: print("[AI CALL]", event, payload),
)
session.run()  # run in current call worker; controller still handles hangup
```

The four `call.*` methods above are **illustrative names**, not existing
methods in the GitHub repository. Adapt them to the actual local controller
after it is synced. For requested desktop actions such as "open Chrome",
`brain_and_action_reply` should call the existing command router and
execute only authorized actions, with confirmations for security-sensitive
requests. It should return a concise spoken result. Ordinary questions go
through the existing LLM, with short conversation history passed in.

### Audio and response timing

- Preserve **the user's verified working WhatsApp device choices**:
  microphone `CABLE Output (VB-Audio Virtual Cable)` and speaker
  `CABLE Input (VB-Audio Virtual Cable)`. Do not silently reset the dropdown.
- The TTS callback plays to the virtual cable feed; the listening callback
  must capture the **remote voice**, not JARVIS's own outbound greeting.
  Measure remote speech levels to ensure an accidental echo loop is absent.
- VAD must end an utterance promptly (e.g. 350-600ms of quiet); no
  wake word inside an active call.
- The target is to **start speaking about 2-3 seconds after the caller stops**.
  No artificial delay is inserted. A single natural acknowledgement
  starts at 1.35s if the brain has not responded. Pre-cache filler audio
  through the existing TTS/cache path so the filler itself does not take
  seconds to synthesize. Phone-audible latency depends on STT, LLM, TTS,
  network, and WhatsApp and cannot be guaranteed by this module.
- Call greeting runs once, after `CONNECTED`, never at `RINGING`.
- `LISTENING` repeats until hangup. Silence or an ordinary receive timeout
  does not end the call. Real stream failures are logged and escalated.
- This loop intentionally does not own the dialer, scheduler, hangup button,
  Windows audio routing or WhatsApp login/session.

### Test

```sh
python -m unittest -v test_jarvis_call_conversation.py
```

The tests simulate multiple turns, delayed thoughts/fillers, silence,
connection checks and failures without calling real WhatsApp, Groq or Cartesia.

### Other errors observed in Windows logs

The logs also show port `127.0.0.1:8765` already bound, duplicate call
controller ownership and occasional `TimeoutError`. Before live testing,
ensure just **one** JARVIS call-controller instance is running; do not kill
unrelated desktop tasks. The actual call controller also needs an explicit
call-hangup/disconnect detector, which cannot be fixed in the older GitHub
`perform_call()` implementation without the newer local source.
