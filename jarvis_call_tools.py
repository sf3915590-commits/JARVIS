"""Bounded, real desktop and live-information tools for a verified JARVIS call.

The phone can launch known applications/sites and request current public data.
Never turn a transcription or retrieved webpage into arbitrary shell commands,
payments, messages, file deletion, or desktop-wide permissions.
"""
from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urlparse


APP_ALIASES = {
    "chrome": "chrome", "google chrome": "chrome",
    "vs code": "vscode", "vscode": "vscode",
    "visual studio code": "vscode",
    "notepad": "notepad", "calculator": "calculator",
    "calc": "calculator", "paint": "paint", "ms paint": "paint",
    "edge": "edge", "microsoft edge": "edge",
    "whatsapp": "whatsapp", "chatgpt": "chatgpt",
    "chat gpt": "chatgpt", "claude": "claude",
    "spotify": "spotify",
}
SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "gmail": "https://mail.google.com",
    "spotify web": "https://open.spotify.com",
}
FOLDERS = {"downloads", "documents", "desktop", "pictures", "videos", "music"}
OPEN_PREFIX = r"(?:please\s+)?(?:open|launch|start|run|khol|kholo|khol do|chalao|chalu karo|open karo|open kar do)"
OPEN_SUFFIX = r"(?:open|open karo|open kar do|khol do|kholo|chalao|chalu karo|launch karo)"


def normalize(text):
    phrase = re.sub(r"^(?:(?:hey|hello)\s+)?jarvis[\s,.:!-]*", "", str(text or "").strip(), flags=re.I)
    phrase = re.sub(r"[^\w\s]", " ", phrase.lower())
    return re.sub(r"\s+", " ", phrase).strip()


def call_hangup_command(text):
    """Only full utterances; quoted mentions of a command must not hang up."""
    phrase = normalize(text)
    return phrase in {
        "cut the call", "cut call", "call cut", "call cut karo",
        "call cut kar do", "call kaat do", "call kaat dena",
        "call band karo", "call band kar do", "call rakh do",
        "phone rakh do", "phone kaat do",
        "disconnect", "disconnect call", "disconnect the call",
        "hang up", "hangup", "hang up the call",
        "end call", "end the call", "end this call",
        "call end karo", "call end kar do",
        "bye hang up", "goodbye hang up",
        "kall kat do", "kat do call",
    }


def classify(text):
    """Return a stable (intent, argument) tuple, or None for ordinary chat."""
    t = normalize(text)
    if not t:
        return None
    if call_hangup_command(text):
        return ("hangup", "")
    if t in {"what can you do", "tell me your features", "tell me your future",
             "what are your features", "what are your capabilities", "your features",
             "apne features batao", "tum kya kar sakti ho"}:
        return ("capabilities", "")
    if (re.search(r"\b(?:what(?:s| is)? the time|what time is it|current time|time now)\b", t)
            or re.search(r"\b(?:time batao|kitne baje|kitna time hua|abhi time kya|abhi kya time)\b", t)):
        return ("time", "")
    if re.search(r"\b(?:today s date|todays date|what date is it|current date|aaj ki date|aaj ka din|what day is it)\b", t):
        return ("date", "")
    if re.search(r"\b(?:latest news|today s news|todays news|breaking news|news batao|aaj ki news|headlines|current news|recent news|live news)\b", t):
        topic = re.sub(r"\b(?:tell me|show me|give me|what is|what are|batao|sunao|ki|ke|about|on|latest|today s|todays|breaking|current|recent|live|news|headlines|aaj)\b", " ", t)
        topic = re.sub(r"\s+", " ", topic).strip()
        return ("news", (topic[:90] + " latest news") if topic else "India world latest news")

    # Only explicit named targets get privileged desktop operations.
    prefix = re.fullmatch(OPEN_PREFIX + r"\s+(?:the\s+)?(.+?)(?:\s+app)?", t)
    suffix = re.fullmatch(r"(.+?)\s+" + OPEN_SUFFIX, t)
    target = prefix.group(1).strip() if prefix else suffix.group(1).strip() if suffix else ""
    if target:
        target = re.sub(r"^(?:my|the)\s+", "", target)
        if target.endswith(" folder"):
            target = target[:-7].strip()
        if target in FOLDERS:
            return ("folder", target)
        if target in SITES:
            return ("site", target)
        if target in APP_ALIASES:
            return ("app", APP_ALIASES[target])

    # A public web search returns snippets to the phone, not a browser command.
    m = re.fullmatch(r"(?:search(?: the)? (?:web|internet|google) (?:for )?|google search (?:for )?)(.{3,150})", t)
    if m:
        return ("search", m.group(1).strip())
    return None


