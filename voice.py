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


async def generate_voice(text, output_file):
    def _generate():
        client = Cartesia(api_key=os.environ["CARTESIA_API_KEY"])
        response = client.tts.generate(
            model_id="sonic-3.5",
            transcript=text,
            voice="6b02ffe5-e3cb-48c0-a023-c72f85953375",
            output_format={
                "container": "wav",
                "encoding": "pcm_s16le",
                "sample_rate": 44100,
            },
        )
        response.write_to_file(str(output_file))

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
        text.encode("utf-8")
    ).hexdigest()[:16]

    safe_slug = "".join(
        c if c.isalnum() else "_"
        for c in text[:40]
    )

    output_file = CACHE_DIR / f"{safe_slug}_{content_hash}.wav"

    try:
        if not output_file.exists():
            asyncio.run(generate_voice(text, output_file))

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
