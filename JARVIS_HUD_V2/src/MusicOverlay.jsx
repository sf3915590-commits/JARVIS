import React from "react";

const NOTES = ["♪", "♫", "♬", "♪", "♫", "♬", "♪", "♫", "♬", "♪", "♫", "♬"];

function formatTime(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return "--:--";
  const m = Math.floor(value / 60);
  const s = Math.floor(value % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function MusicOverlay({
  active = false,
  playing = false,
  title = "Music",
  artist = "",
  lyric = "",
  progress = 0,
  position = 0,
  duration = 0,
}) {
  if (!active) return null;

  const safeProgress = Math.max(0, Math.min(100, Number(progress) || 0));
  const hasProgress = Number(duration) > 0;
  const lyricText = String(lyric || "").trim();

  return (
    <div className={`jarvis-music-mode ${playing ? "is-playing" : "is-paused"}`}>
      <div className="music-mode-vignette" />
      <div className="music-mode-stars" aria-hidden="true">
        {Array.from({ length: 90 }, (_, i) => (
          <span
            key={i}
            style={{
              "--x": `${(i * 37) % 100}%`,
              "--y": `${(i * 61) % 100}%`,
              "--d": `${(i % 17) * 0.11}s`,
              "--s": `${1 + (i % 3)}px`,
            }}
          />
        ))}
      </div>

      <div className="music-mode-orbit music-mode-orbit-a" />
      <div className="music-mode-orbit music-mode-orbit-b" />
      <div className="music-mode-orbit music-mode-orbit-c" />

      <div className="music-mode-note-field" aria-hidden="true">
        {NOTES.map((note, i) => (
          <span
            key={`${note}-${i}`}
            style={{
              "--angle": `${i * 30}deg`,
              "--radius": `${34 + (i % 3) * 5}%`,
              "--delay": `${(i % 8) * 0.45}s`,
            }}
          >
            {note}
          </span>
        ))}
      </div>

      <section className="music-mode-core">
        <div className="music-mode-inner-ring" />
        <div className="music-mode-particle-ring">
          {Array.from({ length: 72 }, (_, i) => (
            <i key={i} style={{ "--i": i, "--delay": `${(i % 12) * 0.08}s` }} />
          ))}
        </div>

        <div className="music-mode-center">
          <div className="music-mode-main-note">{playing ? "♫" : "♪"}</div>
          <div className="music-mode-title">{title || "Music"}</div>
          <div className="music-mode-artist">{artist || "Unknown artist"}</div>
          <div className="music-mode-time">
            {formatTime(position)} / {formatTime(duration)}
          </div>

          <div className={`music-mode-progress ${hasProgress ? "" : "indeterminate"}`}>
            <span style={{ width: `${safeProgress}%` }} />
          </div>

          <div className="music-mode-controls" aria-hidden="true">
            <span>↶</span>
            <button type="button" tabIndex={-1}>{playing ? "Ⅱ" : "▶"}</button>
            <span>↷</span>
          </div>
        </div>

        <div className="music-mode-lyrics">
          <div className="music-mode-section-label">LYRICS</div>
          <div className="music-mode-lyrics-panel">
            {lyricText || "Lyrics unavailable for this source."}
            <div className="music-mode-wave">
              {Array.from({ length: 30 }, (_, i) => <i key={i} />)}
            </div>
          </div>
        </div>
      </section>

      <aside className="music-mode-left">
        <div className="music-mode-clock">
          {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
        <div className="music-mode-date">
          {new Date().toLocaleDateString([], { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}
        </div>
        <div className="music-mode-greeting">Music Mode</div>

        <nav className="music-mode-nav">
          <span>⌂ Home</span>
          <span>▣ AI Chat</span>
          <span className="selected">♫ Music</span>
          <span>⚒ Tools</span>
          <span>⚙ System</span>
          <span>⚙ Settings</span>
        </nav>

        <div className="music-mode-quote">
          “Music is not just sound,<br />
          it’s a feeling.”<br />
          <small>— JARVIS</small>
        </div>
      </aside>

      <aside className="music-mode-right">
        <div className="music-mode-panel">
          <div className="music-mode-panel-title">NOW PLAYING</div>
          <div className="music-mode-now">
            <div className="music-mode-art">♫</div>
            <div>
              <strong>{title || "Music"}</strong>
              <span>{artist || "Unknown artist"}</span>
            </div>
            <b>♡</b>
          </div>
        </div>

        <div className="music-mode-panel music-mode-upnext">
          <div className="music-mode-panel-title">UP NEXT</div>
          <div className="music-mode-empty">Queue data will appear here when JARVIS has a queue.</div>
        </div>

        <div className="music-mode-panel music-mode-say">
          <div className="music-mode-panel-title">YOU CAN SAY</div>
          <span>“Next song”</span>
          <span>“Pause music”</span>
          <span>“Volume up”</span>
          <span>“Stop music”</span>
          <span>“Music mode”</span>
        </div>
      </aside>

      <div className="music-mode-voice">
        <div className="music-mode-voice-wave">
          {Array.from({ length: 11 }, (_, i) => <i key={i} />)}
        </div>
        <div className="music-mode-mic">♫</div>
        <span>{playing ? "Music playing, Boss..." : "Music paused, Boss..."}</span>
        <div className="music-mode-voice-wave">
          {Array.from({ length: 11 }, (_, i) => <i key={i} />)}
        </div>
      </div>
    </div>
  );
}
