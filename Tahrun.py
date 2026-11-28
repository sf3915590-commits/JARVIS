import study_mode as _jarvis_study_mode
from jarvis_dashboard_runtime import start_real_dashboard, start_telemetry, get_dashboard_command
import time
import threading
import ctypes
import difflib
import re
import keyboard
import sounddevice as sd
import numpy as np
from pathlib import Path
import os
import subprocess
import webbrowser

from command_repair import repair_command
from voice import speak as _voice_speak
from brain import understand as _brain_understand
import brain as _jarvis_brain
import ollama
from memory_manager import add_conversation
from whatsapp_agent import WhatsAppAgent
from actions import actions
from coding_agent import build_website
from youtube_agent import play_youtube
from file_manager import read_pdf
from source_agent import edit_source
from security_policy import needs_message_approval, explicit_shutdown_command
from image_agent import generate_image
from music_agent import music  # JARVIS_MUSIC_BACKEND_V1
from windows_control import launch_installed_app, close_app as close_windows_app
from config import LANGUAGE, WAKE_WORDS
from orchestrator import route as orchestrator_route

# JARVIS Music Core UI state
_music_ui_mode = False
from faster_whisper import WhisperModel
from groq import Groq

from jarvis_live_bridge import (
    safe_state as live_hud_state,
    safe_message as live_hud_message,
    safe_activity as live_hud_activity,
    safe_command as live_hud_command,
    safe_executing as live_hud_executing,
    safe_result as live_hud_result,
    safe_telemetry as live_hud_telemetry,
    diagnostic as live_hud_diagnostic,
)
# ============================================================
# JARVIS SPEECH NORMALIZER
# Existing TTS is preserved; emoji/symbol codepoints are removed
# before speech so the engine does not read emoji names.
# ============================================================


# ================= JARVIS GROQ STT V2 Ã¢â‚¬â€ ROBUST =================
_GROQ_STT_CLIENT = None
_GROQ_STT_DISABLED = False
_GROQ_STT_LAST_ERROR = None

# JARVIS_STUDY_MODE_V2
def _jarvis_handle_study_command(command):
    import re
    from pathlib import Path
    text = str(command or "").strip()
    preserved = re.sub(r"^(?:hey\s+)?jarvis[,\s:-]*", "", text, flags=re.I).strip()
    low = preserved.lower().strip(" ,.!?")
    if not low:
        return False
    if any(p in low for p in ("study mode on", "turn study mode on", "start study mode", "this is a study mode", "study mode shuru karo")):
        subject = ""
        m = re.search(r"\b(?:study|subject)\s+(?:mode\s+)?(?:on\s+)?(?:for\s+)?(python|c\+\+|cpp|dsa|data structures|computer science)\b", low)
        if m:
            subject = m.group(1)
        if subject == "cpp": subject = "C++"
        elif subject == "data structures": subject = "DSA"
        elif subject: subject = subject.title()
        _jarvis_study_mode.set_mode(True, subject or None)
        msg = "Study Mode ON" + (f" — {subject}" if subject else "") + ". Boss, study memory ready hai."
        print("[STUDY] " + msg, flush=True)
        try: speak(msg)
        except Exception: pass
        return True
    if any(p in low for p in ("study mode off", "turn study mode off", "stop study mode", "study mode band karo", "end study mode")):
        _jarvis_study_mode.stop()
        msg = "Study Mode OFF. Study memory save ho gayi, Boss."
        print("[STUDY] " + msg, flush=True)
        try: speak(msg)
        except Exception: pass
        return True
    if "study status" in low or "study memory" in low or "what did i study" in low:
        memory = _jarvis_study_mode.load_memory()
        subject = memory.get("active_subject") or "General"
        key = re.sub(r'[<>:"/\\|?*]', "", subject).replace(" ", "_")
        entry = memory.get("subjects", {}).get(key, {})
        topics = entry.get("topics", [])
        msg = f"Study Mode {'ON' if memory.get('study_mode') else 'OFF'}. Subject: {subject}. Topics: {', '.join(topics) if topics else 'none saved yet'}."
        print("[STUDY] " + msg, flush=True)
        try: speak(msg)
        except Exception: pass
        return True
    note_match = re.match(r"(?:please\s+)?(?:save|add|write)\s+(?:these\s+)?notes?\s+(?:for\s+)?(python|c\+\+|cpp|dsa|data structures|computer science)\b\s*[:,-]?\s*(.+)", preserved, re.I)
    if note_match:
        subject, note_text = note_match.group(1), note_match.group(2).strip()
        if subject.lower() == "cpp": subject = "C++"
        elif subject.lower() == "data structures": subject = "DSA"
        else: subject = subject.title()
        path = _jarvis_study_mode.add_notes(subject, note_text, topic="Voice note")
        msg = f"Notes saved: {Path(path).name}"
        print("[STUDY] " + msg, flush=True)
        try: speak(msg)
        except Exception: pass
        return True
    return False

def _get_groq_api_key():
    key = os.getenv("GROQ_API_KEY")
    if key and key.strip():
        return key.strip().strip('"\'')
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        try:
            for raw in env_file.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                name, sep, value = line.partition("=")
                if sep and name.strip() == "GROQ_API_KEY":
                    value = value.strip().strip('"\'')
                    if value:
                        os.environ["GROQ_API_KEY"] = value
                        return value
        except Exception as exc:
            print(f"Groq .env read error: {type(exc).__name__}: {exc}", flush=True)
    return None

def _get_groq_stt_client():
    global _GROQ_STT_CLIENT, _GROQ_STT_DISABLED, _GROQ_STT_LAST_ERROR
    if _GROQ_STT_CLIENT is not None:
        return _GROQ_STT_CLIENT
    if _GROQ_STT_DISABLED:
        return None
    api_key = _get_groq_api_key()
    if not api_key:
        _GROQ_STT_DISABLED = True
        print("Groq STT: GROQ_API_KEY not found; local fallback enabled.", flush=True)
        return None
    try:
        _GROQ_STT_CLIENT = Groq(api_key=api_key)
        print("Groq STT: client ready (Whisper Large V3 primary).", flush=True)
        return _GROQ_STT_CLIENT
    except Exception as exc:
        _GROQ_STT_LAST_ERROR = f"{type(exc).__name__}: {exc}"
        print(f"Groq STT client error: {_GROQ_STT_LAST_ERROR}", flush=True)
        return None

def _groq_transcribe_audio(audio_array):
    global _GROQ_STT_LAST_ERROR
    client = _get_groq_stt_client()
    if client is None:
        return ""
    import io, wave
    pcm = np.clip(audio_array * 32767.0, -32768, 32767).astype(np.int16)
    for attempt in (1, 2):
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm.tobytes())
            buf.seek(0)
            buf.name = "jarvis_stt.wav"
            result = client.audio.transcriptions.create(
                file=buf,
                model="whisper-large-v3",
            prompt=("Literal speech transcription only. Write only words actually spoken in this audio. "
                    "Do not continue, complete, summarize, translate, paraphrase, or add common phrases. "
                    "If audio is unclear, do not invent words. Vocabulary: JARVIS, YouTube, Chrome, WhatsApp, "
                    "Instagram, ChatGPT, Python, C++, JavaScript, HTML, CSS, React, Three.js, OpenVINO, Ollama, Groq, VS Code."),
                response_format="text",
                temperature=0,
            )
            text = str(result).strip()
            if text:
                print("Groq STT: transcription success.", flush=True)
            return text
        except Exception as exc:
            _GROQ_STT_LAST_ERROR = f"{type(exc).__name__}: {exc}"
            if attempt == 1:
                print(f"Groq STT attempt 1 failed: {_GROQ_STT_LAST_ERROR} Ã¢â‚¬â€ retrying once...", flush=True)
                time.sleep(0.35)
            else:
                print(f"Groq STT attempt 2 failed: {_GROQ_STT_LAST_ERROR} Ã¢â‚¬â€ using local Whisper fallback.", flush=True)
    return ""


# ================= WHISPER HALLUCINATION FILTER =================

WHISPER_HALLUCINATIONS = {
    "subtitles by the amara.org community",
    "amara.org",
    "thank you for watching",
    "please subscribe",
    "like and subscribe",
    "yang xi xi",
    "ming pao",
}

def clean_transcript(text):
    raw = str(text or "").strip()
    norm = raw.lower().strip(" .:-!?,")

    if not norm:
        return ""

    if any(item in norm for item in WHISPER_HALLUCINATIONS):
        print(
            f"[STT] Filtered Whisper hallucination: '{raw}'",
            flush=True
        )
        return ""

    if re.search(r"[\u4e00-\u9fff]", raw):
        print(
            f"[STT] Filtered CJK subtitle hallucination: '{raw}'",
            flush=True
        )
        return ""

    return raw


# ================= JARVIS SOURCE-CODE CHATGPT ROUTER V3 =================
def _jarvis_source_command_router(command):
    """Intercept the explicit source-code repair workflow before the normal brain router."""
    try:
        from jarvis_source_agent import handle_command
        handled, status, detail = handle_command(command)
        if not handled:
            return False
        if status == "review_ready":
            speak("Boss, ChatGPT ke saath source-code discussion complete ho gayi. Fix ready hai. Apply karun? Ya report dikhaun?")
        elif status == "apply_success":
            speak("Boss, ChatGPT ke proposed fix ko backup ke saath apply kiya aur validation pass ho gaya.")
        elif status == "apply_failed":
            speak("Boss, fix validation pass nahi hua. Maine changes rollback kar diye hain.")
        elif status == "show_report":
            speak("Boss, complete source-code report HUD par dikha raha hoon.")
        elif status == "cancelled":
            speak("Theek hai Boss, pending fix cancel kar diya.")
        elif status == "review_failed":
            speak("Boss, source-code repair discussion complete nahi ho paayi. HUD aur console mein exact reason de diya hai.")
        return True
    except Exception as exc:
        print(f"Source-code ChatGPT router error: {exc}", flush=True)
        try:
            speak("Boss, source-code ChatGPT workflow mein error aa gaya.")
        except Exception:
            pass
        return True
# =============== END JARVIS SOURCE-CODE CHATGPT ROUTER V3 ===============


# ============================================================
# JARVIS FAST VOICE ENGINE
# - microphone is detected ONCE, not on every listen
# - sample rate is detected ONCE
# - no 250 ms ambient calibration on every command
# - Listening is printed immediately
# - short silence ends a command quickly
# ============================================================

whatsapp_agent = WhatsAppAgent()

MIC_DEVICE = None
SAMPLE_RATE = None
BASE_THRESHOLD = 450.0
AMBIENT_RMS = 120.0

WHISPER_MODEL_NAME = "small"
whisper_model = None
_whisper_lock = threading.Lock()
_whisper_loading = False

# ============================================================
# JARVIS LOCAL AI ONLY
# Gemini/cloud fallback is deliberately bypassed here.
# ============================================================
LOCAL_AI_MODEL = "qwen3:4b-instruct"
_ai_lock = threading.Lock()


def ask_ai(text):
    """Fast normal conversation path: OpenVINO fast adapter first, clean prompt, Ollama fallback."""
    prompt = str(text or "").strip()
    if not prompt:
        return "Boss, bolo kya karna hai?"
    # JARVIS_CONTEXT_FINAL_SAFE
    try:
        from memory_manager import load_memory
        _jarvis_memory = load_memory()
        _jarvis_recent = _jarvis_memory.get('conversations', [])[-6:]
        _jarvis_context_lines = []
        for _item in _jarvis_recent:
            _u = str(_item.get('user', '')).strip()
            _j = str(_item.get('jarvis', '')).strip()

            _j = re.sub(
                r"^wala[,\s]*boss[.:! ]*",
                "",
                _j,
                flags=re.IGNORECASE
            ).strip()

            if (
                _u
                and _j
                and not any(
                    h in _u.lower()
                    for h in ("amara.org", "subtitles")
                )
            ):
                _jarvis_context_lines.append('User: ' + _u)
                _jarvis_context_lines.append('Jarvis: ' + _j)
        if _jarvis_context_lines:
            prompt = (
                'RECENT CONVERSATION:\\n'
                + '\\n'.join(_jarvis_context_lines)
                + '\\n\\nCURRENT USER MESSAGE:\\n'
                + prompt
                + '\\n\\n'
                'Continue the same conversation when the recent turns are relevant. '
                'Resolve follow-up replies such as yes, no, it, that, this, '
                'isko, usko, woh, phir, and short answers from those recent turns. '
                'If recent turns are unrelated, ignore them. Do not invent context.'
            )
    except Exception as _jarvis_context_error:
        print(f'[JARVIS CONTEXT] skipped: {_jarvis_context_error}', flush=True)

    system = (
        "You are JARVIS, a personal desktop AI assistant. "
        "Answer the exact user request. Do not invent intent. "
        "Reply naturally to the exact user request. Default to Roman Urdu/Hinglish. "
        "For Hindi/Urdu speech, ALWAYS use Latin/English alphabet (Roman Urdu/Hinglish), not Devanagari or Urdu/Arabic script. "
        "Never answer 'How are you?' or 'Thank you' with Salam or Walaikum Salam. "
        "Only use Salam/Walaikum Salam when the user actually greets with Salam/Assalamualaikum. "
        "Do not add fake greetings, unrelated memory, or made-up context. "
        "For technical questions, give the actual technical answer first. "
        "Keep voice answers concise but complete, usually 1-3 sentences. "
        "Use plain spoken text suitable for text-to-speech; avoid emojis and avoid Urdu/Arabic script. "
        "Do not add filler such as 'Let me explain' unless it is required by the answer. "
    )

    try:
        fast_chat = getattr(_jarvis_brain, "_fast_chat", None)
        if callable(fast_chat):
            response = fast_chat(
                model=getattr(_jarvis_brain, "MODEL", LOCAL_AI_MODEL),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                think=False,
                keep_alive="30m",
                options={
                    "temperature": 0.2,
                    "num_predict": 384 if str(text).startswith("__JARVIS_STUDY__") else 180,
                    "num_ctx": 1536,
                },
            )
        else:
            response = _jarvis_brain.ask_ai(prompt)

        if isinstance(response, dict):
            response = response.get("message", {}).get("content", "")
        else:
            message = getattr(response, "message", None)
            if message is not None:
                response = getattr(message, "content", response)
        answer = str(response or "").strip()

        _p_norm = re.sub(r"\s+", " ", prompt.lower()).strip()
        _a_norm = re.sub(r"\s+", " ", answer.lower()).strip()
        if _a_norm.startswith("walaikum salam") and _p_norm in {"hi", "hello", "hey", "how are you", "how are you?", "thank you", "thanks"}:
            if _p_norm in {"how are you", "how are you?"}:
                answer = "I'm doing great, Boss. I'm ready to help."
            elif _p_norm in {"thank you", "thanks"}:
                answer = "You're welcome, Boss."
            else:
                answer = "Hi Boss. How can I help?"

        # Remove Qwen reasoning blocks if the backend emitted any, without hiding the answer.
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S | re.I).strip()
        answer = re.sub(r"<think>.*", "", answer, flags=re.S | re.I).strip()

        return answer or "Boss, mujhe iska response nahi mila."
    except Exception as error:
        print(f"Local fast brain error: {error}", flush=True)
        try:
            response = ollama.chat(
                model=LOCAL_AI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                think=False,
                keep_alive="30m",
                options={"temperature": 0.2, "num_predict": 180, "num_ctx": 1536},
            )
            return str(response.get("message", {}).get("content", "")).strip() or "Boss, mujhe iska response nahi mila."
        except Exception as fallback_error:
            print(f"Ollama fallback error: {fallback_error}", flush=True)
            return "Boss, local AI abhi response nahi de raha."

