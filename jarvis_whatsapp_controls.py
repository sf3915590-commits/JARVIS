"""Safe, explicit WhatsApp Web voice actions for the existing JARVIS agent.

These UI routines use the existing WhatsAppAgent/Edge CDP session and do not
create a browser profile or transmit data to a new service. WhatsApp Web DOMs
change often; every operation validates the target and fails closed if a
reliable control cannot be identified.
"""
from __future__ import annotations

import re
from typing import Any


def parse_command(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    # Keep punctuation intact because quoted message text must be matched exactly.
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"^(?:hey\s+)?jarvis[\s,:-]*", "", cleaned, flags=re.I).strip()
    cleaned = cleaned.strip(" \t\r\n,.;!?")
    c = cleaned.lower()

    # Read-receipt toggle: account privacy setting, changed only on an explicit on/off request.
    for pattern in (
        r"(?:turn|switch|set)\s+(?:whatsapp\s+)?read receipts\s+(on|off)",
        r"(?:turn|switch)\s+(on|off)\s+(?:whatsapp\s+)?read receipts",
        r"(?:enable|activate)\s+(?:whatsapp\s+)?read receipts",
        r"(?:disable|deactivate)\s+(?:whatsapp\s+)?read receipts",
        r"(?:read receipts|blue ticks)\s+(on|off|enable|disable)",
        r"(?:turn|switch)\s+(?:whatsapp\s+)?blue ticks\s+(on|off)",
    ):
        m = re.fullmatch(pattern, c, re.I)
        if m:
            value = m.group(1) if m.lastindex else ""
            enabled = value in ("on", "enable") if value else ("enable" in c or "activate" in c)
            if "disable" in c or "deactivate" in c or value == "off":
                enabled = False
            return {"action": "whatsapp_read_receipts", "enabled": enabled}

    # Exact-text delete requests only. A contact and exact message must both be present.
    patterns = [
        r"(?:delete|remove)\s+(?:the\s+)?(?:whatsapp\s+)?message\s+['\"](.+?)['\"]\s+(?:from|in)\s+(.+?)(?:\s+(?:on\s+)?whatsapp)?(?:\s+(for everyone|for me))?",
        r"(?:delete|remove)\s+(?:the\s+)?(?:whatsapp\s+)?message\s+(.+?)\s+from\s+(.+?)(?:\s+(?:on\s+)?whatsapp)?(?:\s+(for everyone|for me))?",
    ]
    for i, pattern in enumerate(patterns):
        m = re.fullmatch(pattern, cleaned, re.I)
        if m:
            message, contact, scope = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "for me").strip().lower()
            if message and contact and contact not in {"everyone", "me"}:
                return {
                    "action": "whatsapp_delete_message",
                    "target": contact,
                    "message": message,
                    "scope": "everyone" if scope == "for everyone" else "me",
                }

    # Alternative, clear form: delete message from CONTACT saying "EXACT MESSAGE".
    m = re.fullmatch(
        r"(?:delete|remove)\s+(?:the\s+)?(?:whatsapp\s+)?message\s+from\s+(.+?)\s+(?:saying|that says)\s+['\"](.+?)['\"](?:\s+(for everyone|for me))?",
        cleaned, re.I,
    )
    if m:
        return {
            "action": "whatsapp_delete_message",
            "target": m.group(1).strip(),
            "message": m.group(2).strip(),
            "scope": "everyone" if (m.group(3) or "").lower() == "for everyone" else "me",
        }

    # Voice/video calls. Contact name must be delimited by 'on/via WhatsApp' or follow 'WhatsApp call'.
    call_patterns = [
        r"(?:(video|voice)\s+)?call\s+(?:to\s+)?(.+?)\s+(?:on|via)\s+whatsapp",
        r"whatsapp\s+(?:(video|voice)\s+)?call\s+(?:to\s+)?(.+)",
        r"(?:(video|voice)\s+)?whatsapp\s+call\s+(?:to\s+)?(.+)",
    ]
    for pattern in call_patterns:
        m = re.fullmatch(pattern, cleaned, re.I)
        if m:
            call_type = (m.group(1) or "voice").strip().lower()
            name = m.group(2).strip(" .,!?:;-")
            if name and name not in {"me", "everyone"}:
                return {"action": "whatsapp_call", "target": name, "video": call_type == "video"}

    return None


