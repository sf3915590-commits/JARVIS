from __future__ import annotations

import re
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pygame


AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
LRC_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")


@dataclass
class Track:
    path: str
    title: str
    artist: str = ""
    duration: float = 0.0


class JarvisMusic:
    """
    Local music engine.
    No YouTube and no browser playback.
    Audio lives in Tahrun/Music/.
    Optional synced lyrics live beside the audio file as:
        Song Name.lrc
    """

    def __init__(self, music_dir="Music"):
        self.music_dir = Path(music_dir)
        self.music_dir.mkdir(parents=True, exist_ok=True)

        pygame.mixer.init()
        self.volume = 0.85
        pygame.mixer.music.set_volume(self.volume)

        self.tracks = []
        self.index = -1
        self.playing = False
        self.started_at = 0.0
        self.paused_position = 0.0
        self.lyrics = []
        self.listeners: list[Callable[[dict], None]] = []
        self._stop = False

        self.refresh()

        self._thread = threading.Thread(
            target=self._watch,
            daemon=True,
            name="JARVIS-Music-Watcher",
        )
        self._thread.start()

    def add_listener(self, callback):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def refresh(self):
        files = sorted(
            p for p in self.music_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
        )

        tracks = []
        for p in files:
            title = p.stem
            artist = ""
            if " - " in title:
                title, artist = title.split(" - ", 1)

            try:
                duration = float(pygame.mixer.Sound(str(p)).get_length())
            except Exception:
                duration = 0.0

            tracks.append(
                Track(
                    path=str(p),
                    title=title.strip(),
                    artist=artist.strip(),
                    duration=duration,
                )
            )

        self.tracks = tracks
        return tracks

    def _find(self, query):
        q = str(query or "").strip().lower()

        if not self.tracks:
            self.refresh()

        if not self.tracks:
            return -1

        if not q:
            return 0

        exact = [
            i for i, track in enumerate(self.tracks)
            if track.title.lower() == q
        ]
        if exact:
            return exact[0]

        partial = [
            i for i, track in enumerate(self.tracks)
            if q in track.title.lower()
            or track.artist.lower() in q
        ]
        return partial[0] if partial else -1

    def _load_lyrics(self, audio_path):
        path = Path(audio_path).with_suffix(".lrc")
        if not path.exists():
            return []

        result = []
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        for line in text.splitlines():
            match = LRC_RE.match(line.strip())
            if not match:
                continue

            minutes = int(match.group(1))
            seconds = float(match.group(2))
            result.append(
                (minutes * 60 + seconds, match.group(3).strip())
            )

        return sorted(result)

    def _position(self):
        if self.index < 0:
            return 0.0

        if self.playing:
            return max(0.0, time.monotonic() - self.started_at)

        return max(0.0, self.paused_position)

    def _lyric(self):
        position = self._position()
        current = ""

        for timestamp, text in self.lyrics:
            if timestamp <= position:
                current = text
            else:
                break

        return current

    def state(self):
        track = (
            self.tracks[self.index]
            if 0 <= self.index < len(self.tracks)
            else None
        )

        return {
            "active": bool(track),
            "playing": self.playing,
            "track": asdict(track) if track else None,
            "title": track.title if track else "",
            "artist": track.artist if track else "",
            "position": self._position(),
            "duration": track.duration if track else 0.0,
            "lyric": self._lyric(),
            "volume": self.volume,
        }

    def _emit(self):
        payload = self.state()
        for listener in list(self.listeners):
            try:
                listener(payload)
            except Exception:
                pass

    def play(self, query=""):
        self.refresh()
        index = self._find(query)

        if index < 0:
            return False, "Boss, Music folder mein woh song nahi mila."

        track = self.tracks[index]

        try:
            pygame.mixer.music.load(track.path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()

            self.index = index
            self.playing = True
            self.paused_position = 0.0
            self.started_at = time.monotonic()
            self.lyrics = self._load_lyrics(track.path)
            self._emit()

            return True, f"{track.title} play kar diya Boss."
        except Exception as error:
            return False, f"Boss, song play nahi ho paaya: {error}"

    def pause(self):
        if self.playing:
            self.paused_position = self._position()
            pygame.mixer.music.pause()
            self.playing = False
            self._emit()
        return True, "Music pause kar diya Boss."

    def resume(self):
        if self.index >= 0:
            pygame.mixer.music.unpause()
            self.started_at = time.monotonic() - self.paused_position
            self.playing = True
            self._emit()
            return True, "Music resume kar diya Boss."

        return False, "Boss, abhi koi music loaded nahi hai."

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False
        self.index = -1
        self.paused_position = 0.0
        self.lyrics = []
        self._emit()
        return True, "Music stop kar diya Boss."

    def next(self):
        self.refresh()
        if not self.tracks:
            return False, "Boss, Music folder empty hai."

        next_index = 0 if self.index < 0 else (self.index + 1) % len(self.tracks)
        return self.play(self.tracks[next_index].title)

    def previous(self):
        self.refresh()
        if not self.tracks:
            return False, "Boss, Music folder empty hai."

        if self.index < 0:
            previous_index = len(self.tracks) - 1
        else:
            previous_index = (self.index - 1) % len(self.tracks)

        return self.play(self.tracks[previous_index].title)

    def set_volume(self, percent):
        value = max(0, min(100, int(percent)))
        self.volume = value / 100.0
        pygame.mixer.music.set_volume(self.volume)
        self._emit()
        return True, f"Volume {value}% kar diya Boss."

    def _watch(self):
        while not self._stop:
            time.sleep(0.25)

            if self.playing and not pygame.mixer.music.get_busy():
                self.playing = False
                self.index = -1
                self.lyrics = []
                self._emit()
            elif self.playing:
                self._emit()

    def shutdown(self):
        self._stop = True
        pygame.mixer.music.stop()
        pygame.mixer.quit()


music = JarvisMusic()
