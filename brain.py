from pathlib import Path
import re
import time as _jarvis_perf_time
import ollama
import os
import json
import urllib.request
import urllib.error
import time
try:
    import psutil
except ImportError:
    psutil = None
from security_policy import explicit_shutdown_command, parse_delete_request
from memory_manager import (
    load_memory,
    add_fact,
    add_conversation,

    clear_memory,
)

MODEL = "qwen3:4b-instruct"

_selected_model = None
_model_lock = __import__("threading").Lock()


def _check_ram_throttle():
    """Lightweight resource-throttle guard for RAM usage above 90%."""
    if psutil is not None:
        try:
            mem = psutil.virtual_memory()
            if mem.percent > 90.0:
                print(f"[JARVIS RESOURCE WARNING] High RAM usage detected: {mem.percent}% (Available: {mem.available / (1024**2):.1f} MB). Throttling inference...", flush=True)
                time.sleep(0.5)
        except Exception:
            pass

# =====================================================
# USER ROUTINE ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â persistent + query-only
# =====================================================

ROUTINE_FACT = (
    "User routine: first get up and take care of himself; "
    "then do some study; then have some scrolling/free time."
)

USER_ROUTINE = [
    "Sabse pehle uth kar apna khayal rakhna.",
    "Uske baad thodi padhai-likhai.",
    "Uske baad thodi scrolling / free time.",
]


def routine_response():
    return (
        "Boss, tumhara routine: sabse pehle uth kar apna khayal rakhna, "
        "phir thodi padhai-likhai, aur uske baad thodi scrolling ya free time."
    )


def ensure_routine_saved():
    """Persist the default routine once so it survives restarts."""
    try:
        memory = load_memory()
        facts = memory.get("facts", [])
        if not any("User routine:" in str(fact) for fact in facts):
            add_fact(ROUTINE_FACT)
    except Exception as error:
        print(f"Memory init warning: {error}", flush=True)


def is_routine_query(command):
    c = norm(command)
    if "routine" not in c and "daily routine" not in c:
        return False
    query_words = [
        "what", "what's", "tell", "show", "batao", "kya hai",
        "mera", "meri", "my", "daily", "routine"
    ]
    return any(word in c for word in query_words)


def is_routine_save_request(command):
    c = norm(command)
    return (
        ("routine" in c or "daily routine" in c)
        and any(word in c for word in [
            "remember", "save", "store", "yaad", "save kar",
            "yaad rakho", "yaad rakhna"
        ])
    )


def get_memory_context():
    memory = load_memory()

    facts = memory.get("facts", [])
    conversations = memory.get("conversations", [])

    context_parts = []

    if facts:
        context_parts.append(
            "IMPORTANT FACTS ABOUT THE USER:\n"
            + "\n".join(f"- {fact}" for fact in facts[-20:])
        )

    if conversations:
        recent = conversations[-5:]

        conversation_text = "\n".join(
            f"User: {item.get('user', '')}\n"
            f"Jarvis: {item.get('jarvis', '')}"
            for item in recent
        )

        context_parts.append(
            "RECENT CONVERSATION:\n" + conversation_text
        )

    if not context_parts:
        return "No saved memory yet."

    return "\n\n".join(context_parts)


def _get_local_model():
    global _selected_model
    if _selected_model:
        return _selected_model

    with _model_lock:
        if _selected_model:
            return _selected_model
        try:
            models = ollama.list().get("models", [])
            installed = {
                str(item.get("model", item.get("name", ""))).lower()
                for item in models
            }
            for candidate in MODEL_CANDIDATES:
                if candidate.lower() in installed:
                    _selected_model = candidate
                    break
        except Exception:
            pass

        _selected_model = _selected_model or MODEL
        return _selected_model


# =====================================================
# JARVIS REPLY LANGUAGE
# Default = Roman Urdu / Hinglish
# Explicit user request changes the language.
# =====================================================

REPLY_LANGUAGE = "roman_urdu"


def set_reply_language(command):
    global REPLY_LANGUAGE

    c = str(command or "").lower().strip()

    reset_phrases = [
        "reset language",
        "normal language",
        "default language",
        "language reset",
        "normal reply",
        "roman urdu",
        "roman urdu mein reply",
        "roman urdu me reply",
        "reply in roman urdu",
    ]

    if any(x in c for x in reset_phrases):
        REPLY_LANGUAGE = "roman_urdu"
        return REPLY_LANGUAGE

    language_map = {
        "hindi": [
            "reply in hindi",
            "reply me in hindi",
            "hindi mein reply",
            "hindi me reply",
            "hindi mein jawab",
            "hindi me jawab",
        ],
        "english": [
            "reply in english",
            "reply me in english",
            "english mein reply",
            "english me reply",
            "english mein jawab",
            "english me jawab",
        ],
        "urdu": [
            "reply in urdu",
            "reply me in urdu",
            "urdu mein reply",
            "urdu me reply",
            "urdu mein jawab",
            "urdu me jawab",
        ],
        "bengali": [
            "reply in bengali",
            "reply me in bengali",
            "bengali mein reply",
            "bengali me reply",
        ],
        "telugu": [
            "reply in telugu",
            "reply me in telugu",
            "telugu mein reply",
            "telugu me reply",
        ],
        "marathi": [
            "reply in marathi",
            "reply me in marathi",
            "marathi mein reply",
            "marathi me reply",
        ],
        "tamil": [
            "reply in tamil",
            "reply me in tamil",
            "tamil mein reply",
            "tamil me reply",
        ],
        "gujarati": [
            "reply in gujarati",
            "reply me in gujarati",
            "gujarati mein reply",
            "gujarati me reply",
        ],
        "kannada": [
            "reply in kannada",
            "reply me in kannada",
            "kannada mein reply",
            "kannada me reply",
        ],
        "malayalam": [
            "reply in malayalam",
            "reply me in malayalam",
            "malayalam mein reply",
            "malayalam me reply",
        ],
        "punjabi": [
            "reply in punjabi",
            "reply me in punjabi",
            "punjabi mein reply",
            "punjabi me reply",
        ],
        "odia": [
            "reply in odia",
            "reply me in odia",
            "odia mein reply",
            "odia me reply",
        ],
        "assamese": [
            "reply in assamese",
            "reply me in assamese",
            "assamese mein reply",
            "assamese me reply",
        ],
    }

    for language, phrases in language_map.items():
        if any(phrase in c for phrase in phrases):
            REPLY_LANGUAGE = language
            return REPLY_LANGUAGE

    return None


def get_language_instruction():
    instructions = {
        "roman_urdu": (
            "Reply ONLY in natural Roman Urdu/Hinglish. "
            "Use Latin/English letters. Do not use Devanagari or Urdu script. "
            "This is the default JARVIS reply language."
        ),
        "hindi": "Reply ONLY in natural Hindi using Devanagari script.",
        "english": "Reply ONLY in natural English.",
        "urdu": "Reply ONLY in natural Urdu using Urdu script.",
        "bengali": "Reply ONLY in natural Bengali using Bengali script.",
        "telugu": "Reply ONLY in natural Telugu using Telugu script.",
        "marathi": "Reply ONLY in natural Marathi using Devanagari script.",
        "tamil": "Reply ONLY in natural Tamil using Tamil script.",
        "gujarati": "Reply ONLY in natural Gujarati using Gujarati script.",
        "kannada": "Reply ONLY in natural Kannada using Kannada script.",
        "malayalam": "Reply ONLY in natural Malayalam using Malayalam script.",
        "punjabi": "Reply ONLY in natural Punjabi using Gurmukhi script.",
        "odia": "Reply ONLY in natural Odia using Odia script.",
        "assamese": "Reply ONLY in natural Assamese using Assamese/Bengali script.",
    }

    return instructions.get(
        REPLY_LANGUAGE,
        instructions["roman_urdu"]
    )



# ============================================================
# FAST LOCAL BRAIN Ã¢â‚¬â€ OpenVINO / Intel GPU
# Existing Ollama remains the fallback.
# ============================================================
import threading as _ov_threading
from types import SimpleNamespace as _OVSimpleNamespace

_OV_MODEL_DIR = Path(__file__).resolve().parent / "qwen3-4b-openvino"
_OV_PIPELINE = None
_OV_LOAD_ERROR = None
_OV_READY = _ov_threading.Event()

def _load_openvino_brain():
    global _OV_PIPELINE, _OV_LOAD_ERROR
    try:
        import openvino_genai as _ov_genai
        _OV_PIPELINE = _ov_genai.LLMPipeline(str(_OV_MODEL_DIR), "GPU")
        # Warm up generation in the existing background loader.
        try:
            _OV_PIPELINE.generate(
                "USER:\nReply with exactly: READY\n\nASSISTANT:\n",
                max_new_tokens=4,
                temperature=0.0,
            )
            print("FAST BRAIN: OpenVINO GPU warm-up complete", flush=True)
        except Exception as _warm_error:
            print(f"FAST BRAIN: OpenVINO warm-up skipped: {_warm_error}", flush=True)
        _OV_READY.set()
        print("FAST BRAIN: OpenVINO Intel GPU READY", flush=True)
    except Exception as _error:
        _OV_LOAD_ERROR = _error
        _OV_READY.set()
        print(f"FAST BRAIN: OpenVINO unavailable, Ollama fallback: {_error}", flush=True)

def _start_openvino_brain():
    if _OV_PIPELINE is None and _OV_LOAD_ERROR is None:
        _ov_threading.Thread(target=_load_openvino_brain, daemon=True, name="OpenVINO-Brain").start()

_start_openvino_brain()

