import hashlib
import asyncio
import os
from cartesia import Cartesia
import threading
import asyncio
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from playsound3 import playsound
from config import VOICE

try:
    import keyboard
except Exception:
    keyboard = None

CACHE_DIR = Path(__file__).resolve().parent / "voice_cache"
CACHE_DIR.mkdir(exist_ok=True)

VOICE_NAME = VOICE or "en-IN-PrabhatNeural"

_current_sound = None
_barge_in = False
_barge_stop = None


def resolve_cartesia_api_keys():
    """Return configured Cartesia keys in primary-then-fallback order."""
    names = ("CARTESIA_API_KEY", "CARTESIA_API_KEY_FALLBACK")
    values = {name: os.environ.get(name, "").strip() for name in names}
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            for name in names:
                try:
                    if not values[name]:
                        values[name] = winreg.QueryValueEx(key, name)[0].strip()
                except OSError:
                    pass
    except (ImportError, OSError):
        pass
    try:
        from dotenv import dotenv_values
        config = dotenv_values(Path(__file__).resolve().parent / ".env", interpolate=False)
        for name in names:
            if not values[name]:
                values[name] = (config.get(name) or "").strip()
    except ImportError:
        pass
    keys = []
    for name in names:
        key = values[name]
        if key and key not in keys:
            keys.append(key)
            os.environ[name] = key
    return keys


def resolve_cartesia_api_key():
    """Compatibility helper returning the primary key."""
    keys = resolve_cartesia_api_keys()
    return keys[0] if keys else ""


async def generate_voice(text, output_file):
    def _generate():
        keys = resolve_cartesia_api_keys()
        if not keys:
            raise RuntimeError("CARTESIA_API_KEY is not configured")
        last_error = None
        for index, key in enumerate(keys):
            try:
                client = Cartesia(api_key=key, timeout=25.0, max_retries=0)
                response = client.tts.generate(
                    model_id="sonic-3.5",
                    transcript=text,
                    voice="47f3bbb1-e98f-4e0c-92c5-5f0325e1e206",
                    output_format={
                        "container": "wav",
                        "encoding": "pcm_s16le",
                        "sample_rate": 44100,
                    },
                )
                response.write_to_file(str(output_file))
                print("[TTS] Cartesia selected voice generated using " + ("primary" if index == 0 else "fallback") + " key.", flush=True)
                return
            except Exception as exc:
                last_error = exc
                status = getattr(exc, "status_code", None)
                if status is None:
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                # Only exhaustion triggers key rotation. Other failures should be
                # surfaced immediately instead of hiding auth/config problems.
                if status != 402 or index == len(keys) - 1:
                    raise
        raise last_error

    await asyncio.to_thread(_generate)


def stop_speaking():
    global _current_sound, _barge_stop

    try:
        if _current_sound is not None and _current_sound.is_alive():
            _current_sound.stop()
    except Exception:
        pass

    _current_sound = None


def was_interrupted():
    return _barge_in


def clear_interrupted():
    global _barge_in
    _barge_in = False


_BARGE_IN_RMS_THRESHOLD = 3200.0
_BARGE_IN_BLOCKS_NEEDED = 7
_PLAYBACK_GRACE_PERIOD = 0.8  # ~320ms of sustained speech-like sound


def _barge_in_looks_like_speech(audio):
    """Spectral speech-vs-noise shape check (same idea as Tahrun.py's
    listen_silence()), kept self-contained here so voice.py has no new
    cross-file dependency."""
    if audio.size < 64:
        return False
    x = audio - float(np.mean(audio))
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1.0 / 16000.0)
    speech_band = float(spectrum[(freqs >= 300.0) & (freqs <= 3400.0)].sum())
    low_band = float(spectrum[(freqs >= 60.0) & (freqs < 300.0)].sum())
    speech_ratio = speech_band / (low_band + 1.0)
    signs = np.signbit(x)
    zcr = float(np.mean(signs[1:] != signs[:-1])) if len(x) > 1 else 0.0
    return speech_ratio >= 0.9 and zcr >= 0.015


def _detect_barge_in(stop_event):
    global _barge_in

    speech_run = 0

    try:
        with sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="int16",
            blocksize=1280,
        ) as stream:

            playback_start = time.monotonic()
            while not stop_event.is_set():
                data, _ = stream.read(1280)
                if time.monotonic() - playback_start < _PLAYBACK_GRACE_PERIOD:
                    continue

                audio = np.asarray(data).reshape(-1).astype(np.float32)
                rms = float(np.sqrt(np.mean(audio * audio))) if audio.size else 0.0

                if rms >= _BARGE_IN_RMS_THRESHOLD and _barge_in_looks_like_speech(audio):
                    speech_run += 1
                else:
                    speech_run = max(0, speech_run - 1)

                if speech_run >= _BARGE_IN_BLOCKS_NEEDED:
                    _barge_in = True
                    stop_event.set()
                    stop_speaking()
                    break

    except Exception as error:
        print(f"Barge-in detector error: {error}", flush=True)


def speak(text):
    global _current_sound, _barge_in, _barge_stop

    if not text:
        return

    print(f"🔊 Jarvis: {text}", flush=True)

    content_hash = hashlib.sha256(
        ("cartesia_sonic35_47f3bbb1-e98f-4e0c-92c5-5f0325e1e206:" + text).encode("utf-8")
    ).hexdigest()[:16]

    safe_slug = "".join(
        c if c.isalnum() else "_"
        for c in text[:40]
    )

    output_file = CACHE_DIR / f"{safe_slug}_{content_hash}.wav"

    try:
        if not output_file.exists():
            coroutine = generate_voice(text, output_file)
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coroutine)
            else:
                # Voice may be requested from JARVIS's active asyncio loop.
                # Run Cartesia's coroutine on a short-lived worker loop and
                # propagate errors to the existing offline TTS fallback.
                result = {}
                def _run_voice_job():
                    try:
                        result['value'] = asyncio.run(coroutine)
                    except BaseException as exc:
                        result['error'] = exc
                worker = threading.Thread(target=_run_voice_job, daemon=True)
                worker.start()
                worker.join(timeout=35)
                if worker.is_alive():
                    raise TimeoutError('Cartesia TTS worker timed out')
                if 'error' in result:
                    raise result['error']

        stop_speaking()

        _barge_in = False
        _barge_stop = threading.Event()

        _current_sound = playsound(str(output_file), block=False)

        detector = threading.Thread(
            target=_detect_barge_in,
            args=(_barge_stop,),
            daemon=True,
        )
        detector.start()

        while _current_sound is not None and _current_sound.is_alive():
            if keyboard is not None:
                try:
                    if keyboard.is_pressed("esc"):
                        print("🛑 Speech interrupted.", flush=True)
                        stop_speaking()
                        break
                except Exception:
                    pass

            if _barge_in:
                print("🎤 Barge-in detected.", flush=True)
                break

            time.sleep(0.05)

        if _barge_stop is not None:
            _barge_stop.set()

    except Exception as error:
        print(f"Voice error: {error}", flush=True)
        _current_sound = None
        if _barge_stop is not None:
            _barge_stop.set()
        raise
