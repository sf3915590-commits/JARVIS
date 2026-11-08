import re
import urllib.parse
import webbrowser
import time
import threading

# JARVIS_YOUTUBE_AUTOPLAY_V3
try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


def clean_query(text):
    text = text.strip()

    text = re.sub(
        r"^(youtube|play|search|find|song|video)\s*[:,-]?\s*",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\b(on|in|par|pe)\s+youtube\b",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\b(chalao|bajao|play karo|play|search karo)\b",
        "",
        text,
        flags=re.I
    )

    return text.strip()


def score_result(title, query):
    title_lower = title.lower()
    query_lower = query.lower()

    score = 0

    words = re.findall(r"[a-z0-9]+", query_lower)

    for word in words:

        if len(word) < 2:
            continue

        if word in title_lower:
            score += 10

    # Strong preference for original Tum Hi Ho
    if "tum hi ho" in query_lower:

        if "tum hi ho" in title_lower:
            score += 100

        if "arijit singh" in title_lower:
            score += 80

        if "official" in title_lower:
            score += 20

        if "audio" in title_lower:
            score += 10

        bad_words = [
            "cover",
            "remix",
            "lofi",
            "slowed",
            "reverb",
            "live",
            "instrumental",
            "karaoke",
            "reaction"
        ]

        for bad in bad_words:
            if bad in title_lower:
                score -= 30

    return score


def start_youtube_playback():
    """
    Focus the YouTube player and start playback.

    YouTube may block browser autoplay, so after the selected
    video opens we explicitly focus the player and send K.
    """

    if pyautogui is None:
        print(
            "JARVIS: pyautogui unavailable; "
            "YouTube playback may require manual play.",
            flush=True
        )
        return False

    try:

        # Allow Chrome/YouTube to finish loading.
        time.sleep(4)

        screen_width, screen_height = pyautogui.size()

        # Focus the video player area.
        pyautogui.click(
            screen_width // 2,
            int(screen_height * 0.45)
        )

        time.sleep(0.4)

        # YouTube keyboard shortcut:
        # K = play/pause
        pyautogui.press("k")

        time.sleep(0.5)

        return True

    except Exception as error:

        print(
            f"JARVIS YouTube playback warning: {error}",
            flush=True
        )

        return False


def search_youtube(query):

    query = clean_query(query)

    if not query:
        return False, "Boss, kaunsa song ya video chahiye?"

    # =====================================================
    # YT-DLP SEARCH
    # =====================================================

    if yt_dlp is not None:

        try:

            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": True,
            }

            with yt_dlp.YoutubeDL(options) as ydl:

                result = ydl.extract_info(
                    f"ytsearch10:{query}",
                    download=False
                )

            entries = result.get("entries") or []

            if entries:

                best_entry = None
                best_score = -999999

                for entry in entries:

                    title = entry.get(
                        "title",
                        ""
                    )

                    current_score = score_result(
                        title,
                        query
                    )

                    print(
                        f"   🔎 {current_score:4} | {title}",
                        flush=True
                    )

                    if current_score > best_score:

                        best_score = current_score
                        best_entry = entry

                if best_entry:

                    video_url = best_entry.get(
                        "webpage_url"
                    )

                    video_id = best_entry.get(
                        "id"
                    )

                    if not video_url and video_id:

                        video_url = (
                            "https://www.youtube.com/watch?v="
                            + video_id
                        )

                    if video_url:

                        title = best_entry.get(
                            "title",
                            query
                        )

                        print(
                            f"✅ Best YouTube result: {title}",
                            flush=True
                        )

                        # -------------------------------------------------
                        # OPEN THE EXACT SELECTED VIDEO
                        # -------------------------------------------------

                        webbrowser.open(
                            video_url,
                            new=0,
                            autoraise=True
                        )

                        print(
                            "▶️ YouTube video opened. "
                            "Starting playback...",
                            flush=True
                        )

                        # -------------------------------------------------
                        # FORCE PLAYER FOCUS + PLAY
                        # -------------------------------------------------

                        playback_started = (
                            start_youtube_playback()
                        )

                        if playback_started:

                            print(
                                "▶️ YouTube playback trigger sent.",
                                flush=True
                            )

                            return (
                                True,
                                f"Boss, YouTube par {title} chala diya."
                            )

                        else:

                            return (
                                True,
                                f"Boss, YouTube par {title} khol diya. "
                                "Play button manually press karna pad sakta hai."
                            )

        except Exception as error:

            print(
                f"⚠️ YouTube search warning: {error}",
                flush=True
            )

    # =====================================================
    # FALLBACK
    # =====================================================

    url = (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(query)
    )

    try:

        webbrowser.open(
            url,
            new=0,
            autoraise=True
        )

        return (
            True,
            f"Boss, YouTube par {query} search kar diya."
        )

    except Exception as error:

        return (
            False,
            f"YouTube open nahi ho paaya: {error}"
        )


def play_youtube(query):
    return search_youtube(query)


def youtube_search_url(query):

    query = clean_query(query)

    return (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(query)
    )


if __name__ == "__main__":

    print("=" * 50)
    print("       JARVIS YOUTUBE AGENT")
    print("=" * 50)

    print()
    print("Example:")
    print("Tum Hi Ho Arijit Singh")
    print()

    query = input("> ").strip()

    ok, message = play_youtube(query)

    print()
    print(message)