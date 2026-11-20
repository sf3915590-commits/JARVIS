"""Regression tests for explicit WhatsApp call routing; no calls are placed."""
import unittest
from jarvis_whatsapp_controls import parse_command


class WhatsAppCallRoutingTests(unittest.TestCase):
    def test_boss_voice_call(self):
        self.assertEqual(
            parse_command("Jarvis, WhatsApp voice call Boss"),
            {"action": "whatsapp_call", "target": "Boss", "video": False},
        )

    def test_hey_jarvis_prefix(self):
        self.assertEqual(
            parse_command("Hey Jarvis, WhatsApp voice call Boss"),
            {"action": "whatsapp_call", "target": "Boss", "video": False},
        )

    def test_non_call_chat_not_routed(self):
        self.assertIsNone(parse_command("Can you explain WhatsApp calls?"))


if __name__ == "__main__":
    unittest.main()