def _visible(loc: Any) -> bool:
    try:
        return loc.count() > 0 and loc.first.is_visible(timeout=700)
    except Exception:
        return False


def perform_call(agent: Any, contact: str, video: bool = False) -> tuple[bool, str]:
    if not agent.started and not agent.start():
        return False, "WhatsApp Web se connection nahi ho paaya. Edge mein WhatsApp logged in hona chahiye."
    try:
        ok, detail = agent.open_contact(contact)
        if not ok:
            return False, detail
        page = agent.page
        header = page.locator("#main header")
        if not header.count() or not header.get_by_text(contact, exact=True).count():
            return False, "Contact header verify nahi hua; call nahi ki."
        page.wait_for_timeout(300)
        desired = "video" if video else "voice"
        buttons = page.get_by_role("button")
        count = min(buttons.count(), 140)
        for index in range(count):
            button = buttons.nth(index)
            try:
                if not button.is_visible(timeout=100):
                    continue
                label = " ".join(filter(None, [
                    button.get_attribute("aria-label"),
                    button.get_attribute("title"),
                    button.inner_text(timeout=150),
                ])).lower()
                if desired == "video":
                    match = "video call" in label or ("video" in label and "call" in label)
                else:
                    match = ("voice call" in label) or (label.strip() in {"call", "voice call"})
                    match = match and "video" not in label
                if match:
                    button.click(timeout=2500)
                    page.wait_for_timeout(500)
                    return True, f"WhatsApp {desired} call button click hua; ringing/connection verify nahi hui."
            except Exception:
                continue
        return False, "Contact chat khul gaya, lekin WhatsApp Web ka call button verify nahi hua. Call manually start karo."
    except Exception as exc:
        return False, f"WhatsApp call start nahi ho paayi: {type(exc).__name__}: {exc}"


def set_read_receipts(agent: Any, enabled: bool) -> tuple[bool, str]:
    if not agent.started and not agent.start():
        return False, "WhatsApp Web se connect nahi ho paaya."
    try:
        page = agent.page
        # Open Settings, then Privacy. Fail closed if the expected screen cannot be identified.
        setting_button = page.locator('button[aria-label*="Settings" i], button[title*="Settings" i], [data-testid*="settings"]')
        if not _visible(setting_button):
            setting_button = page.get_by_role("button", name=re.compile(r"settings", re.I))
        if not _visible(setting_button):
            return False, "WhatsApp Settings button nahi mila; koi setting change nahi ki gayi."
        setting_button.first.click(timeout=2500)
        page.wait_for_timeout(300)
        privacy = page.get_by_text(re.compile(r"^Privacy$", re.I)).first
        if not _visible(privacy):
            return False, "WhatsApp Settings khul gaye, lekin Privacy option nahi mila. Setting unchanged hai."
        privacy.click(timeout=2500)
        page.wait_for_timeout(400)
        label = page.get_by_text(re.compile(r"^Read receipts$", re.I)).first
        if not _visible(label):
            return False, "Read receipts setting nahi mili. Setting unchanged hai."

        # Look around the exact label for a switch/checkbox; require a readable current state.
        candidates = []
        for depth in range(1, 5):
            ancestor = label.locator("xpath=" + "/".join([".."] * depth))
            try:
                for selector in ['[role="switch"]', '[role="checkbox"]', 'input[type="checkbox"]']:
                    loc = ancestor.locator(selector)
                    if loc.count():
                        candidates.append(loc.first)
            except Exception:
                continue
        for toggle in candidates:
            try:
                current_raw = toggle.get_attribute("aria-checked")
                if current_raw is None:
                    current_raw = toggle.get_attribute("checked")
                if current_raw is None:
                    current_raw = toggle.is_checked() if toggle.get_attribute("type") == "checkbox" else None
                if current_raw is None:
                    continue
                if isinstance(current_raw, bool):
                    current = current_raw
                elif str(current_raw).lower() in {"true", "checked", "1"}:
                    current = True
                elif str(current_raw).lower() in {"false", "none", "0", ""}:
                    current = False
                else:
                    continue
                if current != bool(enabled):
                    toggle.click(timeout=2000)
                    page.wait_for_timeout(300)
                verified_raw = toggle.get_attribute("aria-checked")
                if verified_raw is None:
                    verified_raw = toggle.get_attribute("checked")
                if verified_raw is not None:
                    verified = str(verified_raw).lower() in {"true", "checked", "1"}
                    if verified != bool(enabled):
                        return False, "Read receipts toggle ka naya state verify nahi hua."
                return True, f"WhatsApp read receipts {'ON' if enabled else 'OFF'} kar diye."
            except Exception:
                continue
        return False, "Read receipts row mil gaya, lekin toggle ka state safely verify nahi hua; koi change confirm nahi hai."
    except Exception as exc:
        return False, f"Read receipts setting update nahi ho paayi: {type(exc).__name__}: {exc}"


