"""Tests for explicitly-verified phone call commands; all side effects mocked."""
import unittest
from datetime import datetime, timezone
from jarvis_call_tools import CallTools, classify, call_hangup_command, normalize
from jarvis_whatsapp_ai_call import parse_command


class CallToolClassifierTests(unittest.TestCase):
    def test_hangup_variants(self):
        for phrase in ("Jarvis, cut the call.", "Cut the call.", "Hang up",
                       "call band karo", "call cut kar do", "end this call",
                       "Please cut the call", "Jarvis cut the call please"):
            with self.subTest(phrase=phrase):
                self.assertTrue(call_hangup_command(phrase))
                self.assertEqual(parse_command(phrase), {"action": "whatsapp_ai_end"})

    def test_mention_of_hangup_is_not_a_command(self):
        for phrase in ("What if I say cut the call?", "Tell me how to end this call",
                       "Never cut the call", "Cut the call and delete files"):
            with self.subTest(phrase=phrase):
                self.assertFalse(call_hangup_command(phrase))

    def test_open_chrome(self):
        for phrase in ("Open Chrome", "Jarvis, open Chrome", "Chrome open karo",
                       "chrome khol do", "launch Google Chrome",
                       "Jarvis could you open Chrome please",
                       "Now open Chrome"):
            with self.subTest(phrase=phrase):
                self.assertEqual(classify(phrase), ("app", "chrome"))

    def test_named_app_and_website(self):
        self.assertEqual(classify("Please open notepad"), ("app", "notepad"))
        self.assertEqual(classify("Open VS Code"), ("app", "vscode"))
        self.assertEqual(classify("Open YouTube"), ("site", "youtube"))
        self.assertEqual(classify("Open downloads folder"), ("folder", "downloads"))

    def test_unbounded_actions_are_not_executed(self):
        for text in ("run powershell -enc example", "delete all files",
                     "transfer 1000 rupees", "open chrome and delete files",
                     "execute arbitrary Python"):
            self.assertIsNone(classify(text))

    def test_time_and_news_intents(self):
        self.assertEqual(classify("What is the time now?"), ("time", ""))
        self.assertEqual(classify("Please tell me the exact time now"), ("time", ""))
        self.assertEqual(classify("Aaj ki date batao"), ("date", ""))
        self.assertEqual(classify("Latest news")[0], "news")
        self.assertEqual(classify("Search the web for Mars launch")[0], "search")


class CallBrainDispatchTests(unittest.TestCase):
    def test_open_app_routes_to_real_tool_without_model_hallucination(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        from jarvis_whatsapp_ai_call import CallBrain
        calls = []
        fake_model = SimpleNamespace(chat=lambda **kw: self.fail('model should not execute app action'))
        with patch.dict(sys.modules, {
            'ollama': SimpleNamespace(Client=lambda **kw: fake_model)
        }):
            brain = CallBrain(tools=CallTools(
                app_launcher=lambda name: (calls.append(name) or True, 'ok')
            ))
        reply = brain.reply('Jarvis, open Chrome')
        self.assertEqual(calls, ['chrome'])
        self.assertIn('open kar diya', reply)


class ToolExecutionTests(unittest.TestCase):
    def setUp(self):
        self.apps = []
        self.sites = []
        self.calls = []
        self.tools = CallTools(
            app_launcher=lambda name: (self.apps.append(name) or True, "ok"),
            site_opener=lambda url: (self.sites.append(url) or True, "ok"),
            folder_opener=lambda name: (True, "ok"),
            news_search=lambda query: self.calls.append(query) or [
                {"title": "Relevant headline", "url": "https://example.com/news"}
            ],
            text_search=lambda query: [{"title": "Search result", "href": "https://example.com"}],
            clock=lambda: datetime(2026, 11, 17, 12, 34, 56, tzinfo=timezone.utc),
        )

    def test_real_action_results_not_merely_llm_promise(self):
        message = self.tools.handle("Open Chrome")
        self.assertEqual(self.apps, ["chrome"])
        self.assertIn("open kar diya", message)

    def test_site_from_fixed_allowlist(self):
        self.tools.handle("Open YouTube")
        self.assertEqual(self.sites, ["https://www.youtube.com"])

    def test_live_time_exact(self):
        response = self.tools.handle("What is the time now?")
        self.assertIn("12:34:56 PM", response)

    def test_headlines_come_from_retrieval(self):
        response = self.tools.handle("Latest news")
        self.assertIn("Relevant headline", response)
        self.assertEqual(len(self.calls), 1)

    def test_no_hallucinated_news_when_search_fails(self):
        tool = CallTools(news_search=lambda q: [])
        self.assertIn("verified results nahi mile", tool.handle("Latest news"))

    def test_unhandled_chat_goes_to_brain(self):
        self.assertIsNone(self.tools.handle("How are you today?"))


if __name__ == "__main__":
    unittest.main()
