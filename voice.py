import hashlib
import os
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import requests

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


# Cartesia's normal SDK `generate(...).write_to_file(...)` first waits for the
# *entire* utterance to be synthesized and saved.  That was the source of the
# long silent gap before playback.  Keep the request as an HTTP byte stream so
# the sound device receives the first audio chunk as soon as Cartesia returns it.
_CARTESIA_BYTES_URL = "https://api.cartesia.ai/tts/bytes"
_CARTESIA_VERSION = "2026-08-14"
_SAMPLE_RATE = 44100
_VOICE_ID = "6b02ffe5-e3cb-48c0-a023-c72f85953375"


class _StreamingPlayback:
    """Small stop-compatible handle used by stop_speaking and barge-in."""

    def __init__(self):
        self._stopped = threading.Event()

    def stop(self):
        self._stopped.set()

    def is_alive(self):
        return not self._stopped.is_set()


def _cartesia_keys():
    """Yield the configured primary key, then an optional fallback key.

    Older installs only have CARTESIA_API_KEY, so that remains fully supported.
    The alternate names make the primary/fallback setup explicit without ever
    printing credentials to the terminal.
    """
    names = (
        "CARTESIA_API_KEY",
        "CARTESIA_PRIMARY_API_KEY",
        "CARTESIA_FALLBACK_API_KEY",
        "CARTESIA_API_KEY_FALLBACK",
    )
    seen = set()
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value and value not in seen:
            seen.add(value)
            yield name, value


def _open_cartesia_stream(text):
    payload = {
        "model_id": "sonic-3.5",
        "transcript": text,
        "voice": _VOICE_ID,
        "output_format": {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": _SAMPLE_RATE,
        },
    }
    last_error = None
    for key_name, api_key in _cartesia_keys():
        started = time.perf_counter()
        try:
            response = requests.post(
                _CARTESIA_BYTES_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Cartesia-Version": _CARTESIA_VERSION,
                    "Content-Type": "application/json",
                },
                json=payload,
                stream=True,
                timeout=(5, 30),
            )
            if response.ok:
                print(
                    f"[TTS] Cartesia stream connected via {key_name} "
                    f"in {time.perf_counter() - started:.2f}s.",
                    flush=True,
                )
                return response
            last_error = RuntimeError(f"Cartesia HTTP {response.status_code}: {response.text[:200]}")
            response.close()
        except requests.RequestException as error:
            last_error = error
    if not any(_cartesia_keys()):
        raise RuntimeError("No Cartesia API key found in environment variables.")
    raise RuntimeError(f"Cartesia could not start audio stream: {last_error}")


def _play_pcm_chunks(chunks, cache_file=None):
    """Play raw PCM as it arrives; optionally retain it for a zero-latency replay."""
    global _current_sound
    handle = _StreamingPlayback()
    _current_sound = handle
    first_audio_at = None
    started = time.perf_counter()
    cache_handle = open(cache_file, "wb") if cache_file else None
    try:
        with sd.RawOutputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=0,
        ) as output:
            for chunk in chunks:
                if handle._stopped.is_set():
                    break
                if keyboard is not None:
                    try:
                        if keyboard.is_pressed("esc"):
                            print("🛑 Speech interrupted.", flush=True)
                            handle.stop()
                            break
                    except Exception:
                        pass
                if _barge_in:
                    print("🎤 Barge-in detected.", flush=True)
                    handle.stop()
                    break
                if not chunk:
                    continue
                if first_audio_at is None:
                    first_audio_at = time.perf_counter()
                    print(
                        f"[TTS] First Cartesia audio in {first_audio_at - started:.2f}s.",
                        flush=True,
                    )
                output.write(chunk)
                if cache_handle:
                    cache_handle.write(chunk)
    finally:
        if cache_handle:
            cache_handle.close()
        handle.stop()
        if _current_sound is handle:
            _current_sound = None


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

    # Raw PCM can be sent straight to sounddevice.  A cached reply still uses
    # the same low-overhead player, with no network synthesis at all.
    output_file = CACHE_DIR / f"{safe_slug}_{content_hash}.pcm"

    try:
        stop_speaking()

        _barge_in = False
        _barge_stop = threading.Event()

        detector = threading.Thread(
            target=_detect_barge_in,
            args=(_barge_stop,),
            daemon=True,
        )
        detector.start()

        if output_file.exists() and output_file.stat().st_size:
            print("[TTS] Playing cached Cartesia audio.", flush=True)
            def cached_chunks():
                with open(output_file, "rb") as cached:
                    while data := cached.read(8192):
                        yield data
            _play_pcm_chunks(cached_chunks())
        else:
            response = _open_cartesia_stream(text)
            try:
                _play_pcm_chunks(response.iter_content(chunk_size=8192), output_file)
            finally:
                response.close()

        if _barge_stop is not None:
            _barge_stop.set()

    except Exception as error:
        print(f"Voice error: {error}", flush=True)
        _current_sound = None
        if _barge_stop is not None:
            _barge_stop.set()
