"""Safety regression tests that do not import audio, Windows, or AI providers."""
import ast
import re
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "Tahrun.py"


def isolated_function(name):
    source = SOURCE.read_text(encoding="utf-8-sig")
    module = ast.parse(source, filename=str(SOURCE))
    nodes = [n for n in module.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(nodes) != 1:
        raise AssertionError(f"Expected one function {name}, got {len(nodes)}")
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace = {"re": re}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace[name]


class ExplicitStandbyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standby = staticmethod(isolated_function("is_standby_command"))
        cls.partial = staticmethod(isolated_function("_likely_incomplete_command"))

    def test_explicit_standby_commands(self):
        for text in (
            "standby", "go to standby", "Jarvis, go into standby",
            "Hey Jarvis, standby!", "so jao", "rest karo",
            "stop listening", "go to sleep",
        ):
            with self.subTest(text=text):
                self.assertTrue(self.standby(text))

    def test_generic_and_unrelated_speech_cannot_trigger_standby(self):
        for text in (
            "", "wait", "cancel", "cancel command", "ruk jao",
            "bas karo", "Jarvis, wait", "Jarvis, what's the weather?",
            "I want to cancel the download", "don't go to standby",
            "standby mode is not working", "sleep mode kaise kaam karta hai",
        ):
            with self.subTest(text=text):
                self.assertFalse(self.standby(text))

    def test_partial_command_speech_recovery(self):
        for text in ("Give", "search", "Please!", "open"):
            with self.subTest(text=text):
                self.assertTrue(self.partial(text))
        self.assertFalse(self.partial("show the forecast"))
        self.assertFalse(self.partial("play music"))

    def test_ai_standby_routing_cannot_bypass_explicit_command(self):
        source = SOURCE.read_text(encoding="utf-8-sig")
        self.assertIn(
            'result.get("action") == "standby" and not is_standby_command(command)',
            source,
        )


if __name__ == "__main__":
    unittest.main()
