from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import re
import os
from pathlib import Path
from urllib.parse import urlparse

# ============================================================
# JARVIS WHATSAPP WEB AGENT — EXISTING EDGE / CDP MODE
# ============================================================
# IMPORTANT:
# - Does NOT launch a new Chromium/Edge browser.
# - Does NOT create a new WhatsApp profile.
# - Connects to the already-running Edge instance on port 9222.
# - The Edge instance must have been started with:
#     --remote-debugging-port=9222
# - The browser/session stays alive. JARVIS only disconnects
#   from Playwright; it does NOT close Edge.
# ============================================================

CDP_URL = "http://127.0.0.1:9222"
WHATSAPP_URL = "https://web.whatsapp.com/"


class WhatsAppAgent:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.started = False

    # ========================================================
    # START / ATTACH
    # ========================================================

    def start(self):
        if self.started and self.page:
            try:
                if not self.page.is_closed():
                    return True
            except Exception:
                pass

        try:
            self.playwright = sync_playwright().start()

            # Attach to the EXISTING Edge instance.
            endpoint = CDP_URL
            active_port = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data/DevToolsActivePort"
            try:
                port, route = active_port.read_text().splitlines()[:2]
                if port == "9222" and route.startswith("/devtools/browser/"):
                    endpoint = "ws://127.0.0.1:" + port + route
            except (OSError, ValueError):
                pass
            try:
                self.browser = self.playwright.chromium.connect_over_cdp(endpoint, timeout=15000)
            except Exception as exc:
                if endpoint != CDP_URL or "404" not in str(exc):
                    raise
                # edge://inspect serves a WebSocket endpoint without HTTP discovery.
                print("WhatsApp: requesting access to existing Edge; allow its debugging prompt if shown.", flush=True)
                self.browser = self.playwright.chromium.connect_over_cdp(
                    "ws://127.0.0.1:9222/devtools/browser", timeout=30000
                )

            contexts = self.browser.contexts
            if not contexts:
                raise RuntimeError("Existing Edge ka browser context nahi mila.")

            whatsapp_pages = []
            for context in contexts:
                for page in context.pages:
                    try:
                        if urlparse(page.url).hostname == "web.whatsapp.com":
                            whatsapp_pages.append((context, page))
                    except Exception:
                        pass
            if len(whatsapp_pages) != 1:
                raise RuntimeError("Keep exactly one WhatsApp Web tab open in the main Edge session; no new tab was opened.")
            self.context, self.page = whatsapp_pages[0]

            self.started = True

            print(
                "[WhatsApp] attached to existing Edge (CDP 9222).",
                flush=True,
            )
            return True

        except Exception as error:
            print(
                f"[WhatsApp] Edge attach error: {error}",
                flush=True,
            )
            self._disconnect_only()
            return False

    # ========================================================
    # WAIT UNTIL READY
    # ========================================================

    def wait_until_ready(self, timeout=15):
        if not self.page:
            return False, "WhatsApp Web connection nahi hai."

        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                if self.page.is_closed():
                    return False, "WhatsApp Web tab band ho gaya."

                search = self.page.get_by_role(
                    "textbox",
                    name=re.compile(
                        r"Search or start a new chat",
                        re.IGNORECASE,
                    ),
                ).first

                if search.is_visible(timeout=700):
                    return True, "WhatsApp Web ready."

                # Fallback: WhatsApp may expose textboxes without the expected aria name.
                boxes = self.page.get_by_role("textbox")
                count = boxes.count()

                for index in range(min(count, 8)):
                    try:
                        box = boxes.nth(index)
                        if box.is_visible(timeout=200):
                            return True, "WhatsApp Web ready."
                    except Exception:
                        continue

                body_text = ""
                try:
                    body_text = self.page.locator("body").inner_text(
                        timeout=500
                    ).lower()
                except Exception:
                    pass

                login_words = [
                    "scan qr",
                    "use whatsapp on your computer",
                    "link with phone number",
                    "link as companion device",
                ]

                if any(word in body_text for word in login_words):
                    return (
                        False,
                        "Boss, WhatsApp Web login nahi hai. Pehle Edge mein WhatsApp connect karo.",
                    )

            except Exception:
                pass

            time.sleep(0.35)

        return (
            False,
            "Boss, WhatsApp Web ready hone mein zyada time lag raha hai.",
        )

    # ========================================================
    # SEARCH CONTACT
    # ========================================================

    def search_contact(self, name):
        if not self.page:
            return False, "WhatsApp connection nahi hai."
        name = name.strip()
        if not name:
            return False, "Contact name missing."
        try:
            ready, message = self.wait_until_ready(timeout=10)
            if not ready:
                return False, message
            search = None
            for selector in (
                'input[role="textbox"][data-tab="3"]',
                '#side [contenteditable="true"][role="textbox"]',
                '#side [contenteditable="true"][data-tab]',
                '#side input[placeholder*="Search" i]',
                '#side [contenteditable="true"]',
                '[data-testid="chat-list-search"]',
                'div[role="textbox"][aria-label*="Search" i]',
                'div[contenteditable="true"][data-tab="3"]',
            ):
                boxes = self.page.locator(selector)
                for i in range(boxes.count()):
                    box = boxes.nth(i)
                    if box.is_visible():
                        search = box
                        break
                if search is not None:
                    break
            if search is None:
                return False, "WhatsApp search box nahi mila."
            search.fill(name)
            self.page.wait_for_timeout(900)
            return True, "Search completed."
        except Exception as error:
            return False, f"Search failed: {error}"

    # ========================================================
    # OPEN CONTACT - EXACT MATCH ONLY
    # ========================================================

    def open_contact(self, name):
        name = name.strip()
        success, message = self.search_contact(name)
        if not success:
            return False, message
        try:
            results = self.page.locator('#pane-side span[title]')
            matches = []
            for i in range(results.count()):
                item = results.nth(i)
                title = item.get_attribute("title") or ""
                if title.strip().casefold() == name.casefold() and item.is_visible():
                    matches.append(item)
            if len(matches) != 1:
                return False, f"Exact contact {name} uniquely nahi mila. Cancelled."
            matches[0].click()
            self.page.wait_for_timeout(700)
            header = self.page.locator('[data-testid="conversation-info-header-chat-title"]')
            if header.count() == 0:
                return False, "Chat header verify nahi hua. Cancelled."
            actual = ""
            for i in range(header.count()):
                item = header.nth(i)
                title = item.inner_text().strip()
                if title.casefold() == name.casefold():
                    actual = title
                    break
            if actual.strip().casefold() != name.casefold():
                return False, f"Wrong contact: {actual}. Cancelled."
            return True, f"Verified chat: {actual}"
        except Exception as error:
            return False, f"Contact verification failed: {error}"

    # ========================================================
    # MESSAGE BOX
    # ========================================================

    def _get_message_box(self):
        if not self.page:
            return None

        boxes = self.page.get_by_role("textbox")
        count = boxes.count()

        if count <= 0:
            return None

        for index in range(count - 1, -1, -1):
            try:
                box = boxes.nth(index)
                if box.is_visible(timeout=300):
                    return box
            except Exception:
                continue

        return None

    # ========================================================
    # SEND MESSAGE
    # ========================================================

    def send_message(self, name, message):
        name = name.strip()
        message = message.strip()

        if not name:
            return False, "Boss, WhatsApp contact name nahi mila."

        if not message:
            return False, "Boss, WhatsApp message khaali hai."

        if not self.started:
            if not self.start():
                return False, "WhatsApp Web Edge se attach nahi ho paaya."

        try:
            ready, ready_message = self.wait_until_ready(timeout=15)
            if not ready:
                return False, ready_message

            opened, open_message = self.open_contact(name)
            if not opened:
                return False, open_message

            message_box = self._get_message_box()
            if message_box is None:
                return False, "Boss, WhatsApp message box nahi mila."

            message_box.click(force=True)
            message_box.fill(message)
            self.page.wait_for_timeout(250)
            message_box.press("Enter")
            self.page.wait_for_timeout(700)

            print(
                f"💬 WhatsApp sent to {name}: {message}",
                flush=True,
            )
            return True, "Message successfully sent."

        except PlaywrightTimeoutError:
            return False, "Boss, WhatsApp Web response nahi de raha."

        except Exception as error:
            print(
                f"❌ WhatsApp send error: {error}",
                flush=True,
            )
            return False, f"WhatsApp message send nahi ho paaya: {error}"

    # ========================================================
    # CLOSE / DISCONNECT
    # ========================================================
    # IMPORTANT:
    # Do NOT close the connected browser/context.
    # Edge belongs to the user. We only disconnect Playwright.

    def close(self):
        self._disconnect_only()

    def _disconnect_only(self):
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        self.started = False


if __name__ == "__main__":
    agent = WhatsAppAgent()

    try:
        if agent.start():
            print("WhatsApp Edge attachment started.")
            ready, message = agent.wait_until_ready(timeout=20)
            print(message)

            if ready:
                name = input("Contact name: ").strip()
                text = input("Message: ").strip()
                success, reply = agent.send_message(name, text)
                print("RESULT:", success, reply)

            input("Press Enter to disconnect JARVIS (Edge will remain open)...")
    except Exception as error:
        print(f"Manual test error: {error}")
    finally:
        agent.close()