# JARVIS_PERFORMANCE_PATCH_V1
# OpenVINO adapter: correct decoded-result extraction, Qwen3 no-think mode,
# and precise provider/wait/generation timing. Ollama remains the fallback.
def _clean_openvino_output(_result):
    _text = ""
    try:
        if isinstance(_result, str):
            _text = _result
        elif isinstance(_result, dict):
            _text = str(
                _result.get("text")
                or _result.get("generated_text")
                or _result.get("content")
                or ""
            )
        else:
            _texts = getattr(_result, "texts", None)
            if _texts is not None:
                _texts = list(_texts)
                _text = str(_texts[0]) if _texts else ""
            else:
                _text = str(_result or "")
    except Exception as _extract_error:
        print(f"JARVIS PERF: OpenVINO result extraction error: {_extract_error}", flush=True)
        _text = ""

    _text = re.sub(r"<think>.*?</think>", "", _text, flags=re.S | re.I)
    _text = re.sub(r"<think>.*", "", _text, flags=re.S | re.I)
    return _text.strip()


def _fast_chat(*, model=None, messages=None, options=None, **_kwargs):
    global _OV_PIPELINE

    _call_started = _jarvis_perf_time.perf_counter()
    _wait_seconds = 0.0
    _fallback_reason = ""

    # Prepare a private copy so the Qwen3 no-thinking switch reaches both
    # the OpenVINO primary path and the preserved Ollama fallback.
    _chat_messages = []
    for _message in (messages or []):
        _copy = dict(_message)
        if str(_copy.get("role", "")).lower() == "system":
            _system_content = str(_copy.get("content", ""))
            if "/no_think" not in _system_content:
                _copy["content"] = _system_content.rstrip() + "\n/no_think"
        _chat_messages.append(_copy)

    if _OV_PIPELINE is None and _OV_LOAD_ERROR is None:
        _wait_started = _jarvis_perf_time.perf_counter()
        _OV_READY.wait(timeout=45)
        _wait_seconds = _jarvis_perf_time.perf_counter() - _wait_started

    if _OV_PIPELINE is not None:
        try:
            _parts = []
            for _m in _chat_messages:
                _role = str(_m.get("role", "user")).upper()
                _content = str(_m.get("content", ""))
                _parts.append(f"{_role}:\n{_content}")
            _prompt = "\n\n".join(_parts) + "\n\nASSISTANT:\n"

            _opts = options or {}
            _max_tokens = int(_opts.get("num_predict", 30))
            _max_tokens = max(16, min(_max_tokens, 120))
            _temperature = float(_opts.get("temperature", 0.2))

            _generation_started = _jarvis_perf_time.perf_counter()
            _out = _OV_PIPELINE.generate(
                _prompt,
                max_new_tokens=_max_tokens,
                temperature=_temperature,
            )
            _generation_seconds = _jarvis_perf_time.perf_counter() - _generation_started
            _answer = _clean_openvino_output(_out)
            if _answer:
                _total = _jarvis_perf_time.perf_counter() - _call_started
                print(
                    "JARVIS PERF | provider=OpenVINO-GPU"
                    f" | ready_wait={_wait_seconds:.2f}s"
                    f" | generation={_generation_seconds:.2f}s"
                    f" | total={_total:.2f}s"
                    f" | prompt_chars={len(_prompt)}"
                    f" | output_chars={len(_answer)}",
                    flush=True,
                )
                return {"message": {"content": _answer}}

            _fallback_reason = "OpenVINO returned empty decoded text"
        except Exception as _error:
            _fallback_reason = f"OpenVINO exception: {_type_name(_error)}: {_error}"
            print(f"JARVIS PERF: {_fallback_reason}", flush=True)
    elif _OV_LOAD_ERROR is not None:
        _fallback_reason = f"OpenVINO loader failed: {_OV_LOAD_ERROR}"
    else:
        _fallback_reason = "OpenVINO was not ready within 45 seconds"

    import ollama as _ollama
    _ollama_started = _jarvis_perf_time.perf_counter()
    _result = _ollama.chat(model=model, messages=_chat_messages, options=options, **_kwargs)
    _ollama_seconds = _jarvis_perf_time.perf_counter() - _ollama_started
    _total = _jarvis_perf_time.perf_counter() - _call_started
    print(
        "JARVIS PERF | provider=Ollama-fallback"
        f" | reason={_fallback_reason}"
        f" | ready_wait={_wait_seconds:.2f}s"
        f" | ollama={_ollama_seconds:.2f}s"
        f" | total={_total:.2f}s",
        flush=True,
    )
    return _result


def _type_name(_value):
    return type(_value).__name__


def ask_ai(text):
       

    """JARVIS local AI response layer using Ollama/Qwen."""

    _ask_started = _jarvis_perf_time.perf_counter()

    selected_language = set_reply_language(text)

    if selected_language:
        confirmations = {
            "roman_urdu": "Theek hai Boss. Ab se main Roman Urdu/Hinglish mein reply karunga.",
            "hindi": "Theek hai Boss. Ab se main Hindi mein reply karunga.",
            "english": "Okay Boss. I will reply in English from now on.",
            "urdu": "Theek hai Boss. Ab se main Urdu mein reply karunga.",
            "bengali": "Theek hai Boss. Ab se main Bengali mein reply karunga.",
            "telugu": "Theek hai Boss. Ab se main Telugu mein reply karunga.",
            "marathi": "Theek hai Boss. Ab se main Marathi mein reply karunga.",
            "tamil": "Theek hai Boss. Ab se main Tamil mein reply karunga.",
            "gujarati": "Theek hai Boss. Ab se main Gujarati mein reply karunga.",
            "kannada": "Theek hai Boss. Ab se main Kannada mein reply karunga.",
            "malayalam": "Theek hai Boss. Ab se main Malayalam mein reply karunga.",
            "punjabi": "Theek hai Boss. Ab se main Punjabi mein reply karunga.",
            "odia": "Theek hai Boss. Ab se main Odia mein reply karunga.",
            "assamese": "Theek hai Boss. Ab se main Assamese mein reply karunga.",
        }

        return confirmations.get(
            selected_language,
            confirmations["roman_urdu"]
        )

    try:
        _memory_started = _jarvis_perf_time.perf_counter()
        memory_context = get_memory_context()
        print(f"JARVIS PERF | memory_context={_jarvis_perf_time.perf_counter() - _memory_started:.2f}s", flush=True)

        system_prompt = f"""
You are JARVIS, a polished personal desktop AI assistant.

STYLE:
- Sound calm, confident, natural and human.
- Address the user as Boss only when it feels natural; do not overuse it.
- Answer the exact question first. Do not invent intent.
- When Hindi/Urdu speech is transcribed into Devanagari or Urdu script, interpret phonetic renderings of English technical terms by context and sound. For example, "ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â¨", "ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¨", or "ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â¨" can mean "Python"; "ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸" can mean "variables". Do not treat these as literal spelling mistakes when the surrounding sentence clearly identifies the technical term.
- Follow the selected JARVIS reply language exactly.
- DEFAULT: Roman Urdu/Hinglish.
- SELECTED LANGUAGE: {get_language_instruction()}
- Do not switch languages unless the user explicitly changes the reply language.
- Keep the selected language consistent throughout the response.
- Never give robotic filler.
- Do not repeat the user's question.
- Normal replies should be 1-4 sentences and spoken-friendly.
- Do not use emojis in spoken answers.
- For simple questions, answer immediately and briefly.
- For technical questions, give the practical answer first.
- Use saved memory only when it is relevant to the current request.
- Do not introduce personal names, people, relationships, or personal details from memory unless directly relevant.
- Never volunteer a person's name just because it exists in memory.

MEMORY:
{memory_context}
"""

        r = _fast_chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            think=False,
            keep_alive="30m",
            options={
                "temperature": 0.2,
                "num_predict": 180,
                "num_ctx": 2048,
            },
        )

        _message = r.get("message", {}) if isinstance(r, dict) else getattr(r, "message", None)
        if isinstance(_message, dict):
            response = str(_message.get("content", "") or "").strip()
        else:
            response = str(getattr(_message, "content", "") or "").strip()

        if not response:
            return "Boss, ek second. Dobara bolna."

        print(f"JARVIS PERF | ask_ai_total={_jarvis_perf_time.perf_counter() - _ask_started:.2f}s", flush=True)
        return response

    except Exception as e:
        print(f"AI Brain Error: {e}")
        return "Boss, AI abhi respond nahi kar pa raha."

