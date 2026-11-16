"""Pure-Python regression tests; no WhatsApp, sound card, or API keys needed."""
import time
import unittest
from jarvis_call_conversation import CallConfig, ContinuousCallSession


class SessionTests(unittest.TestCase):
    def make_session(self, *, inputs, delay=0.0, connected=None, greeting="Hello Boss"):
        heard = list(inputs)
        spoken = []
        events = []
        state = connected if connected is not None else {"on": True}

        def listen(_timeout):
            if heard:
                return heard.pop(0)
            state["on"] = False
            return None

        def brain(text, history):
            if delay:
                time.sleep(delay)
            return f"Answer to: {text} (prior={len(history)})"

        session = ContinuousCallSession(
            is_connected=lambda: state["on"],
            listen_utterance=listen,
            reply_to=brain,
            speak_to_call=spoken.append,
            greeting=greeting,
            config=CallConfig(
                filler_after_seconds=0.05,
                thought_timeout_seconds=2.0,
                listen_poll_seconds=0.01,
            ),
            log_event=lambda k, d: events.append(k),
        )
        return session, spoken, events

    def test_greeting_and_multiple_turns_without_wake_word(self):
        s, spoken, events = self.make_session(inputs=["Hi", "Chrome kholo", "Search YouTube"])
        self.assertEqual(s.run(), 3)
        self.assertEqual(spoken, [
            "Hello Boss",
            "Answer to: Hi (prior=0)",
            "Answer to: Chrome kholo (prior=1)",
            "Answer to: Search YouTube (prior=2)",
        ])
        self.assertEqual(len(s.history), 3)
        self.assertEqual(events.count("HEARD"), 3)

    def test_no_greeting_on_ring(self):
        s, spoken, events = self.make_session(inputs=[], connected={"on": False})
        self.assertEqual(s.run(), 0)
        self.assertEqual(spoken, [])
        self.assertIn("NOT_CONNECTED", events)

    def test_natural_filler_only_when_brain_is_slow(self):
        s, spoken, events = self.make_session(inputs=["What is the time"], delay=0.18)
        self.assertEqual(s.run(), 1)
        self.assertEqual(spoken[0], "Hello Boss")
        self.assertTrue(spoken[1].startswith("Hmm Boss"))
        self.assertTrue(spoken[2].startswith("Answer to:"))
        self.assertEqual(events.count("FILLER"), 1)

    def test_silent_turn_does_not_generate_fake_answer(self):
        s, spoken, _events = self.make_session(inputs=["", None, "Boss"])
        self.assertEqual(s.run(), 1)
        self.assertEqual(len(spoken), 2)

    def test_brain_failure_returns_short_error_not_crash(self):
        s, spoken, events = self.make_session(inputs=["Hi"])
        def fail(_text, _history):
            raise RuntimeError("test error")
        s.reply_to = fail
        self.assertEqual(s.run(), 1)
        self.assertTrue(spoken[-1].startswith("Boss, ek technical issue"))
        self.assertIn("THINK_DONE", events)


if __name__ == "__main__":
    unittest.main()