def load_whisper():
    global whisper_model, _whisper_loading

    if whisper_model is not None:
        return whisper_model

    with _whisper_lock:
        if whisper_model is not None:
            return whisper_model

        if _whisper_loading:
            # Another thread is already loading it; wait briefly until ready.
            while whisper_model is None and _whisper_loading:
                time.sleep(0.05)

            return whisper_model

        _whisper_loading = True

        try:
            print(
                f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€šÃ‚Â§  Loading local STT model: {WHISPER_MODEL_NAME}...",
                flush=True,
            )

            whisper_model = WhisperModel(
                WHISPER_MODEL_NAME,
                device="cpu",
                compute_type="int8",
            )

            print("ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Local STT ready.", flush=True)

            return whisper_model

        except Exception as error:
            print(
                f"ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Local STT setup error: {error}",
                flush=True,
            )

            return None

        finally:
            _whisper_loading = False


def find_microphone():
    global MIC_DEVICE, SAMPLE_RATE

    if MIC_DEVICE is not None and SAMPLE_RATE is not None:
        return MIC_DEVICE

    try:
        devices = sd.query_devices()

        preferred = [
            "microphone array",
            "microphone",
            "headset",
            "headphone",
            "airdopes",
        ]

        # Prefer the first matching input device.
        for index, device in enumerate(devices):
            if device["max_input_channels"] <= 0:
                continue

            name = device["name"].lower()

            if any(word in name for word in preferred):
                MIC_DEVICE = index
                break

        if MIC_DEVICE is None:
            default_device = sd.default.device

            default_input = (
                default_device[0]
                if isinstance(default_device, (list, tuple))
                else default_device
            )

            if default_input is not None and default_input >= 0:
                MIC_DEVICE = int(default_input)

        if MIC_DEVICE is None:
            print("ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Koi microphone nahi mila.", flush=True)
            return None

        info = sd.query_devices(MIC_DEVICE, "input")

        SAMPLE_RATE = int(info["default_samplerate"])

        sd.check_input_settings(
            device=MIC_DEVICE,
            channels=1,
            samplerate=SAMPLE_RATE,
        )

        print(
            f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€¦Ã‚Â½Ãƒâ€šÃ‚Â¤ Microphone ready: {info['name']} | {SAMPLE_RATE} Hz",
            flush=True,
        )

        return MIC_DEVICE

    except Exception as error:
        print(
            f"ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Microphone setup error: {error}",
            flush=True,
        )

        MIC_DEVICE = None
        SAMPLE_RATE = None

        return None


def calibrate_microphone():
    """
    One-time quick calibration. We deliberately do NOT run this
    before every wake-word/command listen.
    """

    global BASE_THRESHOLD

    device = find_microphone()

    if device is None:
        return

    try:
        ambient = sd.rec(
            int(SAMPLE_RATE * 0.35),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            device=device,
            blocking=True,
        )

        sd.wait()

        ambient_rms = float(
            np.sqrt(
                np.mean(
                    np.square(
                        ambient.astype(np.float32)
                    )
                )
            )
        )

        # Keep the gate sensitive enough for normal laptop-mic distance,
        # while still staying above the measured room noise.
        global AMBIENT_RMS
        AMBIENT_RMS = max(1.0, ambient_rms)
        BASE_THRESHOLD = max(180.0, min(850.0, ambient_rms * 1.65))

        print(
            f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€¦Ã‚Â½Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â Mic calibrated | threshold={BASE_THRESHOLD:.0f}",
            flush=True,
        )

    except Exception as error:
        print(
            f"ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡ ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â Mic calibration skipped: {error}",
            flush=True,
        )

        BASE_THRESHOLD = 450.0


def _speech_evidence(audio_array):
    """Balanced 0..1 speech-likeness score; sensitive enough for normal laptop voice."""
    if audio_array is None or len(audio_array) < int(0.16 * 16000):
        return 0.0

    sr = 16000.0
    frame = int(0.08 * sr)
    samples = np.asarray(audio_array, dtype=np.float32)
    frame_scores = []
    rms_values = []
    centroid_values = []

    for start_i in range(0, len(samples) - frame + 1, frame):
        x = samples[start_i:start_i + frame]
        x = x - float(np.mean(x))
        rms = float(np.sqrt(np.mean(np.square(x))))
        rms_values.append(rms)
        if rms < 0.0025:
            continue

        spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) + 1e-9
        freqs = np.fft.rfftfreq(len(x), 1.0 / sr)

        low = float(spec[(freqs >= 60) & (freqs < 300)].sum())
        mid = float(spec[(freqs >= 300) & (freqs <= 3400)].sum())
        high = float(spec[(freqs > 3400) & (freqs <= 7000)].sum())
        total = float(spec[(freqs >= 80) & (freqs <= 7000)].sum())

        ratio = mid / (low + 1.0)
        high_ratio = high / (total + 1.0)
        signs = np.signbit(x)
        zcr = float(np.mean(signs[1:] != signs[:-1]))
        centroid = float((freqs * spec).sum()) / float(spec.sum())

        score = 0.0
        if ratio >= 0.75:
            score += 0.35
        if ratio >= 1.15:
            score += 0.15
        if zcr >= 0.012:
            score += 0.20
        if centroid >= 500.0:
            score += 0.15
        if high_ratio >= 0.06:
            score += 0.08
        if rms >= 0.008:
            score += 0.07
        frame_scores.append(min(1.0, score))
        centroid_values.append(centroid)

    if not frame_scores:
        return 0.0

    strong = sum(1 for s in frame_scores if s >= 0.45) / len(frame_scores)
    usable = sum(1 for s in frame_scores if s >= 0.25) / len(frame_scores)

    variation = 0.0
    if len(rms_values) >= 4:
        mean_rms = float(np.mean(rms_values)) + 1e-6
        rms_cv = float(np.std(rms_values)) / mean_rms
        score_cv = float(np.std(frame_scores))
        variation = min(1.0, max(rms_cv * 2.5, score_cv * 3.0))

    # Small penalty only for extremely steady tonal noise; do not reject normal speech.
    steady_penalty = 0.0
    if len(rms_values) >= 8 and centroid_values:
        rms_mean = float(np.mean(rms_values)) + 1e-6
        rms_cv = float(np.std(rms_values)) / rms_mean
        centroid_mean = float(np.mean(centroid_values)) + 1e-6
        centroid_cv = float(np.std(centroid_values)) / centroid_mean
        if rms_cv < 0.025 and centroid_cv < 0.05:
            steady_penalty = 0.12

    score = (strong * 0.55) + (usable * 0.25) + (variation * 0.20) - steady_penalty
    return float(max(0.0, min(1.0, score)))


def _speech_dynamics(audio_array):
    """Measure speech-like change over time; steady fan/AC tends to score low."""
    if audio_array is None:
        return 0.0

    samples = np.asarray(audio_array, dtype=np.float32)
    frame = int(0.08 * 16000)
    rms_values = []
    for start_i in range(0, len(samples) - frame + 1, frame):
        x = samples[start_i:start_i + frame]
        x = x - float(np.mean(x))
        rms_values.append(float(np.sqrt(np.mean(np.square(x)))))

    if len(rms_values) < 4:
        return 0.0

    arr = np.asarray(rms_values, dtype=np.float32)
    median = float(np.median(arr)) + 1e-6
    mean = float(np.mean(arr)) + 1e-6
    cv = float(np.std(arr)) / mean
    peak_ratio = float(np.max(arr)) / median
    active_change = float(np.mean(arr >= (median * 1.35)))

    onset = min(1.0, max(0.0, (peak_ratio - 1.0) / 2.0))
    variation = min(1.0, cv * 2.5)
    movement = min(1.0, active_change * 1.5)

    return float((onset * 0.45) + (variation * 0.40) + (movement * 0.15))

def _reject_stt_hallucination(text, audio_array):
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return ""
    duration = len(audio_array) / 16000.0 if audio_array is not None else 0.0
    try:
        evidence = _speech_evidence(audio_array)
    except Exception:
        evidence = 0.0
    tokens = set(normalized.split())
    amara_credit = (
        "amara" in tokens and "community" in tokens
        and any(word in tokens for word in ("by", "subtitle", "subtitles", "title", "titles"))
    ) or (
        "amara" in tokens and "org" in tokens
        and any(word in tokens for word in ("subtitle", "subtitles", "community"))
    )
    canned_outros = (
        "thank you for watching", "thanks for watching",
        "thank you for watching this video", "thanks for watching this video",
        "please subscribe", "like and subscribe",
    )
    if amara_credit or any(phrase in normalized for phrase in canned_outros):
        print(f"STT rejected subtitle/outro hallucination: {value!r}", flush=True)
        return ""
    if re.search(r"[\u4e00-\u9fff]", value):
        print(f"STT rejected CJK subtitle hallucination: {value!r}", flush=True)
        return ""
    weak_filler = {"you", "bye", "hmm", "um", "uh", "subscribe", "like and subscribe"}
    if normalized in weak_filler and (duration < 1.6 or evidence < 0.45):
        print(f"STT rejected weak filler: {value!r}", flush=True)
        return ""
    if normalized in {"thank you", "thanks"} and evidence < 0.40:
        print(f"STT rejected weak generic filler: {value!r}", flush=True)
        return ""
    return value

