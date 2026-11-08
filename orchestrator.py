# JARVIS UNIFIED ORCHESTRATOR V1
# Thin routing layer — existing agents remain untouched.

def route(command, brain_router):
    text = str(command or "").strip()
    if not text:
        return {"action": "chat", "response": ""}

    # Existing deterministic/action brain remains the source of truth.
    return brain_router(text)
