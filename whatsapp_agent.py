from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import re

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
        if self.playwright:
            self._disconnect_only()

        try:
            self.playwright = sync_playwright().start()

            # Attach to the EXISTING Edge instance.
            self.browser = self.playwright.chromium.connect_over_cdp(CDP_URL)

            contexts = self.browser.contexts
            if not contexts:
                raise RuntimeError("Existing Edge ka browser context nahi mila.")

            self.context = next((ctx for ctx in contexts if any("web.whatsapp.com" in (p.url or "").lower() for p in ctx.pages)), contexts[0])

            # Prefer an already-open WhatsApp Web tab.
            whatsapp_pages = []
            for page in self.context.pages:
                try:
                    if "web.whatsapp.com" in (page.url or "").lower():
                        whatsapp_pages.append(page)
                except Exception:
                    pass

            if whatsapp_pages:
                self.page = whatsapp_pages[0]
            elif self.context.pages:
                # Reuse an existing Edge tab rather than launching a new browser.
                self.page = self.context.pages[0]
                self.page.goto(
                    WHATSAPP_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
            else:
                self.page = self.context.new_page()
                self.page.goto(
                    WHATSAPP_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

            self.started = True

            print(
                "💬 WhatsApp: attached to existing Edge (CDP 9222).",
                flush=True,
            )
            return True

        except Exception as error:
            print(
                f"❌ WhatsApp Edge attach error: {error}",
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
            return False, "WhatsApp Web connection nahi hai."

        name = name.strip()
        if not name:
            return False, "WhatsApp contact name nahi mila."

        try:
            ready, message = self.wait_until_ready(timeout=10)
            if not ready:
                return False, message

            search = self.page.get_by_role(
                "textbox",
                name=re.compile(
                    r"Search or start a new chat",
                    re.IGNORECASE,
                ),
            ).first

            if not search.is_visible(timeout=2500):
                inputs = self.page.locator(
                    'input[placeholder*="Search" i]'
                )
                if inputs.count() > 0:
                    search = inputs.first
                else:
                    return False, "WhatsApp search box nahi mila."

            search.click(force=True)
            search.fill("")
            search.fill(name)

            self.page.wait_for_timeout(1200)

            return True, f"{name} search ho gaya."

        except PlaywrightTimeoutError:
            return False, "Boss, WhatsApp search box load nahi hua."

        except Exception as error:
            return False, f"Contact search nahi ho paaya: {error}"

    # ========================================================
    # OPEN CONTACT
    # ========================================================

    def open_contact(self, name):
        try:
            success, message = self.search_contact(name)
            if not success:
                return False, message

            self.page.wait_for_timeout(800)

            result = self.page.get_by_text(
                name,
                exact=True,
            ).first

            try:
                result.wait_for(state="visible", timeout=5000)
                result.click(force=True)
                self.page.wait_for_timeout(700)
                return True, f"{name} chat open ho gaya."
            except Exception:
                result = self.page.get_by_text(
                    re.compile(
                        f"^{re.escape(name)}$",
                        re.IGNORECASE,
                    )
                ).first
                result.wait_for(state="visible", timeout=4000)
                result.click(force=True)
                self.page.wait_for_timeout(700)
                return True, f"{name} chat open ho gaya."

        except PlaywrightTimeoutError:
            return False, f"Boss, WhatsApp mein '{name}' contact nahi mila."

        except Exception as error:
            return False, f"WhatsApp chat open nahi ho paayi: {error}"

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

            header = self.page.locator("#main header")
            if not header.count() or not header.get_by_text(name, exact=True).count():
                return False, "Contact header verify nahi hua; message send nahi kiya."
            message_box = self._get_message_box()
            if message_box is None:
                return False, "Boss, WhatsApp message box nahi mila."

            outgoing = self.page.locator("#main .message-out").filter(has_text=message)
            before = outgoing.count()
            message_box.click()
            message_box.fill(message)
            message_box.press("Enter")
            try:
                self.page.wait_for_function(
                    """({text, before}) => [...document.querySelectorAll('#main .message-out')]
                        .filter(el => el.innerText.includes(text)).length > before""",
                    arg={"text": message, "before": before},
                    timeout=6000,
                )
            except Exception:
                return False, "Send confirm nahi hua. Automatic retry nahi kiya; duplicate se bachne ke liye chat check karo."
            return True, "Message outgoing chat mein nazar aa gaya; delivery/read confirm nahi hai."

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