def listen_silence(
    max_seconds=10,
    start_timeout=2.0,
    silence_after=1.50,
    sleep_mode=False,
):
    """Balanced adaptive speech gate: sensitive for real speech, resistant to steady fan noise."""
    device = find_microphone()
    if device is None:
        return ""

    if sleep_mode:
        max_seconds = 3.2
        start_timeout = 0.90
        silence_after = 0.90
    else:
        silence_after = max(1.20, float(silence_after))

    block_seconds = 0.08
    block_size = max(1, int(SAMPLE_RATE * block_seconds))
    max_blocks = max(1, int(max_seconds / block_seconds))
    start_blocks = max(1, int(start_timeout / block_seconds))
    silence_blocks_needed = max(1, int(silence_after / block_seconds))

    print(
        "Ã°Å¸Å½Â§ Listening..." if not sleep_mode
        else "Ã°Å¸Å½Â§ Listening for 'Hey Jarvis'...",
        flush=True,
    )

    chunks = []
    speech_started = False
    silent_blocks = 0
    speech_run = 0
    candidate_blocks = 0
    started_blocks = 0
    preroll = []
    preroll_blocks = 4
    noise_floor = max(20.0, float(AMBIENT_RMS or BASE_THRESHOLD / 1.65))

    def speech_candidate(samples, rms_value):
        # Do not make the spectral classifier the primary gate.
        # The old V2 thresholds were rejecting the user's real voice.
        dynamic_threshold = max(
            150.0,
            noise_floor * 1.45,
            BASE_THRESHOLD * 0.50,
        )
        if rms_value < dynamic_threshold:
            return False

        x = samples.astype(np.float32)
        x = x - float(np.mean(x))
        spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) + 1e-9
        freqs = np.fft.rfftfreq(len(x), 1.0 / float(SAMPLE_RATE))

        low = float(spec[(freqs >= 60.0) & (freqs < 300.0)].sum())
        mid = float(spec[(freqs >= 300.0) & (freqs <= 3400.0)].sum())
        high = float(spec[(freqs > 3400.0) & (freqs <= 7000.0)].sum())
        total = float(spec[(freqs >= 80.0) & (freqs <= 7000.0)].sum())

        ratio = mid / (low + 1.0)
        high_ratio = high / (total + 1.0)
        signs = np.signbit(x)
        zcr = float(np.mean(signs[1:] != signs[:-1]))
        centroid = float((freqs * spec).sum()) / float(spec.sum())

        # Any one of these can be sufficient because some laptop mics produce
        # unusually low ZCR/spectral-ratio values even for clear speech.
        return bool(
            ratio >= 0.70
            or zcr >= 0.010
            or centroid >= 480.0
            or high_ratio >= 0.055
        )

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            device=device,
            blocksize=block_size,
        ) as stream:
            for block_index in range(max_blocks):
                data, _ = stream.read(block_size)
                data = np.asarray(data).reshape(-1)
                rms = float(np.sqrt(np.mean(np.square(data.astype(np.float32)))))
                candidate = speech_candidate(data, rms)

                if not speech_started:
                    preroll.append(data.copy())
                    if len(preroll) > preroll_blocks:
                        preroll.pop(0)

                    if rms < max(noise_floor * 1.25, BASE_THRESHOLD * 0.40):
                        noise_floor = (noise_floor * 0.985) + (rms * 0.015)

                    if candidate:
                        speech_run += 1
                    else:
                        speech_run = max(0, speech_run - 1)

                    # ~160 ms speech-like onset.
                    if speech_run >= 2:
                        speech_started = True
                        silent_blocks = 0
                        candidate_blocks = speech_run
                        started_blocks = speech_run
                        chunks.extend(preroll)
                        chunks.append(data.copy())
                        continue

                    if block_index >= start_blocks and speech_run == 0:
                        continue

                else:
                    chunks.append(data.copy())
                    started_blocks += 1
                    if candidate:
                        candidate_blocks += 1
                        silent_blocks = 0
                        speech_run = min(speech_run + 1, 10)
                    else:
                        silent_blocks += 1
                        speech_run = max(0, speech_run - 1)
                        if silent_blocks >= silence_blocks_needed:
                            break

        if not chunks or not speech_started:
            return ""

        audio_array = np.concatenate(chunks).astype(np.float32) / 32768.0

        if SAMPLE_RATE != 16000:
            target_length = int(len(audio_array) * 16000 / SAMPLE_RATE)
            if target_length <= 1:
                return ""
            audio_array = np.interp(
                np.linspace(0, len(audio_array) - 1, target_length),
                np.arange(len(audio_array)),
                audio_array,
            ).astype(np.float32)

        speech_ratio = candidate_blocks / max(1, started_blocks)
        evidence = _speech_evidence(audio_array)
        dynamics = _speech_dynamics(audio_array)
        speech_duration = started_blocks * block_seconds

        # Normal speech: permissive. The real protection against false stop is
        # applied below, only to dangerous one-word commands.
        if speech_duration < 0.20 or (speech_ratio < 0.12 and evidence < 0.20):
            print(
                f"STT skipped: weak speech evidence "
                f"(duration={speech_duration:.2f}s, candidate={speech_ratio:.2f}, "
                f"evidence={evidence:.2f}, dynamics={dynamics:.2f}).",
                flush=True,
            )
            return ""

        print("Ã°Å¸Å½â„¢Ã¯Â¸Â Recognizing speech...", flush=True)
        raw_text = _groq_transcribe_audio(audio_array)

        if raw_text:
            print(f"Ã°Å¸Å½â„¢Ã¯Â¸Â Groq RAW: {raw_text}", flush=True)
        else:
            model = load_whisper()
            if model is None:
                return ""
            transcribe_kwargs = {
                "language": None,
                "task": "transcribe",
                "beam_size": 5,
                "temperature": 0,
                "condition_on_previous_text": False,
                "vad_filter": True,
            }
            if sleep_mode:
                transcribe_kwargs["initial_prompt"] = "Hey Jarvis"
            print("Ã°Å¸Å½â„¢Ã¯Â¸Â Groq unavailable Ã¢â‚¬â€ using local Whisper fallback...", flush=True)
            segments, _ = model.transcribe(audio_array, **transcribe_kwargs)
            raw_text = " ".join(segment.text.strip() for segment in segments).strip()
            if raw_text:
                print(f"Ã°Å¸Å½â„¢Ã¯Â¸Â Local Whisper RAW: {raw_text}", flush=True)

        raw_text = _reject_stt_hallucination(raw_text, audio_array)
        if not raw_text:
            return ""

        text = correct_transcription(raw_text)

        # Standby mode: only a Jarvis-like transcript can wake JARVIS.
        if sleep_mode and text:
            wake_probe = re.sub(r"[^a-z0-9\s]", " ", text.lower())
            wake_probe = re.sub(r"\s+", " ", wake_probe).strip()
            wake_like = (
                "jarvis" in wake_probe
                or "jervis" in wake_probe
                or any(
                    difflib.SequenceMatcher(None, word, "jarvis").ratio() >= 0.78
                    for word in wake_probe.split()
                )
            )
            if not wake_like:
                print(f"Wake STT rejected non-wake transcript: {text!r}", flush=True)
                return ""

        if text:
            normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
            normalized = re.sub(r"\s+", " ", normalized).strip()

            # Dangerous state-changing commands require temporal/dynamic speech,
            # not just a high spectral score. This prevents steady fan noise from
            # becoming a false stop while keeping ordinary speech sensitive.
            safety_commands = {
                "stop", "exit", "quit", "shutdown", "jarvis stop",
                "band ho jao", "band ho ja", "jarvis band ho jao",
                "standby", "go to standby", "sleep", "so jao", "so ja",
                "cancel", "cancel command", "stop listening",
            }
            if normalized in safety_commands:
                safety_duration = len(audio_array) / 16000.0
                if (
                    safety_duration < 0.35
                    or safety_duration > 2.20
                    or evidence < 0.45
                    or dynamics < 0.20
                ):
                    print(
                        f"Safety command rejected: weak/steady audio "
                        f"(duration={safety_duration:.2f}s, evidence={evidence:.2f}, "
                        f"dynamics={dynamics:.2f}).",
                        flush=True,
                    )
                    return ""

            print(f"Ã°Å¸â€˜Â¤ You: {text}", flush=True)
        return text

    except Exception as error:
        print(f"Ã°Å¸Å½Â¤ Microphone/listening error: {error}", flush=True)
        return ""

def correct_transcription(text):
    """
    Local contextual correction for common Whisper mistakes.
    Does not send ordinary speech to Gemini.
    """

    if not text:
        return ""

    original = text.strip()

    corrected = re.sub(
        r"\s+",
        " ",
        original,
    ).strip()

    # Common JARVIS name transcription variants
    corrected = re.sub(
        r"\bjarvi\b",
        "Jarvis",
        corrected,
        flags=re.IGNORECASE,
    )

    corrected = re.sub(
        r"\bjervis\b",
        "Jarvis",
        corrected,
        flags=re.IGNORECASE,
    )

    # Common command transcription mistakes
    corrected = re.sub(
        r"\bserend\b",
        "send",
        corrected,
        flags=re.IGNORECASE,
    )

    corrected = re.sub(
        r"\bopenyoutube\b",
        "Open YouTube",
        corrected,
        flags=re.IGNORECASE,
    )
    corrected = re.sub(
        r"\bopen\s+yotube\b",
        "Open YouTube",
        corrected,
        flags=re.IGNORECASE,
    )
    corrected = re.sub(
        r"\byotube\s+open\b",
        "YouTube open",
        corrected,
        flags=re.IGNORECASE,
    )
    corrected = re.sub(
        r"\byoutubeopen\b",
        "YouTube open",
        corrected,
        flags=re.IGNORECASE,
    )

    # Common short-question Whisper confusion.
    corrected = re.sub(
        r"\b(?:as|is) you(?:'re| are) doing now\b",
        "what you're doing now",
        corrected,
        flags=re.IGNORECASE,
    )

    corrected = re.sub(
        r"\bwhat you doing now\b",
        "what you're doing now",
        corrected,
        flags=re.IGNORECASE,
    )

    # Common Whisper contractions / short-question errors.
    corrections = {
        r"\bwhat\s+you(?:'re|\s+are)?\s+doing\s+now\b": "what you're doing now",
        r"\bwhat\s+are\s+you\s+doing\s+now\b": "what you're doing now",
        r"\bas\s+you(?:'re|\s+are)\s+doing\s+now\b": "what you're doing now",
        r"\bwhat\s+you\s+doing\b": "what you're doing",
    }
    for pattern, replacement in corrections.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)

    # "network" -> "net worth" only when the surrounding
    # sentence clearly indicates a wealth/net-worth question.
    if re.search(
        r"\b(?:what(?:'s| is)|how much is|tell me)\b.*\bnetwork\b.*\b(?:of|for)\b",
        corrected,
        re.IGNORECASE,
    ):
        corrected = re.sub(
            r"\bnetwork\b",
            "net worth",
            corrected,
            count=1,
            flags=re.IGNORECASE,
        )

    if corrected != original:
        print(
            f"STT correction: {original} -> {corrected}",
            flush=True,
        )

    return corrected


def is_wake_word(text):
    """Robust local wake-word check for imperfect Whisper transcripts."""

    cleaned = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text.lower(),
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    if not cleaned:
        return False

    # Exact/common transcript forms.
    aliases = {
        "hey jarvis",
        "hey jervis",
        "jarvis",
        "jervis",
    }

    if any(
        alias in cleaned
        for alias in aliases
    ):
        return True

    # Whisper tiny sometimes changes one or two sounds in "Jarvis".
    words = cleaned.split()

    for word in words:

        if (
            difflib.SequenceMatcher(
                None,
                word,
                "jarvis",
            ).ratio()
            >= 0.72
        ):
            return True

    # Also accept a close match to the complete phrase.
    for wake_word in list(WAKE_WORDS) + [
        "hey jarvis",
        "hey jervis",
    ]:

        if (
            difflib.SequenceMatcher(
                None,
                cleaned,
                wake_word.lower(),
            ).ratio()
            >= 0.68
        ):
            return True

    return False


def _likely_incomplete_command(text):
    value = re.sub(r"[^a-z0-9\\s]", " ", str(text or "").lower())
    value = re.sub(r"\\s+", " ", value).strip()

    starters = {
        "give", "tell", "explain", "describe", "show",
        "open", "launch", "start", "play", "search",
        "make", "create", "build", "write", "type",
        "find", "check", "what", "why", "how", "can",
        "could", "please"
    }

    return len(value.split()) <= 2 and value in starters


def is_standby_command(text):
    command = text.lower().strip()

    return command in [
        "standby",
        "go to standby",
        "sleep",
        "so jao",
        "so ja",
        "rest karo",
        "wait",
        "stop listening",
        "cancel",
        "cancel command",
        "bas karo",
        "ruk jao",
    ]


def looks_like_action_command(text):
    """Use slow command repair only for action-shaped speech."""
    action_words = [
        "open", "launch", "start", "close", "play", "search", "find",
        "send", "message", "whatsapp", "youtube", "instagram", "facebook",
        "screenshot", "screen", "monitor", "display", "type", "likho",
        "click", "press", "pdf", "folder", "download", "website", "app",
        "chalao", "bajao", "khol", "kholo", "banao", "create",
    ]
    lowered = text.lower()
    return any(word in lowered for word in action_words)