def _plain(text, limit=115):
    # Never repeat scripts, HTML tags, or untrusted snippets as commands.
    s = re.sub(r"<[^>]+>", " ", str(text or ""))
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .:-")
    return s[:limit].strip()


class CallTools:
    def __init__(self, app_launcher=None, site_opener=None, folder_opener=None,
                 news_search=None, text_search=None, clock=None):
        self.app_launcher = app_launcher
        self.site_opener = site_opener
        self.folder_opener = folder_opener
        self.news_search = news_search
        self.text_search = text_search
        self.clock = clock or (lambda: datetime.now().astimezone())

    @staticmethod
    def _app(name):
        try:
            from windows_control import launch_installed_app
            success, message = launch_installed_app(name)
            if success:
                return success, message
        except Exception:
            pass
        from actions import JarvisActions
        return JarvisActions().open_app(name)

    @staticmethod
    def _site(url):
        import webbrowser
        return bool(webbrowser.open(url, new=2)), "Browser mein website open kar di."

    @staticmethod
    def _folder(name):
        from windows_control import open_folder
        return open_folder(name)

    @staticmethod
    def _news(query):
        from web_agent import search_web
        return search_web(query, max_results=3)

    @staticmethod
    def _search(query):
        from ddgs import DDGS
        try:
            return list(DDGS().text(query, max_results=3))
        except Exception:
            return []

    def handle(self, text):
        intent = classify(text)
        if intent is None or intent[0] == "hangup":
            return None
        action, argument = intent
        if action == "capabilities":
            return ("Boss, call par main Chrome aur doosre apps khol sakti hoon, "
                    "web search, live news, date aur exact local time bata sakti hoon. "
                    "Call cut bhi kar sakti hoon.")
        if action == "time":
            now = self.clock()
            return "Boss, abhi " + now.strftime("%I:%M:%S %p").lstrip("0") + " hai, " + now.strftime("%Z") + "."
        if action == "date":
            return "Boss, aaj " + self.clock().strftime("%A, %d %B %Y") + " hai."
        if action == "app":
            launch = self.app_launcher or self._app
            try:
                ok, _message = launch(argument)
            except Exception:
                ok = False
            return (argument + " open kar diya, Boss.") if ok else (
                "Boss, " + argument + " abhi open nahi ho paaya.")
        if action == "site":
            open_site = self.site_opener or self._site
            try:
                ok, _message = open_site(SITES[argument])
            except Exception:
                ok = False
            return (argument + " website khol di, Boss.") if ok else (
                "Boss, " + argument + " site open nahi ho paayi.")
        if action == "folder":
            open_folder = self.folder_opener or self._folder
            try:
                ok, _message = open_folder(argument)
            except Exception:
                ok = False
            return ("Boss, " + argument + " folder open kar diya.") if ok else (
                "Boss, folder open nahi ho paaya.")
        if action in {"news", "search"}:
            get_results = (self.news_search or self._news) if action == "news" else (
                self.text_search or self._search)
            try:
                results = get_results(argument) or []
            except Exception:
                results = []
            headlines = []
            for result in results[:2]:
                if isinstance(result, dict):
                    title = _plain(result.get("title") or result.get("heading"), 100)
                    link = result.get("url") or result.get("href") or ""
                    domain = urlparse(link).hostname or ""
                    if title:
                        headlines.append(title + (", source " + domain if domain else ""))
            if not headlines:
                return ("Boss, live search se abhi verified results nahi mile. "
                        "Main purani news ko latest bata kar guess nahi karungi.")
            label = "Recent headlines" if action == "news" else "Search mein mila"
            return "Boss, " + label + ": " + "; ".join(headlines)
        return None
