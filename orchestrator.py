# JARVIS UNIFIED ORCHESTRATOR V1
# Thin routing layer — existing agents remain untouched.

def route(command, brain_router):
    text = str(command or "").strip()
    if not text:
        return {"action": "chat", "response": ""}

    from computer_tasks import parse_command
    task = parse_command(text)
    if task is not None:
        return task

    # Existing deterministic/action brain remains the source of truth.
    return brain_router(text)