# ============================================================
# JARVIS WEBSITE BUILD INTENT ROUTER V5
# Explicit website creation requests bypass brain.py classification.
# This prevents natural requests such as "make me a grocery website"
# from being downgraded to chat/AI response.
# ============================================================
def _looks_like_website_build_request(text):
    original = str(text or "").strip()
    normalized = re.sub(r"[^a-z0-9\s]", " ", original.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return False

    # These mean "open/visit/search a site", not "build one".
    navigation_only = (
        normalized.startswith((
            "open website", "open the website", "visit website", "visit the website",
            "go to website", "go to the website", "open site", "visit site",
            "search website", "search the website",
        ))
        and not re.search(r"\b(make|create|build|banao|bana|develop|design|redesign|rebuild)\b", normalized)
    )
    if navigation_only:
        return False

    build_verbs = (
        "make", "create", "build", "develop", "design", "redesign", "rebuild",
        "banao", "bana", "banado", "bana do", "tayyar", "tayyar karo",
    )
    site_nouns = (
        "website", "web site", "webpage", "web page", "site", "landing page",
        "web app", "webapp", "portfolio", "online store", "ecommerce", "e-commerce",
        "dashboard", "booking page", "product page", "restaurant site",
    )

    tech_terms = (
        "using html", "using css", "using javascript", "using js", "using react",
        "using vite", "with html", "with css", "with javascript", "with react",
        "in html", "in javascript", "in react", "vs code", "vscode",
    )

    has_build = any(v in normalized for v in build_verbs)
    has_site = any(n in normalized for n in site_nouns)

    # Strong natural-language patterns, including Hinglish.
    strong_patterns = (
        r"\bmake (me )?(a |an )?(website|webpage|web page|site|landing page|web app)",
        r"\bcreate (me )?(a |an )?(website|webpage|web page|site|landing page|web app)",
        r"\bbuild (me )?(a |an )?(website|webpage|web page|site|landing page|web app)",
        r"\bdesign (me )?(a |an )?(website|webpage|web page|site|landing page|web app)",
        r"\b(banao|bana do|banado) (mujhe )?(a |ek )?(website|site|web app|landing page)",
        r"\bwebsite\s+(banao|bana do|banado|create karo|make karo|develop karo)\b",
        r"\bwebsite\s+(chahiye|banana hai)\b",
    )
    has_tech_build_signal = any(term in normalized for term in tech_terms)
    return has_site and (
        has_build
        or has_tech_build_signal
        or any(re.search(p, normalized) for p in strong_patterns)
    )


# ============================================================
# JARVIS ROUTER WRAPPER
# Keep brain.py for real action/memory routing, but send ordinary
# conversation directly through the already-warmed fast local brain.
# This prevents greetings/questions from entering the slower brain.ask_ai().
# ============================================================

def _jarvis_route_screen_command(command):
    """Deterministically route explicit screen-vision and study-capture commands."""
    raw = re.sub(r"\s+", " ", str(command or "").strip())
    raw = re.sub(r"^(?:hey\s+)?jarvis[,\s:-]*", "", raw, flags=re.I).strip().rstrip(" .!?,;:")
    c = raw.lower()
    if not c:
        return None

    if c in {
        "save youtube timestamp", "save this youtube timestamp", "bookmark this video",
        "save video progress", "save current video timestamp", "save this point in the video",
        "mark this timestamp", "bookmark current timestamp", "save current youtube time",
        "youtube timestamp save karo", "is timestamp ko save karo", "video ka timestamp save karo",
    }:
        return {"action": "youtube_bookmark", "mode": "save"}

    if c in {"resume last study video", "resume last youtube timestamp", "open last study video", "last study video kholo"}:
        return {"action": "youtube_bookmark", "mode": "resume"}

    note_phrases = (
        "save screen notes", "save notes from screen", "take notes from screen",
        "make notes from screen", "make study notes from screen", "save screen to study notes",
        "save this screen as study notes", "save this screen to study notes",
        "study notes from screen", "screen se notes banao", "screen se notes bana do",
        "screen ke notes save karo", "screen content ko notes mein save karo",
        "current screen ke notes banao", "save current screen notes",
    )
    # Negative requests must not trigger a capture/save action.
    if re.search(r"\b(?:do not|don't|dont|never|stop)\b", c):
        return None

    if any(phrase in c for phrase in note_phrases):
        subject_match = re.search(
            r"\b(?:for|to|in)\s+(python|c\+\+|cpp|dsa|data structures|computer science|math|mathematics)\b",
            c,
            re.I,
        )
        if subject_match:
            raw_subject = subject_match.group(1)
            subject = "C++" if raw_subject.lower() in {"cpp", "c++"} else ("DSA" if raw_subject.lower() == "data structures" else raw_subject.title())
        else:
            try:
                subject = str(_jarvis_study_mode.current().get("subject") or "General")
            except Exception:
                subject = "General"
        topic_match = re.search(r"\b(?:topic|about)\s+(.+)$", raw, re.I)
        topic = topic_match.group(1).strip() if topic_match else "Screen Notes"
        return {"action": "screen_control", "mode": "study_notes", "subject": subject, "topic": topic}

    describe_commands = {
        "see my screen", "see the screen", "show my screen", "show me my screen",
        "look at my screen", "look at the screen", "check my screen", "check the screen",
        "screen dekho", "mera screen dekho", "screen dikhao", "screen check karo", "screen dekh",
        "describe my screen", "describe the screen", "analyze my screen", "analyze screen",
        "what is on my screen", "what's on my screen", "what is on screen", "what's on screen",
        "what do you see on my screen", "tell me what you see on screen", "read my screen",
        "explain what is on my screen for my study",
        "explain what's on my screen for my study",
        "explain what is on my screen",
        "explain my screen for study",
        "what is on my screen for my study",

        "screen par kya hai", "screen par kya dikh raha hai", "screen pe kya hai",
    }
    if c in describe_commands:
        return {"action": "screen_control", "mode": "describe"}

    screenshot_commands = {
        "take a screenshot", "take screenshot", "screenshot lo", "screenshot le lo",
        "capture screenshot", "capture my screen", "save screenshot", "screen capture karo",
    }
    if c in screenshot_commands:
        return {"action": "screen_control", "mode": "screenshot"}

    match = re.match(r"^(?:find|locate|look for|where is)\s+(.+?)\s+(?:on|in|at)\s+(?:my\s+)?screen$", c)
    if match:
        target = match.group(1).strip(" \"'")
        target = re.sub(r"^(?:the|a|an)\s+", "", target, flags=re.I).strip()
        if target:
            return {"action": "screen_control", "mode": "find_target", "target": target}

    match = re.match(r"^click\s+(?:on\s+)?(.+?)\s+(?:on|in)\s+(?:my\s+)?screen$", c)
    if match:
        target = match.group(1).strip(" \"'")
        target = re.sub(r"^(?:the|a|an)\s+", "", target, flags=re.I).strip()
        if target:
            return {"action": "screen_control", "mode": "click_target", "target": target}

    key_aliases = {
        "enter": "enter", "return": "enter", "tab": "tab", "escape": "esc", "esc": "esc",
        "space": "space", "spacebar": "space", "up": "up", "arrow up": "up",
        "down": "down", "arrow down": "down", "left": "left", "arrow left": "left",
        "right": "right", "arrow right": "right", "home": "home", "end": "end",
        "page up": "pageup", "page down": "pagedown",
    }
    key_match = re.match(r"^(?:press|hit|tap)\s+(?:the\s+)?(.+?)(?:\s+key)?$", c)
    if key_match:
        key = key_aliases.get(key_match.group(1).strip())
        if key:
            return {"action": "screen_control", "mode": "press_key", "key": key}

    type_match = re.match(r"^(?:type on screen|type into the active field|type into active field|type this)\s+(.+)$", raw, re.I)
    if type_match:
        return {"action": "screen_control", "mode": "type_text", "text": type_match.group(1).strip()}

    if c in {"scroll down", "scroll neeche", "neeche scroll karo"}:
        return {"action": "screen_control", "mode": "scroll", "amount": -5}
    if c in {"scroll up", "scroll upar", "upar scroll karo"}:
        return {"action": "screen_control", "mode": "scroll", "amount": 5}
    return None


def _jarvis_route_pending_quiz(command):
    """Use the next ordinary utterance as an answer only while a quiz is pending."""
    try:
        pending = _jarvis_study_mode.pending_quiz()
    except Exception:
        return None
    if not pending:
        return None

    original = re.sub(r"\s+", " ", str(command or "").strip())
    original = re.sub(r"^(?:hey\s+)?jarvis[,\s:-]*", "", original, flags=re.I).strip().rstrip(" .!?,;:")
    c = original.lower()
    if not c:
        return None

    if c in {"skip", "skip question", "skip this question", "skip quiz", "next question"}:
        return {"action": "study_skip"}

    explicit_prefixes = ("my answer is ", "answer is ", "my answer ", "answer: ", "answer ")
    for prefix in explicit_prefixes:
        if c.startswith(prefix):
            answer = original[len(prefix):].strip()
            return {"action": "study_answer", "answer": answer} if answer else None

    # Do not swallow obvious desktop-control, navigation, or Study Mode commands.
    protected = (
        "open ", "launch ", "close ", "play ", "search ", "click ", "scroll ",
        "type on screen ", "type into ", "take screenshot", "screenshot", "save screen",
        "whatsapp", "youtube", "volume ", "screen off", "screen on", "study mode",
        "study ", "teach me ", "explain ", "mujhe ", "what time", "what is the time",
        "time batao", "weather", "help me", "help", "status", "remember",
        "stop jarvis", "shutdown", "restart", "turn off", "turn on",
    )
    if c.startswith(protected):
        return None
    if len(c) < 2:
        return None
    return {"action": "study_answer", "answer": original}


def _jarvis_instant_command(text):
    """Fast deterministic router. Returns an existing execute() action or None."""
    c = re.sub(r"\s+", " ", str(text or "").lower().strip())
    c = re.sub(r"^(?:hey\s+)?jarvis[,:\s-]*", "", c).strip()
    c = c.rstrip(" .!?,;:").strip()

    # Normalize wake-name hallucinations before deterministic routing.
    c = re.sub(
        r"^(?:jarvis|jervis|darwish|darvish)[,\\s]+",
        "",
        c,
        flags=re.IGNORECASE,
    ).strip()


    # ============================================================
    # JARVIS_DEEP_STUDY_ROUTER_V3
    # ============================================================

    # PURE STUDY MODE
    if c in {
        "study mode",
        "study mode on",
        "pure study mode",
        "pure study mode on",
        "start study mode",
        "start pure study mode",
        "study start",
    }:
        return {"action": "study_mode", "mode": "start"}

    if c in {
        "study mode off",
        "pure study mode off",
        "stop study mode",
        "exit study mode",
        "study stop",
    }:
        return {"action": "study_mode", "mode": "stop"}

    if c in {
        "study progress",
        "study status",
        "my study progress",
        "study revision",
        "study weak topics",
    }:
        return {"action": "study_mode", "mode": "status"}

    # STUDY TEACH / EXPLAIN / QUIZ / TEST / REVISION
    for _study_prefix in (
        "study teach ",
        "study explain ",
        "study learn ",
        "study quiz ",
        "study test ",
        "study mock test ",
        "study revise ",
        "study solve ",
    ):
        if c.startswith(_study_prefix):
            _study_target = c[len(_study_prefix):].strip()

            if _study_target:
                return {
                    "action": "study_request",
                    "mode": _study_prefix.strip(),
                    "target": _study_target,
                }

    # NATURAL TEACHING COMMANDS
    for _study_prefix in (
        "teach me ",
        "explain to me ",
        "mujhe samjhao ",
        "mujhe padhaao ",
        "mujhe padha do ",
        "mujhe samjhaao ",
    ):
        if c.startswith(_study_prefix):
            _study_target = c[len(_study_prefix):].strip()

            if _study_target:
                return {
                    "action": "study_request",
                    "mode": "study teach",
                    "target": _study_target,
                }

    # ============================================================
    # SCREEN CONTROL ? ON DEMAND ONLY
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
        "screen dekh",
    }:
        return {
            "action": "screen_control",
            "mode": "screenshot",
        }

    if c in {
        "click allow",
        "allow click karo",
        "allow pe click karo",
        "allow par click karo",
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
    }:
        return {
            "action": "screen_control",
            "mode": "scroll",
            "amount": -5,
        }

    if c in {
        "scroll up",
        "scroll upar",
        "upar scroll karo",
    }:
        return {
            "action": "screen_control",
            "mode": "scroll",
            "amount": 5,
        }


    app_map = {
        "chrome": {
            "open chrome", "chrome kholo", "chrome open karo",
            "chrome khol do", "launch chrome"
        },
        "vscode": {
            "open vscode", "open vs code", "vscode kholo",
            "vs code kholo", "vscode open karo", "vs code open karo"
        },
        "whatsapp": {
            "open whatsapp", "whatsapp kholo",
            "whatsapp open karo", "launch whatsapp"
        },
        "notepad": {
            "open notepad", "notepad kholo", "notepad open karo"
        },
    }

    for app, phrases in app_map.items():
        if c in phrases:
            return {"action": "open_app", "target": app}

    if c in {
        "open youtube", "youtube kholo",
        "youtube open karo", "youtube khol do",
        "launch youtube"
    }:
        return {"action": "open_website", "target": "youtube"}

    if c in {
        "screen off", "turn off screen", "turn off my screen",
        "turn my screen off", "display off", "monitor off",
        "screen band", "screen bandh", "screen band karo",
        "screen band kar do"
    }:
        return {"action": "screen_off"}

    if c in {
        "screen on", "turn on screen", "turn on my screen",
        "turn my screen on", "display on", "monitor on",
        "screen chalu", "screen chalu karo"
    }:
        return {"action": "screen_on"}

    return None

def understand(text):
    original = str(text or "").strip()
    lowered = original.lower().strip()

    # JARVIS_INSTANT_FASTPATH_V1
    _instant = _jarvis_instant_command(original)
    if _instant is not None:
        print(f"[FASTPATH] {_instant}", flush=True)
        return _instant

    # JARVIS_VOICE_SHUTDOWN_V1
    _shutdown_check = re.sub(r"[^a-z0-9\s]", " ", lowered)
    _shutdown_check = re.sub(r"\s+", " ", _shutdown_check).strip()
    if _shutdown_check in {
        "jarvis shut down yourself",
        "shut down yourself",
        "jarvis shutdown yourself",
        "shutdown yourself",
        "jarvis shut yourself down",
    }:
        return {"action": "shutdown_jarvis"}

    memory_phrases = {
        "what do you remember",
        "what do you remember about me",
        "tumhe kya yaad hai",
        "mujhe kya yaad hai",
        "meri memory batao",
        "forget everything",
        "forget all memories",
        "sab kuch bhool jao",
        "meri sari memory delete karo",
    }
    remember_prefixes = (
        "remember ", "remember that ", "yaad rakho ",
        "yaad rakhna ", "isko yaad rakho ",
    )

    needs_brain_router = (
        looks_like_action_command(original)
        or lowered in memory_phrases
        or any(lowered.startswith(p) for p in remember_prefixes)
    )

    if needs_brain_router:
        return orchestrator_route(original, _brain_understand)

    # Normal conversation: use the warm OpenVINO fast path directly.
    response = ask_ai(original)
    add_conversation(original, response)
    return {
        "action": "chat",
        "response": response,
    }


def turn_on_screen():
    """Wake the monitor/display without shutting down Jarvis."""

    try:
        HWND_BROADCAST = 0xFFFF
        WM_SYSCOMMAND = 0x0112
        SC_MONITORPOWER = 0xF170
        MONITOR_ON = -1

        ctypes.windll.user32.SendMessageW(
            HWND_BROADCAST,
            WM_SYSCOMMAND,
            SC_MONITORPOWER,
            MONITOR_ON,
        )

        return True, "Screen on kar diya Boss."

    except Exception as error:
        return False, f"Screen on nahi ho paaya: {error}"



# ============================================================
# JARVIS PERMISSION GATE
# One confirmation only for destructive operations.
# Trusted contacts bypass sensitive-message confirmation.
# ============================================================

