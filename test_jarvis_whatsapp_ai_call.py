"""Isolated tests; no Windows audio, WhatsApp login or API keys needed."""
import time
import unittest
from types import SimpleNamespace
from jarvis_whatsapp_ai_call import AudioBridge, CallController


class FakePA:
    def get_loopback_device_info_generator(self):
        return iter([
            {"name": "Headphones (2- Airdopes 212) [Loopback]", "index": 1},
            {"name": "CABLE Input (VB-Audio Virtual Cable) [Loopback]", "index": 2},
        ])


class AudioSelectionTests(unittest.TestCase):
    def test_matches_verified_whatsapp_speaker(self):
        from unittest.mock import patch
        bridge = AudioBridge.__new__(AudioBridge)
        bridge.p = FakePA()
        bridge.output = None
        with patch.object(AudioBridge, "_cable_output", return_value={"name": "CABLE Input"}):
            with patch.dict("os.environ", {"JARVIS_CALL_LOOPBACK": ""}):
                bridge.select_devices()
        self.assertEqual(bridge.incoming["index"], 2)

    def test_explicit_override(self):
        from unittest.mock import patch
        bridge = AudioBridge.__new__(AudioBridge)
        bridge.p = FakePA()
        with patch.object(AudioBridge, "_cable_output", return_value={"name": "CABLE Input"}):
            with patch.dict("os.environ", {"JARVIS_CALL_LOOPBACK": "Headphones (2- Airdopes 212) [Loopback]"}):
                bridge.select_devices()
        self.assertEqual(bridge.incoming["index"], 1)


class ThoughtTests(unittest.TestCase):
    def make_controller(self, brain):
        c = CallController(agent=object(), brain=brain, status=lambda *_: None)
        c.tick = lambda: None
        c._filler_audio = b"cached"
        said = []
        c.say = lambda text, prepared=None: said.append((text, prepared))
        return c, said

    def test_transient_whatsapp_ui_timeout_is_diagnostic_not_fatal(self):
        messages = []
        controller = CallController(
            agent=object(),
            ui=SimpleNamespace(sample=lambda: (_ for _ in ()).throw(TimeoutError())),
            status=messages.append,
        )
        controller.dialed = True
        controller.connected = True
        controller.tick()  # one flaky DOM read should not kill a connected call
        self.assertTrue(any("probe timed out" in line for line in messages))

    def test_repeated_unverified_ui_times_out_closed(self):
        from jarvis_whatsapp_ai_call import CallError
        controller = CallController(
            agent=object(),
            ui=SimpleNamespace(sample=lambda: (_ for _ in ()).throw(TimeoutError())),
            status=lambda *_: None,
        )
        controller.dialed = True
        controller.connected = True
        controller._unknown_since = time.monotonic() - 4
        with self.assertRaises(CallError):
            controller.tick()

    def test_fast_answer_has_no_filler(self):
        c, said = self.make_controller(SimpleNamespace(reply=lambda text: "Hi Boss"))
        c.think_and_say("Hello")
        self.assertEqual(said, [("Hi Boss", None)])

    def test_slow_answer_has_one_filler(self):
        def respond(_):
            time.sleep(1.6)
            return "Ji Boss"
        c, said = self.make_controller(SimpleNamespace(reply=respond))
        c.think_and_say("Tell me")
        self.assertEqual(said[0], ("Hmm Boss, ek second.", b"cached"))
        self.assertEqual(said[1], ("Ji Boss", None))


if __name__ == "__main__":
    unittest.main()
