import React, { useEffect, useRef } from "react";

export default function MusicHUD({
  musicState = {},
  onPause,
  onResume,
  onNext,
  onPrevious,
  onStop,
}) {
  const frameRef = useRef(null);

  const send = (type, payload = {}) => {
    const frame = frameRef.current;
    if (!frame?.contentWindow) return;
    frame.contentWindow.postMessage(
      { type, ...payload },
      window.location.origin
    );
  };

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;

    const ready = () => {
      send("jarvis-music:text", {
        text: musicState?.title
          ? `play ${musicState.title}`
          : "play music",
        force: true,
      });
    };

    frame.addEventListener("load", ready);
    return () => frame.removeEventListener("load", ready);
  }, []);

  useEffect(() => {
    if (!musicState) return;

    if (musicState.title) {
      send("jarvis-music:text", {
        text: `play ${musicState.title}`,
        force: true,
      });
    }

    if (musicState.playing === false) {
      send("jarvis-music:cmd", { cmd: "pause" });
    }

    if (musicState.playing === true) {
      send("jarvis-music:cmd", { cmd: "play" });
    }
  }, [musicState?.title, musicState?.playing]);

  const command = (cmd, fallback) => {
    send("jarvis-music:cmd", { cmd });
    if (fallback) fallback();
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 99999,
        width: "100vw",
        height: "100vh",
        background: "#000",
        overflow: "hidden",
      }}
    >
      <iframe
        ref={frameRef}
        title="JARVIS Real Spotify Music"
        src="/jarvis-music-mode.html?bridge=1"
        allow="autoplay; encrypted-media"
        style={{
          width: "100%",
          height: "100%",
          border: 0,
          display: "block",
        }}
      />

      <div
        style={{
          position: "absolute",
          bottom: 18,
          left: 18,
          display: "flex",
          gap: 8,
          zIndex: 100000,
        }}
      >
        <button onClick={() => command("previous", onPrevious)}>PREV</button>
        <button onClick={() => command("pause", onPause)}>PAUSE</button>
        <button onClick={() => command("play", onResume)}>PLAY</button>
        <button onClick={() => command("next", onNext)}>NEXT</button>
        <button onClick={() => command("stop", onStop)}>STOP</button>
      </div>
    </div>
  );
}