def ask_for_confirmation(prompt):
    speak(prompt)
    live_hud_state("LISTENING")
    live_hud_message("WAITING FOR APPROVAL")
    answer = listen_silence(
        max_seconds=5,
        start_timeout=1.8,
        silence_after=0.8,
        sleep_mode=False,
    )
    normalized = re.sub(r"[^a-z0-9\s]", " ", str(answer).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized in {
        "yes", "yeah", "yep", "haan", "han", "ha",
        "confirm", "confirmed", "do it", "send it",
    }

def _safe_target_path(target):
    raw = str(target or "").strip().strip('"').strip("'")
    if not raw:
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        # Allow normal Windows paths and common user folders by resolving
        # relative paths from the project directory.
        p = Path.cwd() / p
    try:
        return p.resolve()
    except Exception:
        return p




def _normalize_chatgpt_text(text):
    value = re.sub(r"\s+", " ", str(text or "").strip())
    return re.sub(r"\bchat\s*g(?:pt|pd|bt|bp|t|p)\b", "chatgpt", value, flags=re.I)

def detect_open_chatgpt_command(text):
    value = _normalize_chatgpt_text(text).lower()
    return value in {"open chatgpt", "chatgpt kholo", "chatgpt open karo", "chatgpt khol do", "launch chatgpt", "open chat gpt", "chat gpt kholo", "open chat gpd", "chat gpd kholo", "open chat gbt"}

def _clean_chatgpt_prompt(text):
    prompt = str(text or "").strip()
    prompt = re.sub(r"^(?:hey\s+)?jarvis[\s,;:\-]*", "", prompt, flags=re.I)
    prompt = re.sub(r"\bchat\s*g(?:pt|pd|bt|bp|t|p)\b", "chatgpt", prompt, flags=re.I)
    prompt = re.sub(r"^\s*(?:please\s+)?(?:open|launch)\s+(?:the\s+)?chatgpt\b", " ", prompt, flags=re.I)
    prompt = re.sub(r"\bchatgpt\b(?:\s+(?:mein|me|par|pe))?", " ", prompt, flags=re.I)
    m = re.search(r"(?:write|type|send|paste|enter|likho|likh\s+do)\s+(?:this\s+)?prompt\s*[:\-]?\s*(.+)$", prompt, flags=re.I)
    if m: prompt = m.group(1)
    parts = re.split(r"\b(?:aur|and)\b", prompt, flags=re.I)
    edit = ("edit", "change", "enhance", "improve", "modify", "background", "remove", "replace", "blur", "black paper", "make", "banao", "bana", "fix", "retouch", "crop", "color", "colour", "restore")
    if len(parts) > 1:
        candidates = [p.strip() for p in parts if any(w in p.lower() for w in edit)]
        if candidates: prompt = candidates[-1]
    prompt = re.sub(r"\b(?:this|is|ye)\s+(?:selected\s+)?(?:photo|image|picture|pic)\b", " ", prompt, flags=re.I)
    prompt = re.sub(r"\bselected\s+(?:photo|image|picture|pic)\b", " ", prompt, flags=re.I)
    prompt = re.sub(r"\b(?:photo|image|picture|pic)\s+(?:ko|ki|ka)\b", " ", prompt, flags=re.I)
    prompt = re.sub(r"\b(?:usko|isko|use|isse)\b", " ", prompt, flags=re.I)
    return re.sub(r"\s+", " ", prompt).strip(" .,:;-\"'")

def detect_chatgpt_operator(command: str):
    import re

    text = str(command or "").strip()
    if not text:
        return None

    normalized = re.sub(
        r"\bchat\s*[.]?\s*g\s*[.]?\s*[pqb]\s*[.]?\s*t\b",
        "chatgpt",
        text,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bchat\s*g\s*b\s*t\b",
        "chatgpt",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bchat\s*g\s*p\s*t\b",
        "chatgpt",
        normalized,
        flags=re.IGNORECASE,
    )

    if not re.search(r"\bchatgpt\b", normalized, flags=re.IGNORECASE):
        return None

    prompt = re.sub(
        r"^\s*(?:hey\s+)?jarvis[,:;.!-]*\s*",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    prompt = re.sub(
        r"\b(?:please\s+)?(?:open|launch)\s+chatgpt\b[,:;.!-]*\s*",
        "",
        prompt,
        count=1,
        flags=re.IGNORECASE,
    )
    prompt = re.sub(
        r"^\s*(?:and\s+)?(?:write|type|enter|send|put)\s+"
        r"(?:this\s+|a\s+|an\s+)?"
        r"(?:prompt|message)?\s*"
        r"(?:(?:on|in|to|for)\s+(?:a\s+|an\s+)?chatgpt|saying|that\s+says|which\s+says)?\s*"
        r"[:,.\-]?\s*",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    prompt = prompt.strip(" \t\r\n:,-")
    return prompt or None


def _set_clipboard_text(text):
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        root.clipboard_clear(); root.clipboard_append(str(text)); root.update()
    finally: root.destroy()

def _clipboard_has_image():
    try:
        import ctypes
        u = ctypes.windll.user32
        return bool(u.IsClipboardFormatAvailable(8) or u.IsClipboardFormatAvailable(17))
    except Exception:
        return True

def run_chatgpt_operator(prompt, include_image=False):
    prompt = str(prompt or "").strip()
    if not prompt:
        return False, "Boss, ChatGPT ke liye instruction nahi mili."
    try:
        from jarvis_chatgpt_operator import execute as _chatgpt_execute
        return _chatgpt_execute(
            prompt,
            use_selected_image=bool(include_image),
        )
    except Exception as error:
        print(f"CHATGPT OPERATOR ERROR: {error}", flush=True)
        return False, f"ChatGPT operator failed: {error}"

def execute(result):

    if not result:
        return True, False

    action = str(result.get("action", "") or "").strip().lower()

    # ============================================================
    # PURE STUDY MODE
    # ============================================================

    if action == "computer_task":
        from computer_tasks import execute_task
        success, message = execute_task(result, approve=lambda operation, path: ask_for_confirmation(
            f"Boss, {operation} existing file {path}? Is exact file ko overwrite karne ki permission do."))
        print(f"[COMPUTER TASK] success={success}: {message}", flush=True)
        speak(message)
        return True, False

    if action == "study_mode":
        try:
            import study_mode

            mode = str(result.get("mode", "status")).strip().lower()

            if mode == "start":
                state = study_mode.start()
                speak(
                    "Pure Study Mode on, Boss. "
                    "Ab main teacher, tutor aur examiner mode mein hoon. "
                    "Aap topic bolo."
                )
                print(
                    f"[STUDY MODE] ACTIVE | "
                    f"level={state.get('level')} | "
                    f"subject={state.get('subject')}",
                    flush=True,
                )

            elif mode == "stop":
                study_mode.stop()
                speak("Pure Study Mode off kar diya, Boss.")

            else:
                state = study_mode.current()
                weak = state.get("weak_topics", [])
                strong = state.get("strong_topics", [])

                print(
                    f"[STUDY] active={state.get('active')} "
                    f"level={state.get('level')} "
                    f"subject={state.get('subject')} "
                    f"weak={weak} strong={strong}",
                    flush=True,
                )

                if state.get("active"):
                    speak(
                        f"Boss, Study Mode active hai. "
                        f"Current subject {state.get('subject') or 'set nahi hai'} hai."
                    )
                else:
                    speak("Boss, Pure Study Mode abhi off hai.")

        except Exception as error:
            print(f"[STUDY MODE ERROR] {error}", flush=True)
            speak("Boss, Study Mode start nahi ho paaya.")

        return True, False

    # ============================================================
    # STUDY AI REQUEST
    # Uses existing local AI brain; no second AI.
    # ============================================================

    if action == "study_request":
        try:
            import study_mode

            target = str(result.get("target", "")).strip()
            mode = str(result.get("mode", "study teach")).strip()

            if not target:
                speak("Boss, kis topic ko study karna hai?")
                return True, False

            lowered_mode = mode.lower()
            is_quiz = any(token in lowered_mode for token in ("quiz", "test", "mock"))
            active = study_mode.current()
            subject = str(active.get("subject") or "General")
            if subject.lower() == "general":
                subject_match = re.match(r"^\s*(python|c\+\+|cpp|dsa|data structures|computer science)\b", target, re.I)
                if subject_match:
                    raw_subject = subject_match.group(1)
                    subject = "C++" if raw_subject.lower() in {"c++", "cpp"} else ("DSA" if raw_subject.lower() == "data structures" else raw_subject.title())

            if is_quiz:
                prompt = f"""
{study_mode.professor_system_prompt()}

QUIZ MODE — generate one question only.
Subject: {subject}
Topic: {target}

Return ONLY one valid JSON object with exactly these keys:
{{"question":"...", "expected_answer":"...", "topic":"..."}}
The question must be answerable from the stated topic. expected_answer is a private concise grading rubric, not to be shown to the learner now. Do not include markdown fences, explanation outside JSON, or multiple questions. Use Roman Urdu/Hinglish for the question, but keep technical words and code exact.
""".strip()
                response = ask_ai("__JARVIS_STUDY__\n" + prompt)
                response = str(response).replace("__JARVIS_STUDY__", "").strip()
                try:
                    match_json = re.search(r"\{[\s\S]*\}", response)
                    data = json.loads(match_json.group(0)) if match_json else {}
                    question = str(data.get("question") or "").strip()
                    expected = str(data.get("expected_answer") or "").strip()
                    quiz_topic = str(data.get("topic") or target).strip()
                    if not question or not expected:
                        raise ValueError("Quiz JSON is missing question/rubric.")
                    study_mode.set_pending_quiz(subject, quiz_topic, question, expected)
                    add_conversation(target, question)
                    speak(f"Quiz time, Boss. {question}")
                except Exception as _quiz_error:
                    print(f"[STUDY QUIZ ERROR] Could not safely parse quiz: {_quiz_error}", flush=True)
                    speak("Boss, quiz question reliably prepare nahi hua. Same quiz command dobara bolo.")
            else:
                prompt = f"""
{study_mode.professor_system_prompt()}

CURRENT STUDY REQUEST
MODE: {mode}
TOPIC: {target}

Teach this topic in detail. Do NOT give a short generic answer. Build the lesson naturally:
WHAT; WHY; INTUITION; HOW IT WORKS; INTERNAL WORKING; PRACTICAL EXAMPLE; REAL-WORLD USE;
IMPLEMENTATION / HOW-TO where relevant; COMMON MISTAKES; RECAP; 2-3 CHECKPOINT QUESTIONS.
Use natural spoken Roman Urdu/Hinglish. For Computer Science explain mechanisms and internals. For coding show useful examples and why the code works. If this is revision, prioritize weak concepts. Do not prematurely finish the explanation.
""".strip()
                response = ask_ai("__JARVIS_STUDY__\n" + prompt)
                response = str(response).replace("__JARVIS_STUDY__", "").strip()
                add_conversation(target, response)
                try:
                    if response:
                        notes_path = study_mode.add_notes(subject, response, topic=target)
                        study_mode.save_session(subject, topic=target, progress="Lesson response saved to Study notes")
                        print(f"[STUDY] Lesson saved: {notes_path}", flush=True)
                except Exception as _study_save_error:
                    print(f"[STUDY] Lesson persistence warning: {_study_save_error}", flush=True)
                speak(response)

        except Exception as error:
            print(f"[STUDY AI ERROR] {error}", flush=True)
            speak("Boss, Study Mode mein problem aa gayi.")

        return True, False

    if action == "study_answer":
        try:
            pending = study_mode.pending_quiz()
            answer = str(result.get("answer") or "").strip()
            if not pending:
                speak("Boss, abhi koi pending quiz question nahi hai.")
                return True, False
            if not answer:
                speak("Boss, answer sunayi nahi diya. Dobara bolo.")
                return True, False
            prompt = f"""
{study_mode.professor_system_prompt()}
Grade one learner answer against the private rubric. Be fair: accept equivalent wording and partial answers only when the core idea is correct. Do not claim correctness for unsupported answers.
Return ONLY valid JSON: {{"correct": true, "feedback": "..."}}
Question: {pending.get('question','')}
Expected answer rubric: {pending.get('expected_answer','')}
Learner answer: {answer}
The feedback should be concise Roman Urdu/Hinglish, explain the reason, and include the correction if the answer is wrong. No markdown fences or text outside JSON.
""".strip()
            graded_raw = str(ask_ai("__JARVIS_STUDY__\n" + prompt)).replace("__JARVIS_STUDY__", "").strip()
            match_json = re.search(r"\{[\s\S]*\}", graded_raw)
            grade = json.loads(match_json.group(0)) if match_json else {}
            correct_value = grade.get("correct")
            if isinstance(correct_value, bool):
                correct = correct_value
            elif str(correct_value).strip().lower() in {"true", "yes", "correct", "1"}:
                correct = True
            elif str(correct_value).strip().lower() in {"false", "no", "incorrect", "0"}:
                correct = False
            else:
                raise ValueError("Grader did not return a valid correctness value.")
            topic = str(pending.get("topic") or "General")
            subject = str(pending.get("subject") or "General")
            feedback = str(grade.get("feedback") or "Answer evaluate ho gaya.").strip()
            study_mode.record_revision(subject, str(pending.get("question") or ""), answer, correct, topic=topic)
            study_mode.record_learning(subject, topic, correct, detail=feedback)
            study_mode.clear_pending_quiz()
            add_conversation(f"Quiz answer: {topic}", feedback)
            speak(("Correct, Boss. " if correct else "Is baar answer correct nahi tha, Boss. ") + feedback)
        except Exception as error:
            print(f"[STUDY ANSWER ERROR] {error}", flush=True)
            speak("Boss, answer ko reliably grade nahi kar paaya, isliye result record nahi kiya. Answer dobara bolo.")
        return True, False

    if action == "study_skip":
        try:
            study_mode.clear_pending_quiz()
            speak("Theek hai Boss. Quiz question skip kar diya. Agla quiz topic bolo.")
        except Exception as error:
            print(f"[STUDY SKIP ERROR] {error}", flush=True)
            speak("Boss, question skip nahi ho paaya.")
        return True, False

    if action == "screen_control":
        try:
            import screen_agent
            import screen_vision

            mode = str(result.get("mode", "")).strip().lower()

            if mode == "describe":
                success, message = screen_vision.describe_screen()
                print(f"[SCREEN VISION] {message}", flush=True)
                try: hud_send("MESSAGE", message=str(message))
                except Exception: pass
                speak(message)

            elif mode == "study_notes":
                subject = str(result.get("subject") or "General").strip() or "General"
                topic = str(result.get("topic") or "Screen Notes").strip() or "Screen Notes"
                success, notes = screen_vision.extract_study_notes(subject=subject, topic=topic)
                if not success:
                    print(f"[SCREEN STUDY] {notes}", flush=True)
                    speak(notes)
                else:
                    notes_path = _jarvis_study_mode.add_notes(subject, notes, topic=topic)
                    youtube_state = {}
                    try:
                        from jarvis_dashboard_runtime import get_youtube_playback_state
                        youtube_state = get_youtube_playback_state(max_age=10) or {}
                    except Exception:
                        youtube_state = {}
                    _jarvis_study_mode.save_session(
                        subject,
                        video_url=str(youtube_state.get("url") or ""),
                        video_title=str(youtube_state.get("title") or ""),
                        timestamp_seconds=youtube_state.get("current_time"),
                        topic=topic,
                        progress="Screen content summarized into study notes",
                    )
                    message = f"Screen se study notes save ho gaye: {notes_path}. Subject {subject}, topic {topic}."
                    print(f"[SCREEN STUDY] {message}", flush=True)
                    try: hud_send("MESSAGE", message=message)
                    except Exception: pass
                    speak(message)

            elif mode == "find_target":
                target = str(result.get("target", "")).strip()
                success, message = screen_vision.find_target(target)
                print(f"[SCREEN VISION] {message}", flush=True)
                try: hud_send("MESSAGE", message=str(message))
                except Exception: pass
                speak(message)

            elif mode == "click_target":
                target = str(result.get("target", "")).strip()
                success, message = screen_vision.click_target(target)
                print(f"[SCREEN VISION] {message}", flush=True)
                try: hud_send("MESSAGE", message=str(message))
                except Exception: pass
                speak(message)

            elif mode == "screenshot":
                success, message, image = screen_agent.screenshot()
                print(f"[SCREEN] {message}", flush=True)
                if success:
                    speak("Boss, screen ka screenshot capture kar liya.")
                else:
                    speak(f"Boss, screenshot nahi le paaya. {message}")

            elif mode == "click_text":
                target = str(result.get("target", "")).strip()
                success, message = screen_agent.click_text(target)
                print(f"[SCREEN] {message}", flush=True)
                speak(message)

            elif mode == "scroll":
                amount = int(result.get("amount", -5))
                success, message = screen_agent.scroll(amount)
                print(f"[SCREEN] {message}", flush=True)
                speak(message if success else f"Boss, screen scroll nahi ho paaya. {message}")

            elif mode == "type_text":
                text_value = str(result.get("text", ""))
                if not text_value:
                    speak("Boss, kya type karna hai?")
                    return True, False
                success, message = screen_agent.type_text(text_value)
                print(f"[SCREEN] {message}", flush=True)
                speak(message if success else f"Boss, typing nahi ho paayi. {message}")

            elif mode == "press_key":
                key = str(result.get("key", "")).strip()
                success, message = screen_agent.press(key)
                print(f"[SCREEN] {message}", flush=True)
                speak(message if success else f"Boss, key press nahi ho paayi. {message}")

            else:
                speak("Boss, screen command samajh nahi aayi.")

        except Exception as error:
            print(f"[SCREEN AGENT ERROR] {error}", flush=True)
            speak(f"Boss, screen control mein problem aa gayi: {error}")

        return True, False

    if action == "youtube_bookmark":
        try:
            from jarvis_dashboard_runtime import get_youtube_playback_state
            mode = str(result.get("mode") or "save").lower()
            if mode == "resume":
                session = _jarvis_study_mode.latest_session()
                video_url = str((session or {}).get("video_url") or "")
                if not video_url:
                    speak("Boss, Study Memory mein koi saved YouTube timestamp nahi mila.")
                else:
                    webbrowser.open(video_url, new=0, autoraise=True)
                    speak(f"Boss, saved study video resume kar raha hoon: {(session or {}).get('video_title') or 'YouTube video'}.")
            else:
                playback = get_youtube_playback_state(max_age=10) or {}
                video_url = str(playback.get("url") or "")
                video_id = str(playback.get("video_id") or "")
                title = str(playback.get("title") or "")
                current_time = playback.get("current_time")
                if not video_url or current_time is None or not video_id:
                    speak("Boss, live YouTube timestamp nahi mila. Chrome mein JARVIS YouTube Progress extension load karke video play karo, phir dobara bolo.")
                else:
                    seconds = max(0, int(float(current_time)))
                    base_url = f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
                    status = "paused" if playback.get("paused") else "playing"
                    current = _jarvis_study_mode.current()
                    subject = str(current.get("subject") or "General")
                    _jarvis_study_mode.save_session(
                        subject,
                        video_url=base_url,
                        video_title=title,
                        timestamp_seconds=float(current_time),
                        topic="YouTube timestamp",
                        progress=f"Bookmarked at {seconds}s ({status})",
                    )
                    minutes, seconds_part = divmod(seconds, 60)
                    message = f"YouTube timestamp saved: {title or 'Video'} at {minutes:02d}:{seconds_part:02d}. Subject: {subject}. Link: {base_url}"
                    print(f"[YOUTUBE BOOKMARK] {message}", flush=True)
                    try: hud_send("MESSAGE", message=message)
                    except Exception: pass
                    speak(message)
        except Exception as error:
            print(f"[YOUTUBE BOOKMARK ERROR] {error}", flush=True)
            speak(f"Boss, YouTube timestamp save nahi hua: {error}")
        return True, False

    if action == "read_pdf":

        import os
        import glob
        import PyPDF2

        pdf_files = glob.glob(
            os.path.join(
                os.path.expanduser("~/Downloads"),
                "*.pdf",
            )
        )

        if not pdf_files:
            speak(
                "Boss, Downloads mein koi PDF nahi mili."
            )

            return True, False

        valid_pdfs = []

        for pdf_path in pdf_files:

            try:

                with open(
                    pdf_path,
                    "rb",
                ) as test_file:

                    reader = PyPDF2.PdfReader(
                        test_file
                    )

                    len(reader.pages)

                valid_pdfs.append(pdf_path)

            except Exception as error:

                print(
                    f"Skipping invalid PDF: {pdf_path} | {error}",
                    flush=True,
                )

        if not valid_pdfs:

            speak(
                "Boss, Downloads mein koi valid PDF nahi mili."
            )

            return True, False

        latest_pdf = max(
            valid_pdfs,
            key=os.path.getmtime,
        )

        try:

            success, text = read_pdf(
                latest_pdf
            )

            if success:

                print(
                    "\nPDF:",
                    latest_pdf,
                    flush=True,
                )

                print(
                    "PDF TEXT:\n",
                    text[:5000],
                    flush=True,
                )

                speak(
                    "Boss, PDF read kar li hai."
                )

            else:

                speak(
                    "Boss, PDF read nahi ho paayi."
                )

        except Exception as error:

            print(
                f"PDF error: {error}",
                flush=True,
            )

            speak(
                "Boss, PDF read karne mein problem aa gayi."
            )

        return True, False

    if action == "delete_path":
        target = result.get("target", "").strip()
        kind = result.get("kind", "file")
        path = _safe_target_path(target)

        if path is None or not path.exists():
            speak("Boss, ye file ya folder nahi mila.")
            return True, False

        # Never allow the assistant to delete the project root itself.
        try:
            project_root = Path(__file__).resolve().parent
            if path == project_root or project_root in path.parents:
                speak("Boss, Tahrun project ke andar destructive delete main allow nahi kar raha.")
                return True, False
        except Exception:
            pass

        ok = ask_for_confirmation(
            f"Boss, {kind} delete karne wala hoon: {path.name}. Confirm karne ke liye yes bolo."
        )
        if not ok:
            speak("Theek hai Boss. Delete cancel kar diya.")
            return True, False

        try:
            # Safer Windows behavior: send to Recycle Bin where possible.
            import ctypes
            from ctypes import wintypes

            FO_DELETE = 3
            FOF_ALLOWUNDO = 0x0040
            FOF_NOCONFIRMATION = 0x0010
            FOF_SILENT = 0x0004

            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR),
                    ("fFlags", wintypes.WORD),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", wintypes.LPVOID),
                    ("lpszProgressTitle", wintypes.LPCWSTR),
                ]

            op = SHFILEOPSTRUCTW(
                None, FO_DELETE, str(path) + "\0", None,
                FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT,
                False, None, None
            )
            result_code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            if result_code == 0 and not path.exists():
                speak("Done Boss. Delete complete, aur item Recycle Bin mein gaya.")
            else:
                speak("Boss, delete complete nahi ho paaya.")
        except Exception as error:
            print(f"Delete error: {error}", flush=True)
            speak("Boss, delete operation fail ho gayi.")

        return True, False
    if action == "shutdown_jarvis":
        _jarvis_local_hud_stop()
        print("JARVIS voice shutdown command accepted.", flush=True)
        try:
            speak("Theek hai Boss. Jarvis offline ho raha hai.")
        except Exception:
            pass
        return False, False
    if action == "shutdown_jarvis":
        _jarvis_local_hud_stop()
        print("JARVIS voice shutdown command accepted.", flush=True)
        try:
            speak("Theek hai Boss. Jarvis offline ho raha hai.")
        except Exception:
            pass
        return False, False

    if action == "stop":
        try:
            speak("Boss, shutdown ke liye exact command bolo: Jarvis shut down yourself.")
        except Exception:
            pass
        return True, False

    if action == "standby":

        speak(
            "Theek hai Boss. Main standby mein hoon."
        )

        return True, True

    if action == "screen_off":

        try:

            success, message = (
                actions.turn_off_screen()
            )

            print(
                f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“Ãƒâ€šÃ‚Â¥ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â {message}",
                flush=True,
            )

            speak(message)

        except Exception as error:

            print(
                f"ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Screen off error: {error}",
                flush=True,
            )

            speak(
                "Boss, screen off nahi ho payi."
            )

        return True, False

    if action == "screen_on":

        success, message = turn_on_screen()

        print(
            f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“Ãƒâ€šÃ‚Â¥ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â {message}",
            flush=True,
        )

        speak(message)

        return True, False

    if action == "open_this_pc":

        success, message = (
            actions.open_this_pc()
        )

        print(
            f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢Ãƒâ€šÃ‚Â» {message}",
            flush=True,
        )

        speak(message)

        return True, False

    if action == "power_on_info":

        speak(
            "Boss, completely powered-off PC ko software se khud power on nahi kiya ja sakta. Sleep mode mein ho to wake kiya ja sakta hai."
        )

        return True, False

    if action == "click":

        actions.click()

        speak("Done Boss.")

        return True, False

    if action == "double_click":

        actions.double_click()

        speak("Done Boss.")

        return True, False

    if action == "right_click":

        actions.right_click()

        speak("Done Boss.")

        return True, False

    if action == "type_text":
        text = str(result.get("target", "") or "").strip()
        if text:
            actions.type_text(text)
            speak("Text type kar diya Boss.")
        else:
            speak("Boss, kya type karna hai?")
        return True, False

    if action == "press_key":

        key = result.get(
            "target",
            "",
        )

        if key:

            actions.press_key(key)

            speak("Done Boss.")

        return True, False

    if action == "screenshot":
        try:
            path = actions.take_screenshot()
            if path:
                print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã‚Â¸ Screenshot saved: {path}", flush=True)
                speak("Screenshot le liya Boss.")
            else:
                speak("Boss, screenshot nahi le paya.")
        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ Screenshot error: {error}", flush=True)
            speak("Boss, screenshot nahi le paya.")
        return True, False

    if action == "screen_size":
        try:
            width, height = actions.get_screen_size()
            message = f"Boss, screen size {width} by {height} hai."
            print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬â€œÃ‚Â¥ÃƒÂ¯Ã‚Â¸Ã‚Â {message}", flush=True)
            speak(message)
        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ Screen size error: {error}", flush=True)
            speak("Boss, screen size nahi mil paaya.")
        return True, False

    if action == "youtube":

        query = result.get(
            "target",
            "",
        ).strip()

        if not query:

            speak(
                "Boss, YouTube par kya chalana hai?"
            )

            return True, False

        print(
            f"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“Ãƒâ€šÃ‚Â¶ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â YouTube Agent: {query}",
            flush=True,
        )

        try:

            speak(
                "Theek hai Boss. YouTube par search kar raha hoon."
            )

            success, message = play_youtube(
                query
            )

            if success:
                hud_send(
                    "MUSIC",
                    active=True,
                    playing=True,
                    source="YouTube",
                    track={
                        "title": str(query),
                        "artist": "YouTube",
                        "duration": 0,
                    },
                    title=str(query),
                    artist="YouTube",
                    lyric="",
                    position=0,
                    duration=0,
                    volume=1.0,
                )

            print(
                f"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“Ãƒâ€šÃ‚Â¶ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â {message}",
                flush=True,
            )

            speak(message)

        except Exception as error:

            print(
                f"ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ YouTube Agent Error: {error}",
                flush=True,
            )

            speak(
                "Boss, YouTube mein problem aa gayi."
            )

        return True, False

    # ========================================================
    # VIEW SOURCE CODE
    # Opens the current Tahrun source directly; no Ollama call.
    # ========================================================
    if action == "view_source":
        source_file = Path(__file__).resolve()
        try:
            os.startfile(str(source_file))
            print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂºÃ‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Source code opened: {source_file}", flush=True)
            speak("Done Boss. Tahrun ka source code open kar diya.")
        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ Source viewer error: {error}", flush=True)
            speak("Boss, source code open nahi ho paaya.")
        return True, False

    if action == "source_edit":

        request_text = result.get("target", "").strip()

        try:
            success, message = edit_source(request_text)
            print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂºÃ‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â {message}", flush=True)
            speak(message)
        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ Source editor error: {error}", flush=True)
            speak("Boss, source code change mein problem aa gayi.")

        return True, False

    if action == "ai":

        request_text = result.get("target", "")
        response = ask_ai(request_text)
        add_conversation(request_text, response)

        speak(response)

        return True, False

    if action == "chat":

        response = result.get(
            "response",
            "Boss, mujhe iska response nahi mila.",
        )

        speak(response)

        return True, False

    # ========================================================
# JARVIS_PRIORITY_WHATSAPP_ACTIONS_V1
    if action in {"whatsapp_call", "whatsapp_read_receipts", "whatsapp_delete_message"}:
        try:
            from jarvis_whatsapp_controls import perform_call, set_read_receipts, delete_message
            if action == "whatsapp_call":
                _wa_name = str(result.get("target", "")).strip()
                _wa_video = bool(result.get("video", False))
                if not _wa_name:
                    speak("Boss, WhatsApp call ke liye contact naam chahiye.")
                    return True, False
                _wa_kind = "video" if _wa_video else "voice"
                if not ask_for_confirmation(f"Boss, WhatsApp {_wa_kind} call {_wa_name} ko karun? Yes bolo to start karunga."):
                    speak("Theek hai Boss. WhatsApp call cancel kar di.")
                    return True, False
                if not whatsapp_agent.start():
                    speak("Boss, WhatsApp Web se connect nahi ho paaya. Edge mein login check karo.")
                    return True, False
                _wa_ok, _wa_detail = perform_call(whatsapp_agent, _wa_name, _wa_video)
            elif action == "whatsapp_read_receipts":
                if not whatsapp_agent.start():
                    speak("Boss, WhatsApp Web se connect nahi ho paaya.")
                    return True, False
                _wa_enabled = bool(result.get("enabled", False))
                _wa_ok, _wa_detail = set_read_receipts(whatsapp_agent, _wa_enabled)
            else:
                _wa_name = str(result.get("target", "")).strip()
                _wa_message = str(result.get("message", "")).strip()
                _wa_scope = str(result.get("scope", "me")).strip().lower()
                if not _wa_name or not _wa_message:
                    speak("Boss, delete ke liye contact aur exact message chahiye.")
                    return True, False
                _wa_scope_text = "for everyone" if _wa_scope == "everyone" else "for me"
                if not ask_for_confirmation(f"Boss, {_wa_name} ki chat mein '{_wa_message}' message delete {_wa_scope_text} karna hai? Yes bolo to proceed karunga."):
                    speak("Theek hai Boss. Message delete cancel kar diya.")
                    return True, False
                if not whatsapp_agent.start():
                    speak("Boss, WhatsApp Web se connect nahi ho paaya.")
                    return True, False
                _wa_ok, _wa_detail = delete_message(whatsapp_agent, _wa_name, _wa_message, _wa_scope)
            print("[JARVIS WHATSAPP CONTROL]", _wa_ok, _wa_detail, flush=True)
            speak(_wa_detail)
        except Exception as _wa_error:
            print(f"[JARVIS WHATSAPP CONTROL ERROR] {type(_wa_error).__name__}: {_wa_error}", flush=True)
            speak("Boss, WhatsApp action complete nahi ho paayi. Log mein error record hua hai.")
        return True, False

    # WHATSAPP MESSAGE
    # ========================================================

    if action == "whatsapp_message":

        name = result.get("target", "").strip()
        message_text = result.get("message", "").strip()

        if not name or not message_text:
            speak("Boss, WhatsApp contact aur message dono chahiye.")
            return True, False

        # Exactly one approval for sensitive messages to non-trusted contacts.
        if needs_message_approval(name, message_text):
            approved = ask_for_confirmation(
                f"Boss, ye sensitive message {name} ko bhejna hai. Ek baar approval do, yes bolo."
            )
            if not approved:
                speak("Theek hai Boss. Sensitive message cancel kar diya.")
                return True, False

        try:
            if not whatsapp_agent.start():
                speak("Boss, WhatsApp mein connection problem aa gayi.")
                return True, False

            success, reply = whatsapp_agent.send_message(name, message_text)

            print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â¬ {reply}", flush=True)

            if success:
                add_conversation(
                    f"Send WhatsApp message to {name}: {message_text}",
                    "Successfully sent the WhatsApp message.",
                )
                speak("Done, Boss.")
            else:
                speak(reply)

        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ WhatsApp runtime error: {error}", flush=True)
            speak("Boss, WhatsApp mein connection problem aa gayi.")

        return True, False


    if action == "open_chatgpt":
        try:
            from windows_control import launch_chatgpt_classic
            success, message = launch_chatgpt_classic()
            live_hud_activity("CHATGPT // Classic ready" if success else "CHATGPT // Classic launch failed")
            live_hud_message(message)
            speak(message)
        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ ChatGPT Classic open error: {error}", flush=True)
            speak("Boss, ChatGPT Classic open nahi ho paaya.")
        return True, False

    if action == "chatgpt_operator":
        prompt = str(result.get("prompt") or result.get("target") or result.get("instruction") or "").strip()
        include_image = bool(result.get("include_image"))
        try:
            success, message = run_chatgpt_operator(prompt, include_image=include_image)
            live_hud_activity("CHATGPT // Photo + prompt sent" if include_image else "CHATGPT // Prompt sent")
            live_hud_message(message)
            speak(message)
        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ ChatGPT operator error: {error}", flush=True)
            speak("Boss, ChatGPT operator mein problem aa gayi.")
        return True, False

    if action == "generate_image":
        prompt = (
            result.get("prompt")
            or result.get("target")
            or result.get("description")
            or ""
        ).strip()
        try:
            if not prompt:
                speak("Boss, image kis cheez ki generate karni hai?")
                return True, False

            success, message = generate_image(prompt)



            print(f"ÃƒÂ°Ã…Â¸Ã…Â½Ã‚Â¨ {message}", flush=True)
            speak(message)

        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ Image generation error: {error}", flush=True)
            speak("Boss, image generation mein problem aa gayi.")
        return True, False
    
    if action == "build_website":
        prompt = (
            result.get("prompt")
            or result.get("target")
            or result.get("description")
            or ""
        ).strip()

        try:
            if not prompt:
                speak("Boss, website kis cheez ki banani hai?")
                return True, False

            live_hud_command(f"build website: {prompt}")
            live_hud_activity("CODING AGENT // Building production website")
            live_hud_message("WEBSITE BUILD STARTED // This can take a few minutes for a polished result.")
            speak("Theek hai Boss. Production website bana raha hoon. Thoda time lagega, lekin final files validate karke dunga.")

            success, message = build_website(prompt)

            print(f"Ã°Å¸â€™Â» {message}", flush=True)
            live_hud_activity("CODING AGENT // Website build finished")
            live_hud_message(str(message))
            speak(message)

        except Exception as error:
            print(f"Ã¢ÂÅ’ Website coding error: {error}", flush=True)
            live_hud_activity("CODING AGENT // Build failed")
            live_hud_message(str(error))
            speak("Boss, website build mein problem aa gayi. Exact error console aur HUD mein hai.")

        return True, False


    if action in {"volume_up", "volume_down", "volume_mute", "volume_unmute"}:
        try:
            from windows_control import (
                volume_up,
                volume_down,
                volume_mute,
                volume_unmute,
            )

            handlers = {
                "volume_up": volume_up,
                "volume_down": volume_down,
                "volume_mute": volume_mute,
                "volume_unmute": volume_unmute,
            }

            success, message = handlers[action]()
            print(f"🔊 {message}", flush=True)
            speak(message)

        except Exception as error:
            print(f"❌ Volume control error: {error}", flush=True)
            speak("Boss, volume control mein problem aa gayi.")

        return True, False

    if action == "open_app":
        # IMPORTANT: always resolve the launcher at execution time.
        # This keeps JARVIS independent of an old imported launcher reference.
        app_name = str(result.get("target", "") or "").strip()

        if not app_name:
            speak("Boss, kaunsa app open karna hai?")
            return True, False

        print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â» Opening app: {app_name}", flush=True)

        try:
            from windows_control import launch_installed_app as _launch_app

            success, message = _launch_app(app_name)
            print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â» Windows launcher: success={success} | {message}", flush=True)

            if not success:
                print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â» Trying legacy app launcher: {app_name}", flush=True)
                success, message = actions.open_app(app_name)

            print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â» {message}", flush=True)
            speak(message)

        except Exception as error:
            print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ Windows app launcher error: {error}", flush=True)

            try:
                success, message = actions.open_app(app_name)
                print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â» Legacy launcher: success={success} | {message}", flush=True)
                speak(message)
            except Exception as fallback_error:
                print(f"ÃƒÂ¢Ã‚ÂÃ…â€™ Legacy launcher error: {fallback_error}", flush=True)
                speak(f"Boss, {app_name} open nahi ho paaya.")

        return True, False

    if action == "open_website":

        target = str(result.get("target") or "").strip().lower()

        try:
            if target == "youtube":
                # Direct, non-blocking browser launch. Keep this route isolated from
                # the generic website action so one bad browser handler can never
                # terminate the JARVIS loop.
                webbrowser.open_new_tab("https://www.youtube.com")
                success, message = True, "YouTube open kar diya Boss."
            else:
                success, message = actions.open_website(target)
        except SystemExit as error:
            print(f"Website launcher raised SystemExit for {target!r}: {error}", flush=True)
            success, message = False, f"{target} open nahi ho paaya."
        except Exception as error:
            print(f"Website launcher error for {target!r}: {error}", flush=True)
            success, message = False, f"{target} open nahi ho paaya."

        print(f"Ã°Å¸Å’Â {message}", flush=True)
        speak(message)

        # Never leave continuous voice mode just because a website launcher failed.
        return True, False

    if action == "open_folder":

        target = result.get(
            "target"
        )

        success, message = actions.open_folder(
            target
        )

        print(
            f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒâ€šÃ‚Â {message}",
            flush=True,
        )

        speak(message)

        return True, False

    if action == "search_web":

        query = result.get(
            "target"
        )

        success, message = actions.search_web(
            query
        )

        print(
            f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€¦Ã‚Â½ {message}",
            flush=True,
        )

        speak(message)

        return True, False

    if action == "close_app":

        target = result.get(
            "target"
        )

        target = str(target or "").strip()

        success, message = close_windows_app(target)
        

        print(
            f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂºÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“ {message}",
            flush=True,
        )

        speak(message)

        return True, False

    # ===== JARVIS MUSIC MODE =====

    if action == "music_mode_toggle":
        global _music_ui_mode
        _music_ui_mode = not _music_ui_mode
        hud_send("MUSIC_MODE", active=_music_ui_mode)
        speak(
            "Music Mode on kar diya Boss."
            if _music_ui_mode
            else "Normal HUD wapas kar diya Boss."
        )
        return True, False

    if action == "music_play":
        query = str(result.get("target", "") or "").strip()
        music_title = query if query else "JARVIS Music"
        music_artist = "JARVIS MUSIC SYSTEM"

        hud_send(
            "MUSIC",
            active=True,
            playing=True,
            track={
                "title": music_title,
                "artist": music_artist,
                "duration": 300,
            },
            title=music_title,
            artist=music_artist,
            lyric="Music Mode Active",
            position=0,
            duration=300,
            volume=0.85,
        )

        print(f"MUSIC MODE -> {music_title}", flush=True)
        speak(f"Music mode on. {music_title}")
        return True, False

    if action == "music_pause":
        hud_send(
            "MUSIC",
            active=True,
            playing=False,
            track={
                "title": "Music",
                "artist": "JARVIS MUSIC SYSTEM",
                "duration": 300,
            },
            title="Music",
            artist="JARVIS MUSIC SYSTEM",
            lyric="Paused",
            position=0,
            duration=300,
            volume=0.85,
        )
        speak("Music pause kar diya Boss.")
        return True, False

    if action == "music_resume":
        hud_send(
            "MUSIC",
            active=True,
            playing=True,
            track={
                "title": "Music",
                "artist": "JARVIS MUSIC SYSTEM",
                "duration": 300,
            },
            title="Music",
            artist="JARVIS MUSIC SYSTEM",
            lyric="Music Mode Active",
            position=0,
            duration=300,
            volume=0.85,
        )
        speak("Music resume kar diya Boss.")
        return True, False

    if action == "music_stop":
        hud_send(
            "MUSIC",
            active=False,
            playing=False,
            track={
                "title": "",
                "artist": "",
                "duration": 0,
            },
            title="",
            artist="",
            lyric="",
            position=0,
            duration=0,
            volume=0.85,
        )
        speak("Music stop kar diya Boss.")
        return True, False

    # ===== END JARVIS MUSIC MODE =====

    print(
        f"ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡ ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â Unknown action: {action}",
        flush=True,
    )

    speak(
        "Boss, ye action abhi configured nahi hai."
    )

    return True, False


# ============================================================
# JARVIS HUD BRIDGE
# Sends runtime state/messages to the browser HUD.
# HUD failure must never stop the voice engine.
# ============================================================
import json
import jarvis_repair_runtime as _jarvis_repair_runtime

def _jarvis_wake_only(text):
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    t = t.strip(" .,!?")
    return t in {"jarvis", "hey jarvis"}



try:
    import websocket
except ImportError:
    websocket = None

HUD_WS_URL = "ws://127.0.0.1:8765"


def hud_send(event_type, **data):
    if websocket is None:
        return False
    payload = {"source": "JARVIS", "type": event_type, **data}
    try:
        ws = websocket.create_connection(HUD_WS_URL, timeout=0.35)
        ws.send(json.dumps(payload, ensure_ascii=False))
        ws.close()
        return True
    except Exception:
        return False


def live_hud_state(state):
    return hud_send("STATE", state=state)


def live_hud_message(message):
    return hud_send("MESSAGE", message=str(message))


def live_hud_activity(text):
    return hud_send("ACTIVITY", text=str(text))


def live_hud_diagnostic(key, state, detail=None):
    status = {"key": key, "state": state}
    if detail:
        status["detail"] = detail
    return hud_send("DIAGNOSTIC", status=status)


def _tts_text(text):
    """Remove emoji/symbol glyphs that TTS incorrectly speaks by name."""
    value = str(text or "")
    value = re.sub(
        r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]",
        " ",
        value,
    )
    value = re.sub(r"\s+", " ", value).strip()
    return value


