"""Continuous, callback-based WhatsApp AI conversation loop for JARVIS.

This module intentionally does NOT select Windows/WhatsApp audio devices and
does NOT dial or verify a call. The existing call controller owns those
operations and should invoke `run()` ONLY after a verified connection.

The live AI-call controller must inject:
* is_connected(): bool -- verified ongoing call state
* listen_utterance(timeout_seconds): str | None -- speech endpoint + STT,
  from the WhatsApp remote audio, never the normal wake-word microphone
* reply_to(text, history): str -- JARVIS brain and authorised command router
* speak_to_call(text): None -- blocking TTS playback to CABLE Input

There is deliberately no automatic import of Tahrun.py here: importing the
desktop entry point would start unrelated processes, microphones and HUDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Thread
import logging
import time
from typing import Callable, Sequence

LOG = logging.getLogger(__name__)

# Rotate these, rather than saying one predictable phrase on every turn.
FILLERS = (
    "Hmm Boss, ek second.",
    "Achha, samajh gayi. Dekh rahi hoon.",
    "Haan Boss, batati hoon.",
)


@dataclass(frozen=True)
class CallConfig:
    # The 2-3-second user target is for *starting* speech, not sleeping 2s.
    # A natural acknowledgement can start while the brain is still working.
    filler_after_seconds: float = 1.35
    thought_timeout_seconds: float = 18.0
    listen_poll_seconds: float = 1.0
    error_backoff_seconds: float = 0.15
    history_turns: int = 8


def default_greeting(scheduled_prompt: str | None = None) -> str:
    """First line to speak after connection is actually verified."""
    if scheduled_prompt and scheduled_prompt.strip():
        return scheduled_prompt.strip()
    hour = datetime.now().hour
    when = "Good morning" if 5 <= hour < 12 else ("Good evening" if 17 <= hour < 23 else "Hello")
    return f"{when} Boss! Kya haal chaal? Batao, kya chal raha hai?"


class ContinuousCallSession:
    """One call, many turns. No wake word required inside a verified call.

    Callbacks use only the existing session's audio paths. `speak_to_call`
    must block until playback is finished; this prevents self-feedback and
    overlapping Cartesia voices. `listen_utterance` should implement VAD,
    STT and echo suppression and return a FULL utterance or None on silence.
    """

    def __init__(
        self,
        *,
        is_connected: Callable[[], bool],
        listen_utterance: Callable[[float], str | None],
        reply_to: Callable[[str, Sequence[tuple[str, str]]], str],
        speak_to_call: Callable[[str], None],
        greeting: str | Callable[[], str] | None = None,
        config: CallConfig | None = None,
        log_event: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.is_connected = is_connected
        self.listen_utterance = listen_utterance
        self.reply_to = reply_to
        self.speak_to_call = speak_to_call
        self.greeting = greeting
        self.config = config or CallConfig()
        self.log_event = log_event
        self.history: list[tuple[str, str]] = []
        self._filler_index = 0

    def _emit(self, kind: str, **info: object) -> None:
        if self.log_event is not None:
            try:
                self.log_event(kind, dict(info))
            except Exception:
                LOG.exception("Call telemetry handler failed")
        LOG.info("AI CALL %s %s", kind, info)

    def _say(self, line: str) -> None:
        if line and self.is_connected():
            self._emit("SPEAKING", characters=len(line))
            self.speak_to_call(line)

    def _greet(self) -> None:
        if callable(self.greeting):
            line = self.greeting()
        else:
            line = self.greeting or default_greeting()
        self._emit("GREETING")
        self._say(line)

    def _next_filler(self) -> str:
        result = FILLERS[self._filler_index % len(FILLERS)]
        self._filler_index += 1
        return result

    def _think(self, text: str) -> str | None:
        # Work on a daemon thread to make long LLM calls cancellable from
        # the call controller's point of view. Only one turn runs at a time.
        results: Queue[tuple[bool, str]] = Queue(maxsize=1)
        history_snapshot = tuple(self.history[-self.config.history_turns :])
        started = time.monotonic()

        def run_brain() -> None:
            try:
                answer = str(self.reply_to(text, history_snapshot) or "").strip()
                results.put((True, answer))
            except Exception as exc:
                LOG.exception("AI call brain failed")
                results.put((False, f"{type(exc).__name__}: {exc}"))

        Thread(target=run_brain, name="JarvisCallBrain", daemon=True).start()
        deadline = started + self.config.thought_timeout_seconds
        filler_time = started + self.config.filler_after_seconds
        filler_spoken = False

        while self.is_connected():
            now = time.monotonic()
            if now >= deadline:
                self._emit("BRAIN_TIMEOUT", seconds=round(now - started, 3))
                return "Boss, response mein dikkat aa rahi hai. Dobara bolna."
            try:
                success, answer = results.get(timeout=min(0.08, max(0.001, deadline - now)))
                self._emit("THINK_DONE", seconds=round(time.monotonic() - started, 3))
                return answer if success else "Boss, ek technical issue aaya hai. Dobara bolna."
            except Empty:
                pass

            if not filler_spoken and time.monotonic() >= filler_time and results.empty():
                # An acknowledgement should not race a finished result.
                # It plays over the same validated CABLE audio path.
                filler_spoken = True
                self._emit("FILLER")
                self._say(self._next_filler())
        return None

    def run(self, *, max_turns: int | None = None) -> int:
        """Run until call ends. Return processed-utterance count.

        Run in the existing call-controller worker, not the desktop wake
        listener. The controller still owns hangup and resource cleanup.
        """
        if not self.is_connected():
            self._emit("NOT_CONNECTED")
            return 0
        self._greet()
        processed = 0
        consecutive_errors = 0
        while self.is_connected() and (max_turns is None or processed < max_turns):
            self._emit("LISTENING")
            try:
                utterance = self.listen_utterance(self.config.listen_poll_seconds)
                consecutive_errors = 0
            except (TimeoutError, Empty):
                # Silence/receive timeouts are normal; do not end the call.
                continue
            except Exception as exc:
                consecutive_errors += 1
                self._emit("LISTEN_ERROR", error=type(exc).__name__)
                # Avoid a busy loop; controller should repair lost audio if
                # repeated errors indicate a disconnected audio stream.
                if consecutive_errors >= 5:
                    self._emit("INPUT_UNAVAILABLE")
                    break
                time.sleep(self.config.error_backoff_seconds)
                continue

            if not self.is_connected():
                break
            text = str(utterance or "").strip()
            if not text:
                continue
            processed += 1
            self._emit("HEARD", text=text)
            answer = self._think(text)
            if answer and self.is_connected():
                self.history.append((text, answer))
                self.history = self.history[-self.config.history_turns :]
                self._say(answer)
        self._emit("ENDED", turns=processed)
        return processed
