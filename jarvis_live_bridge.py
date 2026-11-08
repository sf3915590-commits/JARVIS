"""Small compatibility wrapper for the active JARVIS dashboard runtime."""

try:
    from jarvis_dashboard_runtime import publish as _runtime_publish
except Exception:
    _runtime_publish = None


def send(event_type, **data):
    if _runtime_publish is None:
        return False
    try:
        _runtime_publish(str(event_type), **data)
        return True
    except Exception:
        return False


def safe_state(value):
    try:
        return send("STATE", state=str(value).upper())
    except Exception:
        return False


def safe_message(value):
    try:
        return send("MESSAGE", message=str(value))
    except Exception:
        return False


def safe_activity(value):
    try:
        return send("ACTIVITY", text=str(value))
    except Exception:
        return False


def safe_command(value):
    try:
        return send("COMMAND", text=str(value))
    except Exception:
        return False


def safe_executing(action, target=""):
    try:
        return send("EXECUTING", action=str(action), target=str(target or ""))
    except Exception:
        return False


def safe_result(action, ok=True, message=""):
    try:
        return send("RESULT", action=str(action), ok=bool(ok), message=str(message))
    except Exception:
        return False


def safe_telemetry(cpu, ram, battery=None, network="ONLINE"):
    try:
        return send(
            "TELEMETRY",
            cpu=float(cpu),
            ram=float(ram),
            battery=None if battery is None else float(battery),
            network=str(network),
        )
    except Exception:
        return False


def diagnostic(key, state, detail=""):
    status = {"key": str(key), "state": str(state)}
    if detail:
        status["detail"] = str(detail)
    try:
        return send("DIAGNOSTIC", status=status)
    except Exception:
        return False