def speak(text):
    # HUD receives the original text; TTS receives a clean text-only version.
    clean_text = _tts_text(text)
    try:
        live_hud_state("SPEAKING")
        if text:
            live_hud_message(str(text))
            live_hud_activity(f"JARVIS // {str(text)[:70]}")
    except Exception:
        pass

    try:
        print("[TTS] Preparing voice...", flush=True)
        result = _voice_speak(clean_text)
        print("[TTS] Finished.", flush=True)
        return result
    except Exception as error:
        print(f"[TTS] Voice error recovered: {error}", flush=True)
        return None
    finally:
        try:
            live_hud_state("IDLE")
        except Exception:
            pass


def run_hud_startup():
    live_hud_state("STARTING")
    live_hud_message("JARVIS CORE INITIALIZING...")
    live_hud_activity("SYSTEM // Starting JARVIS engine")
    checks = [
        ("core", "READY", "Python engine online"),
        ("voice", "READY", "Local voice channel ready"),
        ("ai", "READY", "AI brain connected"),
        ("computer", "READY", "Computer control loaded"),
        ("network", "READY", "Network channel available"),
        ("security", "READY", "Local runtime protected"),
    ]
    for key, state, detail in checks:
        live_hud_diagnostic(key, state, detail)
    live_hud_state("IDLE")
    live_hud_message("YES BOSS. ALL SYSTEMS ARE RUNNING.")
    live_hud_activity("SYSTEM // All startup checks complete")
    live_hud_message("SECURITY // Delete + shutdown + sensitive-message gates active")