def delete_message(agent: Any, contact: str, message_text: str, scope: str = "me") -> tuple[bool, str]:
    if not contact.strip() or not message_text.strip():
        return False, "Delete ke liye contact aur exact message dono chahiye."
    if not agent.started and not agent.start():
        return False, "WhatsApp Web se connect nahi ho paaya."
    try:
        ok, detail = agent.open_contact(contact)
        if not ok:
            return False, detail
        page = agent.page
        matches = page.get_by_text(message_text, exact=True)
        if matches.count() == 0:
            matches = page.get_by_text(message_text, exact=False)
        if matches.count() == 0:
            return False, "Exact message is chat mein nahi mila; koi message delete nahi hua."
        # Favor the most recent exact match only after the caller confirms the operation.
        target = matches.last
        container = target.locator("xpath=ancestor::*[@data-testid='msg-container'][1]")
        if container.count() == 0:
            container = target.locator("xpath=ancestor::*[contains(@class,'message-out') or contains(@class,'message-in')][1]")
        if container.count() == 0:
            container = target.locator("xpath=..")
        container.hover(timeout=2500, force=True)
        page.wait_for_timeout(200)

        menu_opened = False
        for selector in [
            'button[aria-label*="message options" i]',
            'button[aria-label*="more options" i]',
            'button[title*="message options" i]',
            '[data-testid*="msg-menu"]',
        ]:
            candidate = container.locator(selector)
            if _visible(candidate):
                candidate.first.click(timeout=2000)
                menu_opened = True
                break
        if not menu_opened:
            try:
                target.click(button="right", timeout=2000, force=True)
                menu_opened = True
            except Exception:
                pass
        if not menu_opened:
            return False, "Message ka options menu open nahi hua; koi message delete nahi hua."

        delete_item = page.get_by_text(re.compile(r"^Delete message$", re.I)).first
        if not _visible(delete_item):
            delete_item = page.get_by_role("menuitem", name=re.compile(r"delete message", re.I)).first
        if not _visible(delete_item):
            return False, "Delete message option nahi mila; koi message delete nahi hua."
        delete_item.click(timeout=2500)
        page.wait_for_timeout(300)
        desired = re.compile(r"^Delete for everyone$", re.I) if scope == "everyone" else re.compile(r"^Delete for me$", re.I)
        choice = page.get_by_role("button", name=desired).first
        if not _visible(choice):
            choice = page.get_by_text(desired).first
        if not _visible(choice):
            return False, f"WhatsApp mein '{'Delete for everyone' if scope == 'everyone' else 'Delete for me'}' option available nahi; deletion complete nahi hui."
        choice.click(timeout=2500)
        page.wait_for_timeout(450)
        return True, f"WhatsApp message '{message_text}' {contact} ki chat se {'everyone ke liye' if scope == 'everyone' else 'tumhari chat se'} delete kar diya."
    except Exception as exc:
        return False, f"WhatsApp message delete nahi ho paaya: {type(exc).__name__}: {exc}"