def norm(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def extract_youtube_query(text):
    c = norm(text)

    patterns = [
        r"(?:open|khol(?:o)?|launch)\s+youtube\s+(?:and|aur)\s+(?:play|chalao|bajao)\s+(?:the\s+)?(?:song|gaana|video)\s+(?:by|of)\s+(.+)",
        r"(?:open|khol(?:o)?|launch)\s+youtube\s+(?:and|aur)\s+(?:play|chalao|bajao)\s+(.+)",
        r"youtube\s+(?:par|pe|me|mein)\s+(?:play|chalao|bajao)\s+(?:the\s+)?(?:song|gaana|video)\s+(?:by|of)\s+(.+)",
        r"youtube\s+(?:par|pe|me|mein)\s+(?:play|chalao|bajao)\s+(.+)",
        r"youtube\s+(?:par|pe|me|mein)\s+(.+?)\s+(?:chalao|bajao|play karo|play)$",
        r"youtube\s+(?:par|pe|me|mein)?\s*search\s+(?:karo|for)?\s*(.+)",
        r"youtube\s+search\s+(.+)",
        r"(?:play|chalao|bajao)\s+(?:the\s+)?(?:song|gaana|video)\s+(.+?)\s+(?:on|in)\s+youtube$",
        r"youtube.*?(?:play|chalao|bajao)\s+(?:the\s+)?(?:song|gaana|video)\s+(.+)",
        r"youtube.*?(?:search)\s+(?:for\s+)?(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, c, re.IGNORECASE)

        if not match:
            continue

        query = match.group(1).strip()

        query = re.sub(
            r"\b(?:chalao|bajao|play karo|play|search karo)\b",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            r"^(?:song|gaana|video)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            r"^(?:by|of)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = query.strip(" ,.-")

        if query:
            return query

    return None



# =====================================================
# PERSISTENT ROUTINES / NATURAL INTENT HELPERS
# =====================================================

DEFAULT_ROUTINE = [
    "Sabse pehle uth kar apna khayal rakhna.",
    "Uske baad thodi padhai-likhai.",
    "Uske baad thodi scrolling ya free time.",
]


def _routine_facts():
    memory = load_memory()
    return [f for f in memory.get("facts", []) if "routine" in str(f).lower()]


def ensure_default_routine():
    saved = _routine_facts()
    if saved:
        return saved
    default_text = "Routine: " + " | ".join(DEFAULT_ROUTINE)
    try:
        add_fact(default_text)
    except Exception as error:
        print(f"Routine save warning: {error}")
    return [default_text]


def routine_response():
    saved = ensure_default_routine()
    return "Boss, tumhara saved routine ye hai: " + "; ".join(saved[-5:])


def save_routine_from_text(text):
    c = norm(text)
    patterns = [
        r"^(?:my|meri|mera) routine (?:is|hai|:)(.+)$",
        r"^(?:set|save) (?:my|meri|mera) routine (?:to|as) (.+)$",
        r"^(?:meri routine|my routine) (.+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, c, re.IGNORECASE)
        if m:
            value = m.group(1).strip(" .:-")
            if value:
                add_fact("Routine: " + value)
                return "Boss, routine save kar di."
    return None


def _is_shutdown_request(c):
    # Shutdown is intentionally strict: only an explicit shutdown command.
    return explicit_shutdown_command(c)


def _extract_whatsapp(text):
    c = norm(text)
    patterns = [
        r"(?:send|message|whatsapp)\s+(?:a\s+)?(?:whatsapp\s+)?(?:message\s+)?to\s+(.+?)\s+(?:saying|that|message)\s+(.+)$",
        r"(?:send\s+)?whatsapp\s+(?:message\s+)?to\s+(.+?)\s+(?:saying|that)\s+(.+)$",
        r"(?:send\s+)?(?:a\s+)?message\s+to\s+(.+?)\s+(?:saying|that)\s+(.+)$",
        r"whatsapp\s+(.+?)\s*[:,-]\s*(.+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, c, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            msg = m.group(2).strip()
            if name and msg:
                return {"action": "whatsapp_message", "target": name, "message": msg}
    return None


def _is_routine_query(c):
    return (
        ("routine" in c or "schedule" in c or "daily plan" in c)
        and any(word in c for word in ["my", "mera", "meri", "today", "aaj", "batao", "kya hai", "what is", "whats", "what's"])
    )


def understand(text):
    original = text.strip()
    c = norm(original)

    # Remove an optional wake-word prefix when the active command
    # contains "Jarvis" (e.g. "Jarvis take a screenshot").
    command = re.sub(
        r"^(?:hey\s+jarvis|jarvis)[,\s]+",
        "",
        c,
        flags=re.IGNORECASE,
    ).strip()

    # Use the cleaned wake-word-free command for every deterministic router below.
    c = command.rstrip(' .!?,;:').strip()

    # Normalize compact voice STT forms like OpenYoutube -> Open YouTube
    c = re.sub(r'(?i)\b(open|launch)(youtube|google|chrome|chatgpt|whatsapp|vscode|instagram)\b', r'\1 \2', c)


    # ============================================================
    # JARVIS PURE STUDY MODE
    # Dedicated study router. Existing normal chat remains untouched.
    # ============================================================
    study_commands = {
        "study mode",
        "study mode on",
        "pure study mode",
        "pure study mode on",
        "start study mode",
        "start pure study mode",
        "study start",
        "study mode start",
    }

    if c in study_commands:
        return {
            "action": "study_mode",
            "mode": "start",
        }

    if c in {
        "study mode off",
        "pure study mode off",
        "stop study mode",
        "exit study mode",
        "study stop",
    }:
        return {
            "action": "study_mode",
            "mode": "stop",
        }

    if c in {
        "study status",
        "study progress",
        "my study progress",
        "study revision",
        "study weak topics",
    }:
        return {
            "action": "study_mode",
            "mode": "status",
        }

    # Explicit study requests are sent through the existing local AI brain
    # with the dedicated professor instructions. No second AI is created.
    study_prefixes = (
        "study teach ",
        "study explain ",
        "study learn ",
        "study quiz ",
        "study test ",
        "study mock test ",
        "study revise ",
        "study solve ",
    )

    for prefix in study_prefixes:
        if c.startswith(prefix):
            return {
                "action": "study_request",
                "mode": prefix.strip(),
                "target": c[len(prefix):].strip(),
            }

    # ============================================================
    # SCREEN / GUI CONTROL
    # Screen-aware actions use screen_agent.py.
    # ============================================================

    if c in {
        "see my screen",
        "see the screen",
        "show my screen",
        "show me my screen",
        "look at my screen",
        "look at the screen",
        "check my screen",
        "check the screen",
        "screen dekho",
        "mera screen dekho",
        "screen dikhao",
        "screen check karo",
        "take a screenshot",
        "take screenshot",
        "screenshot lo",
        "screenshot le lo",
    }:
        return {
            "action": "screen_control",
            "mode": "screenshot",
        }

    if c in {
        "click allow",
        "allow click karo",
        "allow pe click karo",
        "allow click kar do",
        "allow ko click karo",
        "click on allow",
    }:
        return {
            "action": "screen_control",
            "mode": "click_text",
            "target": "Allow",
        }

    if c in {
        "scroll down",
        "scroll neeche",
        "neeche scroll karo",
        "scroll up",
        "scroll upar",
        "upar scroll karo",
    }:
        amount = -5 if ("down" in c or "neeche" in c) else 5
        return {
            "action": "screen_control",
            "mode": "scroll",
            "amount": amount,
        }

    # ============================================================
    # WINDOWS VOLUME FAST PATH
    # ============================================================
    if c in {
        "volume up",
        "increase volume",
        "increase the volume",
        "louder",
        "make it louder",
        "volume badhao",
        "awaz badhao",
        "awaaz badhao",
        "sound badhao",
    }:
        return {"action": "volume_up"}

    if c in {
        "volume down",
        "decrease volume",
        "decrease the volume",
        "lower volume",
        "make it quieter",
        "volume kam",
        "volume kam karo",
        "awaz kam karo",
        "awaaz kam karo",
        "sound kam karo",
    }:
        return {"action": "volume_down"}

    if c in {
        "mute",
        "mute volume",
        "mute sound",
        "sound mute",
        "volume mute",
        "awaz mute",
        "awaaz mute",
    }:
        return {"action": "volume_mute"}

    if c in {
        "unmute",
        "unmute volume",
        "unmute sound",
        "sound unmute",
        "volume unmute",
        "awaz unmute",
        "awaaz unmute",
    }:
        return {"action": "volume_unmute"}

    # =====================================================
    # REMEMBER SOMETHING
    # =====================================================

    remember_patterns = [
        r"remember that (.+)",
        r"remember (.+)",
        r"yaad rakho (.+)",
        r"yaad rakhna (.+)",
        r"isko yaad rakho (.+)",
    ]

    for pattern in remember_patterns:
        match = re.match(pattern, c, re.IGNORECASE)

        if match:
            fact = match.group(1).strip()

            if fact:
                add_fact(fact)

                return {
                    "action": "chat",
                    "response": "Theek hai Boss. Main yaad rakhunga."
                }

    # =====================================================
    # VIEW SOURCE CODE
    # Viewing source must NOT invoke the AI source editor.
    # =====================================================

    view_source_phrases = [
        "see your source code",
        "see the source code",
        "show your source code",
        "show me your source code",
        "show source code",
        "open your source code",
        "open source code",
        "source code dikhao",
        "source code dikha",
        "apna source code dikhao",
        "apna source code dikha",
    ]

    if any(phrase in command for phrase in view_source_phrases):
        return {
            "action": "view_source",
            "target": "tahrun.py",
        }

    # =====================================================
    # SOURCE CODE EDITING
    # Only actual change/edit requests go to the AI editor.
    # =====================================================

    source_words = [
        "code change", "code changes",
        "code mein change", "code me change",
        "edit my code", "change my code",
        "fix my code", "modify my code",
        "edit source code", "change source code",
        "fix source code", "modify source code",
        "source edit", "edit source file",
    ]

    if any(word in command for word in source_words):
        return {
            "action": "source_edit",
            "target": original,
        }

    # =====================================================
    # FILE / FOLDER DELETE
    # Actual delete requests are gated in the orchestrator by confirmation.
    # =====================================================
    delete_kind, delete_target = parse_delete_request(command)
    if delete_kind and delete_target:
        return {
            "action": "delete_path",
            "target": delete_target,
            "kind": delete_kind,
        }

    # =====================================================
    # STOP / SHUTDOWN - natural speech
    # =====================================================

    if _is_shutdown_request(c):
        return {"action": "stop"}

    if c in [
        "stop",
        "exit",
        "quit",
        "shutdown",
        "band ho jao",
        "band ho ja",
        "jarvis band ho jao"
    ]:
        return {"action": "stop"}

    # =====================================================
    # STANDBY
    # =====================================================

    if c in [
        "standby",
        "go to standby",
        "sleep",
        "so jao",
        "so ja",
        "rest karo"
    ]:
        return {"action": "standby"}

    # =====================================================
    # ROUTINE
    # =====================================================

    saved_routine = save_routine_from_text(c)
    if saved_routine:
        return {"action": "chat", "response": saved_routine}

    if _is_routine_query(c) or c in ["routine batao", "meri routine", "my routine"]:
        return {"action": "chat", "response": routine_response()}

    # =====================================================
    # WHATSAPP MESSAGE
    # =====================================================

# JARVIS_PRIORITY_WHATSAPP_ROUTER_V1
    try:
        from jarvis_whatsapp_controls import parse_command as _jarvis_parse_whatsapp_control
        _jarvis_whatsapp_action = _jarvis_parse_whatsapp_control(original)
        if _jarvis_whatsapp_action:
            return _jarvis_whatsapp_action
    except Exception as _jarvis_whatsapp_route_error:
        print(f"[JARVIS WHATSAPP ROUTER] {type(_jarvis_whatsapp_route_error).__name__}", flush=True)

    whatsapp_result = _extract_whatsapp(original)
    if whatsapp_result:
        return whatsapp_result

    # =====================================================
    # COMPUTER CONTROL
    # =====================================================

    # Screen power
    command = command.rstrip(' .!?,;:').strip()
    if command in [
        "screen off","screening off","screening off kar do","screening my screen off","turn off my screen",
        "turn off screen",
        "turn off my screen",
        "turn my screen off",
        "display off",
        "monitor off",
        "screen band",
        "screen bandh",
        "display band",
        "monitor band",
    ]:
        return {"action": "screen_off"}

    if command in [
        "screen on","screening on","screening on kar do","screening my screen on","turn on my screen",
        "turn on screen",
        "turn on my screen",
        "turn my screen on",
        "display on",
        "monitor on",
        "screen chalu",
        "display chalu",
        "monitor chalu",
    ]:
        return {"action": "screen_on"}
    # Screen power
    command = command.rstrip(' .!?,;:').strip()
    if command in [
        "screen off","screening off","screening off kar do","screening my screen off","turn off my screen",
        "turn off screen",
        "turn off my screen",
        "turn my screen off",
        "display off",
        "monitor off",
        "screen band",
        "screen bandh",
        "display band",
        "monitor band",
    ]:
        return {"action": "screen_off"}

    if command in [
        "screen on","screening on","screening on kar do","screening my screen on","turn on my screen",
        "turn on screen",
        "turn on my screen",
        "turn my screen on",
        "display on",
        "monitor on",
        "screen chalu",
        "display chalu",
        "monitor chalu",
    ]:
        return {"action": "screen_on"}
    # Screen ON/OFF
    if command in [
        "turn on screen", "turn on my screen", "screen on","screening on","screening on kar do","screening my screen on","turn on my screen",
        "screen chalu karo", "screen on kar do", "monitor on", "display on"
    ]:
        return {"action": "screen_on"}

    if command in [
        "turn off screen", "turn off my screen", "screen off","screening off","screening off kar do","screening my screen off","turn off my screen",
        "screen band karo", "screen band kar do", "monitor off", "display off"
    ]:
        return {"action": "screen_off"}
    # Screenshot
    if command in [
        "take screenshot",
        "screenshot lo",
        "screenshot le lo",
        "screen shot lo",
        "screen capture lo",
    ]:
        return {"action": "screenshot"}

    # Screen size
    if command in [
        "screen size batao",
        "screen resolution batao",
        "display size batao",
        "monitor size batao",
    ]:
        return {"action": "screen_size"}

    # Mouse clicks
    if command in ["click", "click karo", "mouse click", "mouse se click karo"]:
        return {"action": "click"}

    if command in [
        "double click",
        "double click karo",
        "mouse double click",
    ]:
        return {"action": "double_click"}

    if command in [
        "right click",
        "right click karo",
        "mouse right click",
    ]:
        return {"action": "right_click"}

    # Keyboard
    if command in ["press enter", "enter press karo", "enter dabao"]:
        return {"action": "press_key", "target": "enter"}

    if command in ["press esc", "press escape", "escape dabao", "esc dabao"]:
        return {"action": "press_key", "target": "esc"}

    if command in ["press tab", "tab dabao"]:
        return {"action": "press_key", "target": "tab"}

    if command in ["press space", "space dabao"]:
        return {"action": "press_key", "target": "space"}

    # Type text
    type_match = re.match(
        r"^(?:type|type karo|likho|text likho)\s+(.+)$",
        command,
        re.IGNORECASE,
    )
    if type_match:
        return {
            "action": "type_text",
            "target": type_match.group(1).strip()
        }

    # =====================================================
    # YOUTUBE
    # =====================================================

    if "youtube" in c or "you tube" in c:

        youtube_action_words = [
            "play",
            "chalao",
            "bajao",
            "song",
            "gaana",
            "video",
            "search",
            "khol",
            "kholo",
            "open",
            "launch"
        ]

        if any(word in c for word in youtube_action_words):

            query = extract_youtube_query(original)

            if query:
                print(f"ÃƒÂ¢Ã¢â‚¬â€œÃ‚Â¶ÃƒÂ¯Ã‚Â¸Ã‚Â YouTube command detected: {query}")

                return {
                    "action": "youtube",
                    "target": query
                }

            if c in [
                "youtube kholo",
                "youtube open karo",
                "youtube khol do",
                "open youtube",
                "launch youtube",
                "you tube kholo",
                "you tube open karo",
                "open you tube",
                "launch you tube",
            ]:
                return {
                    "action": "open_website",
                    "target": "youtube"
                }

    # =====================================================
    # WEBSITE BUILDING
    # =====================================================

    site_words = [
        "website",
        "web site",
        "webpage",
        "web page",
        "site",
        "portfolio",
        "landing page",
        "navbar",
        "hero section",
        "contact section"
    ]

    task_words = [
        "bana",
        "banao",
        "bana do",
        "banakar",
        "banake",
        "create",
        "build",
        "develop",
        "design",
        "edit",
        "change",
        "modify",
        "update",
        "improve",
        "fix",
        "add",
        "remove",
        "replace",
        "responsive",
        "animation",
        "professional"
    ]

    if (
        any(x in c for x in site_words)
        and any(x in c for x in task_words)
    ):
        print("ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â» Website coding task detected.")

        return {
            "action": "build_website",
            "target": original
        }    # =====================================================
    # IMAGE GENERATION
    # =====================================================

    image_triggers = [
        "generate image",
        "generate an image",
        "create image",
        "create an image",
        "make an image",
        "make image",
        "image generate karo",
        "image banao",
        "image bana do",
        "tasveer banao",
        "picture banao",
        "photo banao",
        "image create karo",
    ]

    for trigger in image_triggers:
        if trigger in c:
            prompt = c.split(trigger, 1)[1].strip()

            if prompt:
                print(f"ÃƒÂ°Ã…Â¸Ã…Â½Ã‚Â¨ Image generation task detected: {prompt}", flush=True)
                return {
                    "action": "generate_image",
                    "target": prompt,
                }


    # =====================================================
    # IMAGE GENERATION CONFIRMATION / FOLLOW-UP
    # =====================================================

    image_confirmations = {
        "haan", "han", "yes", "yeah", "yep", "ok", "okay",
        "haan kar do", "han kar do", "yes do it", "yes generate it",
        "generate it", "make it", "create it", "kar do", "bana do"
    }

    if c in image_confirmations:
        try:
            _memory = load_memory()
            _conversations = _memory.get("conversations", [])

            for _item in reversed(_conversations):
                _previous_user = str(_item.get("user", "")).strip()

                if any(_trigger in _previous_user.lower() for _trigger in image_triggers):
                    _prompt = _previous_user

                    for _trigger in image_triggers:
                        if _trigger in _prompt.lower():
                            _prompt = _prompt.lower().split(_trigger, 1)[1].strip()
                            break

                    if _prompt:
                        print(f"Image confirmation detected: {_prompt}", flush=True)
                        return {
                            "action": "generate_image",
                            "target": _prompt,
                        }

        except Exception as _e:
            print(f"Image confirmation context error: {_e}", flush=True)

    # =====================================================
    # APPS
    # =====================================================

    apps = {
        "chrome": [
            "open chrome",
            "chrome kholo",
            "chrome open karo",
            "chrome khol do",
            "launch chrome"
        ],
        "vscode": [
            "open vscode",
            "open vs code",
            "vscode kholo",
            "vs code kholo",
            "vscode open karo",
            "vs code open karo"
        ],
        "notepad": [
            "open notepad",
            "notepad kholo",
            "notepad open karo"
        ],
        "calculator": [
            "open calculator",
            "calculator kholo",
            "calculator open karo"
        ],
        "paint": [
            "open paint",
            "paint kholo",
            "paint open karo"
        ],
    }

    for app, phrases in apps.items():

        if c in phrases:
            return {
                "action": "open_app",
                "target": app
            }

    # Extra installed Windows apps. These run before website aliases.
    extra_apps = {
        "whatsapp": ["open whatsapp", "whatsapp kholo", "whatsapp open karo", "whatsapp khol do", "launch whatsapp"],
        "instagram": ["open instagram", "instagram kholo", "instagram open karo", "instagram khol do", "launch instagram", "insta kholo", "insta open karo", "open insta"],
        "chatgpt": ["open chatgpt", "chatgpt kholo", "chatgpt open karo", "chatgpt khol do", "launch chatgpt"],
        "claude": ["open claude", "claude kholo", "claude open karo", "claude khol do", "launch claude", "open anthropic"],
        "node": ["open node", "node kholo", "node open karo", "launch node"],
        "chrome": ["open chrome", "chrome kholo", "chrome open karo", "chrome khol do", "launch chrome"],
        "vscode": ["open vscode", "vscode kholo", "vscode open karo", "vscode khol do", "launch vscode"],
    }
    for app, phrases in extra_apps.items():
        if command in phrases:
            return {"action": "open_app", "target": app}


    # =====================================================
    # MULTILINGUAL INDIAN APP COMMAND ROUTER
    # Handles major Indian languages + English/Hinglish.
    # This is deterministic: if an installed app is clearly named
    # together with an open/launch command, do not fall through to AI.
    # =====================================================
    indian_open_words = [
        # English / Hinglish
        "open", "launch", "start", "run", "chalao", "chalu karo",
        "khol", "kholo", "khol do", "open karo", "open kar",
        # Hindi / Urdu
        "ÃƒÂ Ã‚Â¤Ã¢â‚¬â€œÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¤Ã¢â‚¬â€œÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â²", "ÃƒÂ Ã‚Â¤Ã¢â‚¬â€œÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â² ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Å“",
        "ÃƒÅ¡Ã‚Â©ÃƒÅ¡Ã‚Â¾Ãƒâ„¢Ã‹â€ Ãƒâ„¢Ã¢â‚¬Å¾Ãƒâ„¢Ã‹â€ ", "ÃƒÅ¡Ã‚Â©ÃƒÅ¡Ã‚Â¾Ãƒâ„¢Ã‹â€ Ãƒâ„¢Ã¢â‚¬Å¾", "ÃƒÅ¡Ã‚Â©ÃƒÅ¡Ã‚Â¾Ãƒâ„¢Ã‹â€ Ãƒâ„¢Ã¢â‚¬Å¾ ÃƒËœÃ‚Â¯Ãƒâ„¢Ã‹â€ ", "ÃƒÅ¡Ã¢â‚¬Â ÃƒËœÃ‚Â§Ãƒâ„¢Ã¢â‚¬Å¾Ãƒâ„¢Ã‹â€  ÃƒÅ¡Ã‚Â©ÃƒËœÃ‚Â±Ãƒâ„¢Ã‹â€ ", "ÃƒËœÃ‚Â´ÃƒËœÃ‚Â±Ãƒâ„¢Ã‹â€ ÃƒËœÃ‚Â¹ ÃƒÅ¡Ã‚Â©ÃƒËœÃ‚Â±Ãƒâ„¢Ã‹â€ ",
        # Bengali
        "ÃƒÂ Ã‚Â¦Ã¢â‚¬â€œÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¦Ã¢â‚¬â€œÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â¨", "ÃƒÂ Ã‚Â¦Ã¢â‚¬â€œÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â§Ã¢â‚¬Â¡ ÃƒÂ Ã‚Â¦Ã‚Â¦ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã¢â‚¬Å“", "ÃƒÂ Ã‚Â¦Ã…Â¡ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â§Ã‚Â ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¦Ã‚Â°ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¦Ã‚Â¶ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â°ÃƒÂ Ã‚Â§Ã‚Â ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¦Ã‚Â°ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹",
        # Telugu
        "ÃƒÂ Ã‚Â°Ã‚Â¤ÃƒÂ Ã‚Â±Ã¢â‚¬Â ÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚ÂµÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â°Ã‚Â¤ÃƒÂ Ã‚Â±Ã¢â‚¬Â ÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â°Ã‚ÂµÃƒÂ Ã‚Â°Ã¢â‚¬Å¡ÃƒÂ Ã‚Â°Ã‚Â¡ÃƒÂ Ã‚Â°Ã‚Â¿", "ÃƒÂ Ã‚Â°Ã¢â‚¬Å“ÃƒÂ Ã‚Â°Ã‚ÂªÃƒÂ Ã‚Â±Ã¢â‚¬Â ÃƒÂ Ã‚Â°Ã‚Â¨ÃƒÂ Ã‚Â±Ã‚Â ÃƒÂ Ã‚Â°Ã…Â¡ÃƒÂ Ã‚Â±Ã¢â‚¬Â¡ÃƒÂ Ã‚Â°Ã‚Â¯ÃƒÂ Ã‚Â°Ã‚Â¿", "ÃƒÂ Ã‚Â°Ã‚Â¤ÃƒÂ Ã‚Â±Ã¢â‚¬Â ÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â°Ã‚Â¿ÃƒÂ Ã‚Â°Ã…Â¡ÃƒÂ Ã‚Â°Ã‚Â¿ ÃƒÂ Ã‚Â°Ã‚ÂªÃƒÂ Ã‚Â±Ã¢â‚¬Â ÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â°Ã‚ÂªÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â°Ã¢â‚¬Å¡ÃƒÂ Ã‚Â°Ã‚Â­ÃƒÂ Ã‚Â°Ã‚Â¿ÃƒÂ Ã‚Â°Ã¢â‚¬Å¡ÃƒÂ Ã‚Â°Ã…Â¡ÃƒÂ Ã‚Â±Ã‚Â",
        # Marathi
        "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã‹Å“ÃƒÂ Ã‚Â¤Ã‚Â¡", "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã‹Å“ÃƒÂ Ã‚Â¤Ã‚Â¡ÃƒÂ Ã‚Â¤Ã‚Â¾", "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã‹Å“ÃƒÂ Ã‚Â¤Ã‚Â¡ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¨ ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡", "ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â°", "ÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â°",
        # Tamil
        "ÃƒÂ Ã‚Â®Ã‚Â¤ÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã‚Â±", "ÃƒÂ Ã‚Â®Ã‚Â¤ÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã‚Â±ÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â®Ã‚ÂµÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚Â®ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â®Ã‚Â¤ÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã‚Â±ÃƒÂ Ã‚Â®Ã‚Â¨ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚Â¤ÃƒÂ Ã‚Â¯Ã‚Â ÃƒÂ Ã‚Â®Ã‚ÂµÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â®Ã‚Â¤ÃƒÂ Ã‚Â¯Ã…Â ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â®Ã¢â€žÂ¢ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â®Ã¢â‚¬Â ÃƒÂ Ã‚Â®Ã‚Â°ÃƒÂ Ã‚Â®Ã‚Â®ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚ÂªÃƒÂ Ã‚Â®Ã‚Â¿",
        # Gujarati
        "ÃƒÂ Ã‚ÂªÃ¢â‚¬â€œÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ‚Â²ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹", "ÃƒÂ Ã‚ÂªÃ¢â‚¬â€œÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ‚Â²", "ÃƒÂ Ã‚ÂªÃ¢â‚¬â€œÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ‚Â²ÃƒÂ Ã‚Â«Ã¢â€šÂ¬ ÃƒÂ Ã‚ÂªÃ‚Â¦ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹", "ÃƒÂ Ã‚ÂªÃ…Â¡ÃƒÂ Ã‚ÂªÃ‚Â¾ÃƒÂ Ã‚ÂªÃ‚Â²ÃƒÂ Ã‚Â«Ã‚Â ÃƒÂ Ã‚ÂªÃ¢â‚¬Â¢ÃƒÂ Ã‚ÂªÃ‚Â°ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹", "ÃƒÂ Ã‚ÂªÃ‚Â¶ÃƒÂ Ã‚ÂªÃ‚Â°ÃƒÂ Ã‚Â«Ã¢â‚¬Å¡ ÃƒÂ Ã‚ÂªÃ¢â‚¬Â¢ÃƒÂ Ã‚ÂªÃ‚Â°ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹",
        # Kannada
        "ÃƒÂ Ã‚Â²Ã‚Â¤ÃƒÂ Ã‚Â³Ã¢â‚¬Â ÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â³Ã¢â‚¬Â ", "ÃƒÂ Ã‚Â²Ã‚Â¤ÃƒÂ Ã‚Â³Ã¢â‚¬Â ÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â³Ã¢â‚¬Â ÃƒÂ Ã‚Â²Ã‚Â¯ÃƒÂ Ã‚Â²Ã‚Â¿ÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â²Ã‚Â¿", "ÃƒÂ Ã‚Â²Ã‚Â¤ÃƒÂ Ã‚Â³Ã¢â‚¬Â ÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â³Ã¢â‚¬Â ÃƒÂ Ã‚Â²Ã‚Â¦ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â¬ÃƒÂ Ã‚Â²Ã‚Â¿ÃƒÂ Ã‚Â²Ã‚Â¡ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚Â²Ã…Â¡ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚Â²ÃƒÂ Ã‚Â³Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â²Ã‚Â®ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚Â¡ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚Â²Ã‚ÂªÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â²Ã¢â‚¬Å¡ÃƒÂ Ã‚Â²Ã‚Â­ÃƒÂ Ã‚Â²Ã‚Â¿ÃƒÂ Ã‚Â²Ã‚Â¸ÃƒÂ Ã‚Â³Ã‚Â",
        # Malayalam
        "ÃƒÂ Ã‚Â´Ã‚Â¤ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ¢â‚¬Å¡", "ÃƒÂ Ã‚Â´Ã‚Â¤ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã¢â‚¬Â¢", "ÃƒÂ Ã‚Â´Ã‚Â¤ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚Â´Ã‚Â¨ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â¨ÃƒÂ Ã‚ÂµÃ‚Â ÃƒÂ Ã‚Â´Ã‚Â¤ÃƒÂ Ã‚Â´Ã‚Â°ÃƒÂ Ã‚ÂµÃ¢â‚¬Å¡", "ÃƒÂ Ã‚Â´Ã¢â‚¬Å“ÃƒÂ Ã‚Â´Ã‚ÂªÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚ÂªÃƒÂ Ã‚ÂµÃ‚Âº ÃƒÂ Ã‚Â´Ã…Â¡ÃƒÂ Ã‚ÂµÃ¢â‚¬Â ÃƒÂ Ã‚Â´Ã‚Â¯ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â¯ÃƒÂ Ã‚ÂµÃ¢â‚¬Å¡", "ÃƒÂ Ã‚Â´Ã‚Â¤ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã…Â¸ÃƒÂ Ã‚Â´Ã¢â€žÂ¢ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã¢â€žÂ¢ÃƒÂ Ã‚ÂµÃ¢â‚¬Å¡",
        # Punjabi
        "ÃƒÂ Ã‚Â¨Ã¢â‚¬â€œÃƒÂ Ã‚Â©Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¨Ã‚Â²ÃƒÂ Ã‚Â©Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Â¹ÃƒÂ Ã‚Â©Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¨Ã¢â‚¬â€œÃƒÂ Ã‚Â©Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¨Ã‚Â²ÃƒÂ Ã‚Â©Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Â¹", "ÃƒÂ Ã‚Â¨Ã¢â‚¬â€œÃƒÂ Ã‚Â©Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¨Ã‚Â²ÃƒÂ Ã‚Â©Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Â¹ ÃƒÂ Ã‚Â¨Ã‚Â¦ÃƒÂ Ã‚Â¨Ã‚Â¿ÃƒÂ Ã‚Â¨Ã¢â‚¬Å“", "ÃƒÂ Ã‚Â¨Ã…Â¡ÃƒÂ Ã‚Â¨Ã‚Â¾ÃƒÂ Ã‚Â¨Ã‚Â²ÃƒÂ Ã‚Â©Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¨Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¨Ã‚Â°ÃƒÂ Ã‚Â©Ã¢â‚¬Â¹", "ÃƒÂ Ã‚Â¨Ã‚Â¸ÃƒÂ Ã‚Â¨Ã‚Â¼ÃƒÂ Ã‚Â©Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Â°ÃƒÂ Ã‚Â©Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¨Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¨Ã‚Â°ÃƒÂ Ã‚Â©Ã¢â‚¬Â¹",
        # Odia
        "ÃƒÂ Ã‚Â¬Ã¢â‚¬â€œÃƒÂ Ã‚Â­Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¬Ã‚Â²", "ÃƒÂ Ã‚Â¬Ã¢â‚¬â€œÃƒÂ Ã‚Â­Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¬Ã‚Â²ÃƒÂ Ã‚Â¬Ã‚Â¨ÃƒÂ Ã‚Â­Ã‚ÂÃƒÂ Ã‚Â¬Ã‚Â¤ÃƒÂ Ã‚Â­Ã‚Â", "ÃƒÂ Ã‚Â¬Ã¢â‚¬â€œÃƒÂ Ã‚Â­Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¬Ã‚Â²ÃƒÂ Ã‚Â¬Ã‚Â¿ÃƒÂ Ã‚Â¬Ã‚Â¦ÃƒÂ Ã‚Â¬Ã‚Â¿ÃƒÂ Ã‚Â¬Ã¢â‚¬Â¦", "ÃƒÂ Ã‚Â¬Ã…Â¡ÃƒÂ Ã‚Â¬Ã‚Â¾ÃƒÂ Ã‚Â¬Ã‚Â²ÃƒÂ Ã‚Â­Ã‚Â ÃƒÂ Ã‚Â¬Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¬Ã‚Â°", "ÃƒÂ Ã‚Â¬Ã¢â‚¬Â ÃƒÂ Ã‚Â¬Ã‚Â°ÃƒÂ Ã‚Â¬Ã‚Â®ÃƒÂ Ã‚Â­Ã‚ÂÃƒÂ Ã‚Â¬Ã‚Â­ ÃƒÂ Ã‚Â¬Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¬Ã‚Â°",
        # Assamese
        "ÃƒÂ Ã‚Â¦Ã¢â‚¬â€œÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢", "ÃƒÂ Ã‚Â¦Ã¢â‚¬â€œÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã‚Â²", "ÃƒÂ Ã‚Â¦Ã¢â‚¬â€œÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â¦Ã‚Â¿ ÃƒÂ Ã‚Â¦Ã‚Â¦ÃƒÂ Ã‚Â¦Ã‚Â¿ÃƒÂ Ã‚Â¦Ã‚Â¯ÃƒÂ Ã‚Â¦Ã‚Â¼ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢", "ÃƒÂ Ã‚Â¦Ã…Â¡ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â§Ã‚Â ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â§Ã‚Â°ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢", "ÃƒÂ Ã‚Â¦Ã¢â‚¬Â ÃƒÂ Ã‚Â§Ã‚Â°ÃƒÂ Ã‚Â¦Ã‚Â®ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â­ ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â§Ã‚Â°ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢",
    ]

    app_command_names = {
        "chrome": ["chrome", "google chrome", "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â®", "ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â°ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã‚Â®", "ÃƒÂ Ã‚Â°Ã¢â‚¬Â¢ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â±Ã¢â‚¬Â¹ÃƒÂ Ã‚Â°Ã‚Â®ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â®"],
        "instagram": ["instagram", "insta", "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬â€ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â®", "ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¦Ã‚Â¨ÃƒÂ Ã‚Â¦Ã‚Â¸ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã…Â¸ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã¢â‚¬â€ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â°ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã‚Â®", "ÃƒÂ Ã‚Â°Ã¢â‚¬Â¡ÃƒÂ Ã‚Â°Ã‚Â¨ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…â€™ÃƒÂ Ã‚Â°Ã‚Â¸ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã¢â‚¬â€ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã‚Â®ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã¢â‚¬Â¡ÃƒÂ Ã‚Â®Ã‚Â©ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚Â¸ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â®Ã‚Â¾ÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã‚Â°ÃƒÂ Ã‚Â®Ã‚Â¾ÃƒÂ Ã‚Â®Ã‚Â®ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã¢â‚¬Â¡ÃƒÂ Ã‚Â²Ã‚Â¨ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…â€™ÃƒÂ Ã‚Â²Ã‚Â¸ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã…Â¸ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã¢â‚¬â€ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚Â®ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ¢â‚¬Â¡ÃƒÂ Ã‚ÂªÃ‚Â¨ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ‚Â¸ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ…Â¸ÃƒÂ Ã‚ÂªÃ‚Â¾ÃƒÂ Ã‚ÂªÃ¢â‚¬â€ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ‚Â°ÃƒÂ Ã‚ÂªÃ‚Â¾ÃƒÂ Ã‚ÂªÃ‚Â®", "ÃƒÂ Ã‚Â´Ã¢â‚¬Â¡ÃƒÂ Ã‚ÂµÃ‚Â»ÃƒÂ Ã‚Â´Ã‚Â¸ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚Â´Ã‚Â¾ÃƒÂ Ã‚Â´Ã¢â‚¬â€ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â°ÃƒÂ Ã‚Â´Ã‚Â¾ÃƒÂ Ã‚Â´Ã¢â‚¬Å¡", "ÃƒÂ Ã‚Â¨Ã¢â‚¬Â¡ÃƒÂ Ã‚Â©Ã‚Â°ÃƒÂ Ã‚Â¨Ã‚Â¸ÃƒÂ Ã‚Â¨Ã…Â¸ÃƒÂ Ã‚Â¨Ã‚Â¾ÃƒÂ Ã‚Â¨Ã¢â‚¬â€ÃƒÂ Ã‚Â©Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Â°ÃƒÂ Ã‚Â¨Ã‚Â¾ÃƒÂ Ã‚Â¨Ã‚Â®", "ÃƒËœÃ‚Â§Ãƒâ„¢Ã¢â‚¬Â ÃƒËœÃ‚Â³Ãƒâ„¢Ã‚Â¹ÃƒËœÃ‚Â§ÃƒÅ¡Ã‚Â¯ÃƒËœÃ‚Â±ÃƒËœÃ‚Â§Ãƒâ„¢Ã¢â‚¬Â¦"],
        "whatsapp": ["whatsapp", "ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Âª", "ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Âª", "ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Âª", "ÃƒÂ Ã‚Â¦Ã‚Â¹ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã‚Â¯ÃƒÂ Ã‚Â¦Ã‚Â¼ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã…Â¸ÃƒÂ Ã‚Â¦Ã‚Â¸ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¦ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â¯ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã‚Âª", "ÃƒÂ Ã‚Â°Ã‚ÂµÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â¸ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã‚ÂªÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã‚ÂµÃƒÂ Ã‚Â®Ã‚Â¾ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚Â¸ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã¢â‚¬Â¦ÃƒÂ Ã‚Â®Ã‚ÂªÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã‚ÂµÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã…Â¸ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â¸ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚ÂªÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ‚ÂµÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ…Â¸ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ‚Â¸ÃƒÂ Ã‚ÂªÃ‚ÂÃƒÂ Ã‚ÂªÃ‚Âª", "ÃƒÂ Ã‚Â´Ã‚ÂµÃƒÂ Ã‚Â´Ã‚Â¾ÃƒÂ Ã‚Â´Ã…Â¸ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã…Â¸ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â¸ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã¢â‚¬Â ÃƒÂ Ã‚Â´Ã‚ÂªÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚ÂªÃƒÂ Ã‚ÂµÃ‚Â", "ÃƒÂ Ã‚Â¨Ã‚ÂµÃƒÂ Ã‚Â¨Ã…Â¸ÃƒÂ Ã‚Â¨Ã‚Â¸ÃƒÂ Ã‚Â¨Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Âª", "Ãƒâ„¢Ã‹â€ ÃƒËœÃ‚Â§Ãƒâ„¢Ã‚Â¹ÃƒËœÃ‚Â³ ÃƒËœÃ‚Â§Ãƒâ€ºÃ…â€™Ãƒâ„¢Ã‚Â¾"],
        "chatgpt": ["chatgpt", "chat gpt", "ÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬", "ÃƒÂ Ã‚Â¦Ã…Â¡ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â¯ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã…Â¸ÃƒÂ Ã‚Â¦Ã…â€œÃƒÂ Ã‚Â¦Ã‚Â¿ÃƒÂ Ã‚Â¦Ã‚ÂªÃƒÂ Ã‚Â¦Ã‚Â¿ÃƒÂ Ã‚Â¦Ã…Â¸ÃƒÂ Ã‚Â¦Ã‚Â¿", "ÃƒÂ Ã‚Â°Ã…Â¡ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…â€™ÃƒÂ Ã‚Â°Ã…â€œÃƒÂ Ã‚Â°Ã‚Â¿ÃƒÂ Ã‚Â°Ã‚ÂªÃƒÂ Ã‚Â°Ã‚Â¿ÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â°Ã‚Â¿", "ÃƒÂ Ã‚Â®Ã…Â¡ÃƒÂ Ã‚Â®Ã‚Â¾ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã…â€œÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã‚ÂªÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â®Ã‚Â¿", "ÃƒÂ Ã‚Â²Ã…Â¡ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã…Â¸ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…â€™ÃƒÂ Ã‚Â²Ã…â€œÃƒÂ Ã‚Â²Ã‚Â¿ÃƒÂ Ã‚Â²Ã‚ÂªÃƒÂ Ã‚Â²Ã‚Â¿ÃƒÂ Ã‚Â²Ã…Â¸ÃƒÂ Ã‚Â²Ã‚Â¿", "ÃƒÂ Ã‚ÂªÃ…Â¡ÃƒÂ Ã‚Â«Ã¢â‚¬Â¡ÃƒÂ Ã‚ÂªÃ…Â¸ÃƒÂ Ã‚ÂªÃ…â€œÃƒÂ Ã‚Â«Ã¢â€šÂ¬ÃƒÂ Ã‚ÂªÃ‚ÂªÃƒÂ Ã‚ÂªÃ‚Â¿ÃƒÂ Ã‚ÂªÃ…Â¸ÃƒÂ Ã‚Â«Ã¢â€šÂ¬", "ÃƒÂ Ã‚Â´Ã…Â¡ÃƒÂ Ã‚Â´Ã‚Â¾ÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã…â€œÃƒÂ Ã‚Â´Ã‚Â¿ÃƒÂ Ã‚Â´Ã‚ÂªÃƒÂ Ã‚Â´Ã‚Â¿ÃƒÂ Ã‚Â´Ã…Â¸ÃƒÂ Ã‚Â´Ã‚Â¿", "ÃƒÂ Ã‚Â¨Ã…Â¡ÃƒÂ Ã‚Â©Ã‹â€ ÃƒÂ Ã‚Â¨Ã…Â¸ÃƒÂ Ã‚Â¨Ã…â€œÃƒÂ Ã‚Â©Ã¢â€šÂ¬ÃƒÂ Ã‚Â¨Ã‚ÂªÃƒÂ Ã‚Â©Ã¢â€šÂ¬ÃƒÂ Ã‚Â¨Ã…Â¸ÃƒÂ Ã‚Â©Ã¢â€šÂ¬"],
        "claude": ["claude", "anthropic", "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã‚Â¡", "ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â¦Ã‚Â¡", "ÃƒÂ Ã‚Â°Ã¢â‚¬Â¢ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â²ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã‚Â¡ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚Â³ÃƒÂ Ã‚Â®Ã‚Â¾ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã¢â‚¬Â¢ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â²ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚Â¡ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ¢â‚¬Â¢ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ‚Â²ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ‚Â¡", "ÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â²ÃƒÂ Ã‚ÂµÃ¢â‚¬Â¹ÃƒÂ Ã‚Â´Ã‚Â¡ÃƒÂ Ã‚ÂµÃ‚Â", "ÃƒÂ Ã‚Â¨Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¨Ã‚Â²ÃƒÂ Ã‚Â©Ã…â€™ÃƒÂ Ã‚Â¨Ã‚Â¡"],
        "vscode": ["vscode", "vs code", "visual studio code", "ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¡", "ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¡", "ÃƒÂ Ã‚Â¦Ã‚Â­ÃƒÂ Ã‚Â¦Ã‚Â¿ÃƒÂ Ã‚Â¦Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â¸ ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã‚Â¡", "ÃƒÂ Ã‚Â°Ã‚ÂµÃƒÂ Ã‚Â±Ã¢â€šÂ¬ÃƒÂ Ã‚Â°Ã…Â½ÃƒÂ Ã‚Â°Ã‚Â¸ÃƒÂ Ã‚Â±Ã‚Â ÃƒÂ Ã‚Â°Ã¢â‚¬Â¢ÃƒÂ Ã‚Â±Ã¢â‚¬Â¹ÃƒÂ Ã‚Â°Ã‚Â¡ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã‚ÂµÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã…Â½ÃƒÂ Ã‚Â®Ã‚Â¸ÃƒÂ Ã‚Â¯Ã‚Â ÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¯Ã¢â‚¬Â¹ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã‚ÂµÃƒÂ Ã‚Â²Ã‚Â¿ÃƒÂ Ã‚Â²Ã…Â½ÃƒÂ Ã‚Â²Ã‚Â¸ÃƒÂ Ã‚Â³Ã‚Â ÃƒÂ Ã‚Â²Ã¢â‚¬Â¢ÃƒÂ Ã‚Â³Ã¢â‚¬Â¹ÃƒÂ Ã‚Â²Ã‚Â¡ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ‚ÂµÃƒÂ Ã‚Â«Ã¢â€šÂ¬.ÃƒÂ Ã‚ÂªÃ‚ÂÃƒÂ Ã‚ÂªÃ‚Â¸. ÃƒÂ Ã‚ÂªÃ¢â‚¬Â¢ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ‚Â¡", "ÃƒÂ Ã‚Â´Ã‚ÂµÃƒÂ Ã‚Â´Ã‚Â¿ÃƒÂ Ã‚Â´Ã…Â½ÃƒÂ Ã‚Â´Ã‚Â¸ÃƒÂ Ã‚ÂµÃ‚Â ÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ¢â‚¬Â¹ÃƒÂ Ã‚Â´Ã‚Â¡ÃƒÂ Ã‚ÂµÃ‚Â", "ÃƒÂ Ã‚Â¨Ã‚ÂµÃƒÂ Ã‚Â©Ã¢â€šÂ¬ÃƒÂ Ã‚Â¨Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Â¸ ÃƒÂ Ã‚Â¨Ã¢â‚¬Â¢ÃƒÂ Ã‚Â©Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¨Ã‚Â¡"],
        "notepad": ["notepad", "ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã‚Â¡", "ÃƒÂ Ã‚Â¦Ã‚Â¨ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã…Â¸ÃƒÂ Ã‚Â¦Ã‚ÂªÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â¯ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã‚Â¡", "ÃƒÂ Ã‚Â°Ã‚Â¨ÃƒÂ Ã‚Â±Ã¢â‚¬Â¹ÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…â€™ÃƒÂ Ã‚Â°Ã‚ÂªÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â¯ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã‚Â¡ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã‚Â¨ÃƒÂ Ã‚Â¯Ã¢â‚¬Â¹ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚ÂªÃƒÂ Ã‚Â¯Ã¢â‚¬Â¡ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã‚Â¨ÃƒÂ Ã‚Â³Ã¢â‚¬Â¹ÃƒÂ Ã‚Â²Ã…Â¸ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ¢Ã¢â€šÂ¬Ã…â€™ÃƒÂ Ã‚Â²Ã‚ÂªÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â¯ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚Â¡ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ‚Â¨ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ…Â¸ÃƒÂ Ã‚ÂªÃ‚ÂªÃƒÂ Ã‚Â«Ã¢â‚¬Â¡ÃƒÂ Ã‚ÂªÃ‚Â¡", "ÃƒÂ Ã‚Â´Ã‚Â¨ÃƒÂ Ã‚ÂµÃ¢â‚¬Â¹ÃƒÂ Ã‚Â´Ã…Â¸ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã…Â¸ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚ÂªÃƒÂ Ã‚Â´Ã‚Â¾ÃƒÂ Ã‚Â´Ã‚Â¡ÃƒÂ Ã‚ÂµÃ‚Â", "ÃƒÂ Ã‚Â¨Ã‚Â¨ÃƒÂ Ã‚Â©Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¨Ã…Â¸ÃƒÂ Ã‚Â¨Ã‚ÂªÃƒÂ Ã‚Â©Ã‹â€ ÃƒÂ Ã‚Â¨Ã‚Â¡"],
        "calculator": ["calculator", "calc", "ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â°", "ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â¯ÃƒÂ Ã‚Â¦Ã‚Â¾ÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¢ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã‚Â²ÃƒÂ Ã‚Â§Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¦Ã…Â¸ÃƒÂ Ã‚Â¦Ã‚Â°", "ÃƒÂ Ã‚Â°Ã¢â‚¬Â¢ÃƒÂ Ã‚Â°Ã‚Â¾ÃƒÂ Ã‚Â°Ã‚Â²ÃƒÂ Ã‚Â°Ã‚Â¿ÃƒÂ Ã‚Â°Ã¢â‚¬Â¢ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â¯ÃƒÂ Ã‚Â±Ã‚ÂÃƒÂ Ã‚Â°Ã‚Â²ÃƒÂ Ã‚Â±Ã¢â‚¬Â¡ÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â°Ã‚Â°ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â®Ã‚Â¾ÃƒÂ Ã‚Â®Ã‚Â²ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã‚Â²ÃƒÂ Ã‚Â¯Ã¢â‚¬Â¡ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â®Ã‚Â°ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã¢â‚¬Â¢ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â¯ÃƒÂ Ã‚Â²Ã‚Â¾ÃƒÂ Ã‚Â²Ã‚Â²ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã¢â‚¬Â¢ÃƒÂ Ã‚Â³Ã‚ÂÃƒÂ Ã‚Â²Ã‚Â²ÃƒÂ Ã‚Â³Ã¢â‚¬Â¡ÃƒÂ Ã‚Â²Ã…Â¸ÃƒÂ Ã‚Â²Ã‚Â°ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ¢â‚¬Â¢ÃƒÂ Ã‚Â«Ã¢â‚¬Â¡ÃƒÂ Ã‚ÂªÃ‚Â²ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ¢â‚¬Â¢ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ‚Â¯ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ‚Â²ÃƒÂ Ã‚Â«Ã¢â‚¬Â¡ÃƒÂ Ã‚ÂªÃ…Â¸ÃƒÂ Ã‚ÂªÃ‚Â°", "ÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚Â´Ã‚Â¾ÃƒÂ Ã‚ÂµÃ‚Â½ÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã¢â‚¬Â¢ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â²ÃƒÂ Ã‚ÂµÃ¢â‚¬Â¡ÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚ÂµÃ‚Â¼", "ÃƒÂ Ã‚Â¨Ã¢â‚¬Â¢ÃƒÂ Ã‚Â©Ã‹â€ ÃƒÂ Ã‚Â¨Ã‚Â²ÃƒÂ Ã‚Â¨Ã¢â‚¬Â¢ÃƒÂ Ã‚Â©Ã‚ÂÃƒÂ Ã‚Â¨Ã‚Â²ÃƒÂ Ã‚Â©Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¨Ã…Â¸ÃƒÂ Ã‚Â¨Ã‚Â°"],
        "paint": ["paint", "ms paint", "ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã…Â¸", "ÃƒÂ Ã‚Â¦Ã‚ÂªÃƒÂ Ã‚Â§Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¦Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¦Ã‚Â¨ÃƒÂ Ã‚Â§Ã‚ÂÃƒÂ Ã‚Â¦Ã…Â¸", "ÃƒÂ Ã‚Â°Ã‚ÂªÃƒÂ Ã‚Â±Ã¢â‚¬Â ÃƒÂ Ã‚Â°Ã‚Â¯ÃƒÂ Ã‚Â°Ã‚Â¿ÃƒÂ Ã‚Â°Ã¢â‚¬Å¡ÃƒÂ Ã‚Â°Ã…Â¸ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã‚ÂªÃƒÂ Ã‚Â¯Ã¢â‚¬Â ÃƒÂ Ã‚Â®Ã‚Â¯ÃƒÂ Ã‚Â®Ã‚Â¿ÃƒÂ Ã‚Â®Ã‚Â£ÃƒÂ Ã‚Â¯Ã‚ÂÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã‚ÂªÃƒÂ Ã‚Â³Ã¢â‚¬Â¡ÃƒÂ Ã‚Â²Ã¢â‚¬Å¡ÃƒÂ Ã‚Â²Ã…Â¸ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ‚ÂªÃƒÂ Ã‚Â«Ã¢â‚¬Â¡ÃƒÂ Ã‚ÂªÃ¢â‚¬Â¡ÃƒÂ Ã‚ÂªÃ‚Â¨ÃƒÂ Ã‚Â«Ã‚ÂÃƒÂ Ã‚ÂªÃ…Â¸", "ÃƒÂ Ã‚Â´Ã‚ÂªÃƒÂ Ã‚ÂµÃ¢â‚¬Â ÃƒÂ Ã‚Â´Ã‚Â¯ÃƒÂ Ã‚Â´Ã‚Â¿ÃƒÂ Ã‚Â´Ã‚Â¨ÃƒÂ Ã‚ÂµÃ‚ÂÃƒÂ Ã‚Â´Ã‚Â±ÃƒÂ Ã‚ÂµÃ‚Â", "ÃƒÂ Ã‚Â¨Ã‚ÂªÃƒÂ Ã‚Â©Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¨Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¨Ã…Â¸"],
        "node": ["node", "nodejs", "node js", "ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¡", "ÃƒÂ Ã‚Â¦Ã‚Â¨ÃƒÂ Ã‚Â§Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¦Ã‚Â¡", "ÃƒÂ Ã‚Â°Ã‚Â¨ÃƒÂ Ã‚Â±Ã¢â‚¬Â¹ÃƒÂ Ã‚Â°Ã‚Â¡ÃƒÂ Ã‚Â±Ã‚Â", "ÃƒÂ Ã‚Â®Ã‚Â¨ÃƒÂ Ã‚Â¯Ã¢â‚¬Â¹ÃƒÂ Ã‚Â®Ã…Â¸ÃƒÂ Ã‚Â¯Ã‚Â", "ÃƒÂ Ã‚Â²Ã‚Â¨ÃƒÂ Ã‚Â³Ã¢â‚¬Â¹ÃƒÂ Ã‚Â²Ã‚Â¡ÃƒÂ Ã‚Â³Ã‚Â", "ÃƒÂ Ã‚ÂªÃ‚Â¨ÃƒÂ Ã‚Â«Ã¢â‚¬Â¹ÃƒÂ Ã‚ÂªÃ‚Â¡", "ÃƒÂ Ã‚Â´Ã‚Â¨ÃƒÂ Ã‚ÂµÃ¢â‚¬Â¹ÃƒÂ Ã‚Â´Ã‚Â¡ÃƒÂ Ã‚ÂµÃ‚Â", "ÃƒÂ Ã‚Â¨Ã‚Â¨ÃƒÂ Ã‚Â©Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¨Ã‚Â¡"],
    }

    # Check app name + an Indian-language open/launch verb.
    for app, names in app_command_names.items():
        name_found = any(name in command for name in names)
        if not name_found:
            continue

        # Direct app-name commands remain supported.
        if command in names:
            return {"action": "open_app", "target": app}

        if any(word in command for word in indian_open_words):
            return {"action": "open_app", "target": app}

    # =====================================================
    # WEBSITES
    # =====================================================

    sites = {
        "youtube": [
            "youtube kholo",
            "youtube open karo",
            "youtube khol do",
            "open youtube",
            "launch youtube"
        ],
        "google": [
            "google kholo",
            "google open karo",
            "open google"
        ],
        "facebook": [
            "facebook kholo",
            "facebook open karo",
            "open facebook"
        ],
    }

    for site, phrases in sites.items():

        if c in phrases:
            return {
                "action": "open_website",
                "target": site
            }

    # =====================================================
    # JARVIS_YOUTUBE_MUSIC_PRIORITY_V1
    # Explicit YouTube song commands must win over local Music-folder routing.
    if "youtube" in c or "you tube" in c:
        yt_query = extract_youtube_query(original)
        if yt_query:
            return {"action": "youtube", "target": yt_query}

    # JARVIS_MUSIC_MODE_TOGGLE_V1
    if c in {
        "music mode",
        "music mode on",
        "music mode off",
        "music mode toggle",
        "music mode chalu karo",
        "music mode band karo",
        "music mode on karo",
        "music mode off karo",
    }:
        return {"action": "music_mode_toggle", "target": ""}

# JARVIS_MUSIC_ROUTING_V1
    # LOCAL MUSIC ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â NO YOUTUBE
    # =====================================================
    music_play_match = re.match(
        r"^(?:please\s+)?(?:play|bajao|chalao)\s+(?:the\s+)?(?:song\s+|music\s+)?(.+)$",
        command, re.IGNORECASE,
    )
    if music_play_match:
        music_query = music_play_match.group(1).strip()
        if music_query.lower() not in {"music", "a song", "some music"}:
            return {"action": "music_play", "target": music_query}

    if c in {"play music", "music play karo", "music chalao", "music bajao", "music play"}:
        return {"action": "music_Play", "target": ""}

    if c in {"pause music", "music pause karo", "music rok do", "music pause"}:
        return {"action": "music_pause", "target": ""}

    if c in {"resume music", "music resume karo", "music continue karo", "music chalao dobara"}:
        return {"action": "music_resume", "target": ""}

    if c in {"stop music", "music stop karo", "music band karo", "music band kar do"}:
        return {"action": "music_stop", "target": ""}

    if c in {"next song", "next music", "agla gaana", "agla song", "next gana"}:
        return {"action": "music_next", "target": ""}

    # =====================================================
    # FOLDERS
    # =====================================================

    for folder in [
        "desktop",
        "downloads",
        "documents",
        "pictures",
        "videos",
        "music"
    ]:

        if c in [
            f"open {folder}",
            f"{folder} kholo",
            f"{folder} open karo"
        ]:

            return {
                "action": "open_folder",
                "target": folder
            }

    # =====================================================
    # WEB SEARCH
    # =====================================================

    for trigger in [
        "search for ",
        "search ",
        "google ",
        "find on google "
    ]:

        if c.startswith(trigger):

            query = c[len(trigger):].strip()

            if query:
                return {
                    "action": "search_web",
                    "target": query
                }

    # =====================================================
    # CLOSE APPS
    # =====================================================

    closes = {
        "chrome": [
            "close chrome",
            "chrome band karo",
            "chrome band kar do"
        ],
        "notepad": [
            "close notepad",
            "notepad band karo",
            "notepad band kar do"
        ],
    }

    for app, phrases in closes.items():

        if c in phrases:
            return {
                "action": "close_app",
                "target": app
            }
    # =====================================================
    # SHOW MEMORY
    # =====================================================

    if c in [
        "what do you remember",
        "what do you remember about me",
        "tumhe kya yaad hai",
        "mujhe kya yaad hai",
        "meri memory batao"
    ]:
        memory = load_memory()
        facts = memory.get("facts", [])

        if not facts:
            return {
                "action": "chat",
                "response": "Boss, abhi meri memory mein kuch saved nahi hai."
            }

        response = "Boss, mujhe ye yaad hai: " + "; ".join(facts[-10:])

        return {
            "action": "chat",
            "response": response
        }

    # =====================================================
    # FORGET ALL MEMORY
    # =====================================================

    if c in [
        "forget everything",
        "forget all memories",
        "sab kuch bhool jao",
        "meri sari memory delete karo"
    ]:
        clear_memory()

        return {
            "action": "chat",
            "response": "Theek hai Boss. Saari saved memory delete kar di."
        }
    # =====================================================
    # AI CHAT + MEMORY
    # =====================================================

    print("ÃƒÂ°Ã…Â¸Ã‚Â§Ã‚Â  Jarvis AI thinking...")

    # JARVIS_MUSIC_ROUTER_FIX
    _mc = c.strip().lower()
    for _prefix in (
        "play ",
        "play song ",
        "gaana chalao ",
        "song chalao ",
        "music bajao ",
        "music chalao ",
    ):
        if _mc.startswith(_prefix):
            original = _mc[len(_prefix):].strip()
            break

    response = ask_ai(original)

    add_conversation(
        original,
        response
    )

    return {
        "action": "chat",
        "response": response
    }