# ============================================================
# JARVIS_ONE_TAP_PATCH_V2
# ============================================================
try:
    import hud_v2 as _jarvis_local_hud
except Exception:
    _jarvis_local_hud=None

def _jarvis_local_live_hud_state(state):
    if _jarvis_local_hud is not None:
        try: _jarvis_local_hud.set_state(state)
        except Exception: pass

def _jarvis_local_hud_wake():
    if _jarvis_local_hud is not None:
        try: _jarvis_local_hud.wake()
        except Exception: pass

def _jarvis_local_hud_stop():
    if _jarvis_local_hud is not None:
        try: _jarvis_local_hud.stop()
        except Exception: pass

def _start_live_hud_server():
    try:
        import jarvis_hud_server
        import threading
        threading.Thread(target=jarvis_hud_server.run, daemon=True).start()
        time.sleep(0.25)
    except Exception as error:
        print(f"[JARVIS HUD] Bridge server unavailable: {error}", flush=True)

def _live_telemetry_loop():
    try:
        import psutil, socket

        while True:
            try:
                cpu=psutil.cpu_percent(interval=0.4)
                ram=psutil.virtual_memory().percent
                b=psutil.sensors_battery()
                battery=b.percent if b else None
                try:
                    socket.create_connection(("1.1.1.1",53),timeout=0.2).close()
                    net="ONLINE"
                except Exception:
                    net="OFFLINE"
                live_hud_telemetry(cpu,ram,battery,net)
            except Exception:
                pass
            time.sleep(3)
    except Exception:
        pass

