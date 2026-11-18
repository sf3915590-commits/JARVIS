from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAT = "chat-" + "a" * 40
AGENT = "agent-" + "b" * 40


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class RemoteIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        os.environ.update(
            JARVIS_CHAT_TOKEN=CHAT,
            JARVIS_AGENT_TOKEN=AGENT,
            JARVIS_RELAY_DB=str(Path(cls.tempdir.name) / "relay.sqlite3"),
            JARVIS_RESULT_WAIT_SECONDS="5",
            JARVIS_RELAY_URL="http://127.0.0.1:1",
        )
        cls.relay = load_module("jarvis_relay_test", ROOT / "relay.py")
        cls.relay.init_db()
        cls.server = cls.relay.RelayServer(("127.0.0.1", 0), cls.relay.Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tempdir.cleanup()

    def request(self, path, token=None, body=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method="POST" if data else "GET")
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.status, json.loads(response.read())

    def test_health_and_authentication(self):
        self.assertEqual(self.request("/healthz")[1], {"ok": True})
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/mcp", body={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(error.exception.code, 401)

    def test_tools_list_and_sensitive_confirmation(self):
        _, listed = self.request(
            "/mcp", CHAT, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        self.assertEqual([x["name"] for x in listed["result"]["tools"]], ["jarvis_status", "jarvis_ask", "jarvis_command"])
        self.relay._agent_seen()
        _, denied = self.request(
            "/mcp",
            CHAT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "jarvis_command", "arguments": {"command": "turn on microphone"}},
            },
        )
        self.assertTrue(denied["result"]["isError"])
        self.assertIn("Explicit confirmation", denied["result"]["content"][0]["text"])

    def test_end_to_end_ask_through_agent(self):
        self.relay._agent_seen()

        def fake_agent():
            _, packet = self.request("/agent/next?wait=2", AGENT)
            task = packet["task"]
            self.assertEqual(task["name"], "jarvis_ask")
            self.request("/agent/result", AGENT, {"id": task["id"], "result": {"reply": "verified reply", "provider": "jarvis"}})

        agent = threading.Thread(target=fake_agent, daemon=True)
        agent.start()
        _, response = self.request(
            "/mcp",
            CHAT,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "jarvis_ask", "arguments": {"question": "test question"}},
            },
        )
        agent.join(3)
        self.assertFalse(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["reply"], "verified reply")


if __name__ == "__main__":
    unittest.main()