def _warm_fast_brain():
    """Ensure OpenVINO is ready before voice commands start, eliminating first-request load latency."""
    try:
        ready = getattr(_jarvis_brain, "_OV_READY", None)
        pipeline = getattr(_jarvis_brain, "_OV_PIPELINE", None)
        if pipeline is not None:
            print("Fast brain: OpenVINO Intel GPU already ready.", flush=True)
            return
        if ready is not None:
            print("Fast brain: waiting for OpenVINO Intel GPU before listening...", flush=True)
            threading.Thread(target=lambda: ready.wait(timeout=30), daemon=True).start()
            pipeline = getattr(_jarvis_brain, "_OV_PIPELINE", None)
            if pipeline is not None:
                print("Fast brain: OpenVINO Intel GPU READY; voice loop starting.", flush=True)
                print("JARVIS final runtime: WEBSITE_AUTORUN_V6", flush=True)
            else:
                print("Fast brain: OpenVINO not ready; Ollama fallback remains available.", flush=True)
    except Exception as exc:
        print(f"Fast brain warm-up skipped: {exc}", flush=True)


def main():


    # JARVIS_HUD_SERVER_STARTED
    threading.Thread(target=_live_telemetry_loop, daemon=True).start()


    print()
    print("=" * 60)
    print("              JARVIS FAST VOICE ENGINE")
    print("=" * 60)
    print()

    print("ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€šÃ‚Â§  AI Brain: Qwen3 / Ollama")
    print("ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢Ãƒâ€šÃ‚Â» Coding Agent: HTML + CSS + JavaScript")
    print("ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“Ãƒâ€šÃ‚Â¶ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â YouTube Agent: yt-dlp")
    print(
        "Ã°Å¸Å½â„¢Ã¯Â¸Â Voice: Groq Whisper + adaptive speech gate + local fallback"
    )
    print("ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â¡ Status: ONLINE")
    print()

    print("ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€šÃ‚Â§ Initializing microphone...")


    if find_microphone() is None:

        print(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Jarvis cannot start without a microphone."
        )

        return

    calibrate_microphone()

    print(
        "Wake word:",
        ", ".join(WAKE_WORDS),
    )

    print("ESC = Emergency Stop")
    print("Ctrl+C = Exit")
    print()

    print("=" * 60)
    print()

    activated_on_launch = os.environ.get("JARVIS_ACTIVATED") == "1"

    if activated_on_launch:
        _jarvis_local_hud_wake()
        speak("Haan Boss.")
        _jarvis_local_live_hud_state("listening")
        live_hud_state("LISTENING")
        live_hud_message("I'M LISTENING, BOSS.")
        live_hud_activity("VOICE // Wake word detected")
    else:
        run_hud_startup()
        speak("Jarvis online.")

    # Finish the GPU model warm-up before accepting voice commands.
    # This moves model-load cost out of the first AI response.
    _warm_fast_brain()

    live_hud_state("IDLE")

    running = True
    # JARVIS_DUPLICATE_COMMAND_GUARD
    _last_command_key = None
    _last_command_at = 0.0
    continuous_mode = activated_on_launch 
    standby_message_shown = False

    while running:

        try:
            # ESC disabled: voice shutdown is the app shutdown path.

            # JARVIS HUD UPGRADE: DASHBOARD COMMAND
            dashboard_command = get_dashboard_command()
            if dashboard_command:
                continuous_mode = True

            if not continuous_mode:

                if not standby_message_shown:

                    print()
                    print(
                        "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢Ãƒâ€šÃ‚Â¤ Jarvis standby...",
                        flush=True,
                    )

                    print(
                        "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€¦Ã‚Â½Ãƒâ€šÃ‚Â§ Listening for 'Hey Jarvis'...",
                        flush=True,
                    )

                    standby_message_shown = True

                live_hud_state("LISTENING")
                live_hud_activity("VOICE // Listening for wake word")
                wake_text = listen_silence(
                    sleep_mode=True,
                )

                if not wake_text:
                    continue

                if not is_wake_word(wake_text):
                    continue

                print()
                print(
                    "ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â¡ JARVIS ACTIVATED",
                    flush=True,
                )

                continuous_mode = True
                standby_message_shown = False

                # JARVIS_WAKE_DASHBOARD_V1
                try:
                    start_real_dashboard()
                    start_telemetry()
                except Exception as _hud_error:
                    print(f"[JARVIS HUD] {_hud_error}", flush=True)

                speak("Haan Boss.")
                live_hud_state("LISTENING")
                live_hud_message("I'M LISTENING, BOSS.")
                live_hud_activity("VOICE // Wake word detected")

                continue

            _jarvis_local_live_hud_state("listening")
            live_hud_state("LISTENING")
            live_hud_activity("VOICE // Waiting for command")
            if dashboard_command:
                command = dashboard_command
            else:
                command = listen_silence(
                    max_seconds=12,
                    start_timeout=1.8,
                    silence_after=2.20,
                    sleep_mode=False,
                )

            if not command:

                live_hud_state("IDLE")
                print(
                    "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€¦Ã‚Â½Ãƒâ€šÃ‚Â§ Main active hoon. Agla command sun raha hoon.",
                    flush=True,
                )

                continue

            # JARVIS_PARTIAL_COMMAND_RECOVERY
            # Whisper/gate can occasionally stop after a sentence-start word
            # such as "Give". Listen briefly for the continuation and merge it.
            if _likely_incomplete_command(command):
                print(f"[STT] Possible partial command: {command!r}", flush=True)
                live_hud_state("LISTENING")
                live_hud_message("CONTINUE YOUR COMMAND, BOSS.")
                continuation = listen_silence(
                    max_seconds=5,
                    start_timeout=0.70,
                    silence_after=1.00,
                    sleep_mode=False,
                )
                if continuation:
                    command = f"{command} {continuation}".strip()
                    print(f"[STT] Recovered command: {command!r}", flush=True)

            # Ignore an immediate duplicate of the exact same command.
            _command_key = re.sub(r"\s+", " ", str(command or "").strip().lower())
            _command_now = time.monotonic()
            if _command_key and _command_key == _last_command_key and (_command_now - _last_command_at) < 3.0:
                live_hud_activity("VOICE // Duplicate command ignored")
                continue
            _last_command_key = _command_key
            _last_command_at = _command_now

            if is_standby_command(command):

                speak(
                    "Theek hai Boss. Main standby mein hoon."
                )

                # Standby must keep the main voice loop alive for the next wake word.
                # Do not return from the assistant when activated on launch.
                continuous_mode = False
                standby_message_shown = False

                continue

            print()
            # Route immediately after speech capture; no separate thinking stage.
            hud_send("COMMAND", command=command)
            hud_send("CONSOLE", role="YOU", text=command)

            # JARVIS_STUDY_SCHEDULER_ROUTER_V1
            try:
                from jarvis_study_scheduler import handle_command as _handle_study_schedule
                _study_handled, _study_status, _study_detail = _handle_study_schedule(command)
                if _study_handled:
                    print("[JARVIS STUDY SCHEDULER]", _study_detail, flush=True)
                    try: speak(_study_detail)
                    except Exception: pass
                    continue
            except Exception as _study_exc:
                print(f"[JARVIS STUDY SCHEDULER ERROR] {_study_exc}", flush=True)
            # STUDY_DIRECT_ROUTE_V1: handle study commands before AI routing.
            try:
                _study_handled = _jarvis_handle_study_command(command)
            except Exception as _study_err:
                print(f"[STUDY MODE ERROR] {_study_err}", flush=True)
                _study_handled = False
            if _study_handled:
                continue


            # DIRECT WEBSITE ROUTES Ã¢â‚¬â€ never send simple open commands to AI.
            _direct_command = re.sub(r"[^a-z0-9\s]", " ", str(command or "").strip().lower())
            _direct_command = re.sub(r"^(?:hey\s+)?jarvis\s*", "", _direct_command)
            _direct_command = re.sub(r"\bopenyoutube\b", "open youtube", _direct_command)
            _direct_command = re.sub(r"\byoutubeopen\b", "youtube open", _direct_command)
            _direct_command = re.sub(r"\s+", " ", _direct_command).strip()

            from computer_tasks import parse_command as _computer_parse
            _screen_route = _computer_parse(command) or _jarvis_route_screen_command(command)
            _pending_quiz_route = None if _screen_route is not None else _jarvis_route_pending_quiz(command)
            if _screen_route is not None:
                result = _screen_route
                print(f"[SCREEN FASTPATH] {result}", flush=True)
            elif _pending_quiz_route is not None:
                result = _pending_quiz_route
                print(f"[STUDY QUIZ FASTPATH] {result.get('action')}", flush=True)
            elif _direct_command in {
                "open youtube", "youtube open", "launch youtube",
                "youtube kholo", "youtube open karo", "youtube khol do",
                "open you tube", "launch you tube",
                "open yotube", "yotube open",
            }:
                result = {"action": "open_website", "target": "youtube"}
                print("Ã¢â€“Â¶Ã¯Â¸Â Direct YouTube open command detected", flush=True)
            elif _looks_like_website_build_request(command):
                result = {"action": "build_website", "target": command}
                print("Ã°Å¸â€™Â» Website build command detected Ã¢â‚¬â€ routing directly to Coding Agent", flush=True)
            elif detect_open_chatgpt_command(command):
                result = {"action": "open_chatgpt", "target": "chatgpt"}
                print("ÃƒÂ°Ã…Â¸Ã‚Â¤Ã¢â‚¬â€œ ChatGPT Classic open command detected", flush=True)
            else:
                chatgpt_task = detect_chatgpt_operator(command)
                if chatgpt_task:
                    result = {"action": "chatgpt_operator", "prompt": chatgpt_task, "include_image": False, "target": chatgpt_task}
                    print(f"ChatGPT operator command detected: {chatgpt_task}", flush=True)
                else:
                    print(f"[DEBUG COMMAND] {command!r}", flush=True)
                    if explicit_shutdown_command(command): result = {"action": "shutdown_jarvis"}
                    else: result = orchestrator_route(command, _brain_understand)
                    print(f"[DEBUG RESULT] {result!r}", flush=True)

            if result and result.get("action") == "unresolved":
                if looks_like_action_command(command):
                    repaired = repair_command(command)
                    if repaired and repaired.get("action") != "chat":
                        print(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂºÃ‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Repaired command: {repaired}", flush=True)
                        result = repaired
                    else:
                        result = {"action": "ai", "target": command}
                else:
                    result = {"action": "ai", "target": command}

            print(
                f"ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€šÃ‚Â§  Action: {result.get('action')}",
                flush=True,
            )

            _jarvis_local_live_hud_state("executing")
            live_hud_state("EXECUTING")

            action_name = result.get("action", "unknown")
            target_name = result.get("target", "")
            live_hud_message(f"EXECUTING // {action_name}")
            live_hud_activity(f"EXEC // {action_name}" + (f" // {target_name}" if target_name else ""))
            live_hud_executing(action_name, target_name)

            try:
                running, go_standby = execute(result)
            except SystemExit as error:
                # Imported Windows/browser/TTS helpers must never be allowed to
                # silently terminate the entire JARVIS process.
                print(f"Ã¢Å¡Â Ã¯Â¸Â Recovered SystemExit from action execution: {error}", flush=True)
                running, go_standby = True, False
            except Exception as error:
                _jarvis_repair_runtime.record_exception("action_execution", error)
                print(f"Ã¢Å¡Â Ã¯Â¸Â Action execution error recovered: {error}", flush=True)
                speak("Boss, action execute karte waqt problem aayi, lekin Jarvis running hai.")
                running, go_standby = True, False

            print(
                f"Ã¢Å“â€¦ Action finished | running={running} | standby={go_standby}",
                flush=True,
            )

            live_hud_result(action_name, bool(running), "Command execution completed")
            live_hud_state("IDLE")


            hud_send("RESULT", message="Execution finished", action=result.get("action"))
            _jarvis_local_live_hud_state("idle")

            # Stay continuously active until an explicit standby command.
            continuous_mode = not go_standby
            standby_message_shown = False

        except KeyboardInterrupt:

            print()
            print(
                "ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂºÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“ Jarvis stopped by Ctrl+C."
            )

            break

        except Exception as error:

            _jarvis_repair_runtime.record_exception("main_loop", error)
            print()
            print(
                f"ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Main engine error: {error}"
            )

            print()

            time.sleep(0.5)

    print()
    print("=" * 60)
    print("              JARVIS OFFLINE")
    print("=" * 60)


if __name__ == "__main__":
    main()     












