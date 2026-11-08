import React, { useCallback, useEffect, useRef, useState } from "react";
import "./mobile-companion.css";

const TOKEN_KEY = "jarvis.mobile.token.v1";

function makeSocketUrl() {
  const url = new URL("/", window.location.href);
  url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // Tailscale Serve terminates TLS on a dedicated TCP port; this avoids
  // relying on HTTP/2 WebSocket upgrade behavior on the HTTPS reverse proxy.
  url.port = window.location.protocol === "https:" ? "8444" : "8766";
  return url.toString();
}

export default function MobileCompanion() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [tokenDraft, setTokenDraft] = useState("");
  const [paired, setPaired] = useState(false);
  const [connection, setConnection] = useState("CONNECTING");
  const [mode, setMode] = useState("STANDBY");
  const [message, setMessage] = useState("JARVIS mobile companion ready.");
  const [command, setCommand] = useState("");
  const [activity, setActivity] = useState([]);
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [speakReplies, setSpeakReplies] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef(null);
  const recognitionRef = useRef(null);
  const reconnectRef = useRef(null);
  const aliveRef = useRef(true);

  const addActivity = useCallback((text) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setActivity((old) => [{ time, text: String(text).slice(0, 160) }, ...old].slice(0, 12));
  }, []);

  const speak = useCallback((text) => {
    if (!speakReplies || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(String(text));
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  }, [speakReplies]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setVoiceSupported(Boolean(SpeechRecognition));
    return () => {
      aliveRef.current = false;
      clearTimeout(reconnectRef.current);
      try { recognitionRef.current?.abort(); } catch {}
      try { wsRef.current?.close(); } catch {}
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, []);

  useEffect(() => {
    if (!token) {
      setPaired(false);
      setConnection("PAIRING REQUIRED");
      return undefined;
    }
    aliveRef.current = true;
    let stopped = false;

    const connect = () => {
      if (stopped || !aliveRef.current) return;
      setConnection("CONNECTING");
      let ws;
      try {
        ws = new WebSocket(makeSocketUrl());
        wsRef.current = ws;
      } catch (err) {
        setConnection("OFFLINE");
        setError(String(err?.message || err));
        reconnectRef.current = setTimeout(connect, 2500);
        return;
      }

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "AUTH", token }));
      };
      ws.onmessage = (event) => {
        let data;
        try { data = JSON.parse(event.data || "{}"); } catch { return; }
        if (data.type === "AUTH_OK") {
          setPaired(true);
          setConnection("CONNECTED");
          setError("");
          addActivity("SECURE MOBILE LINK ESTABLISHED");
          return;
        }
        if (data.type === "AUTH_FAILED" || data.type === "AUTH_REQUIRED") {
          setPaired(false);
          setConnection("PAIRING FAILED");
          setError("Pairing code ghalat hai. PC par dikhaya gaya code dobara enter karo.");
          localStorage.removeItem(TOKEN_KEY);
          setToken("");
          ws.close();
          return;
        }
        if (data.source !== "JARVIS") return;
        if (data.type === "STATE") setMode(String(data.state || "READY").toUpperCase());
        if (data.type === "MESSAGE") {
          const text = String(data.message || "");
          setMessage(text);
          speak(text);
        }
        if (data.type === "RESULT") {
          const text = String(data.message || "Execution complete");
          setMessage(text);
          addActivity(`RESULT // ${text}`);
          speak(text);
        }
        if (data.type === "ACTIVITY") addActivity(data.text || "JARVIS activity");
        if (data.type === "WAKE") setMode("LISTENING");
        if (data.type === "SYSTEM" && data.online === true) setMode("ONLINE");
      };
      ws.onerror = () => setConnection("CONNECTION ERROR");
      ws.onclose = () => {
        if (stopped) return;
        setPaired(false);
        setConnection("RECONNECTING");
        reconnectRef.current = setTimeout(connect, 2500);
      };
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(reconnectRef.current);
      try { wsRef.current?.close(); } catch {}
    };
  }, [token, addActivity, speak]);

  const savePairing = (event) => {
    event.preventDefault();
    const clean = tokenDraft.trim();
    if (clean.length < 24) {
      setError("Pairing code mukammal nahi lag raha. PC se poora code copy karo.");
      return;
    }
    localStorage.setItem(TOKEN_KEY, clean);
    setError("");
    setToken(clean);
    setTokenDraft("");
  };

  const sendCommand = (raw) => {
    const clean = String(raw || "").trim();
    if (!clean) return;
    const ws = wsRef.current;
    if (!paired || !ws || ws.readyState !== WebSocket.OPEN) {
      setError("JARVIS PC se secure connection nahi hai.");
      return;
    }
    ws.send(JSON.stringify({ source: "MOBILE", type: "COMMAND", command: clean }));
    setCommand("");
    setMessage(`Command sent: ${clean}`);
    setMode("PROCESSING");
    addActivity(`YOU // ${clean}`);
  };

  const startVoice = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError("Is iPhone browser mein speech recognition available nahi. Text command use karo.");
      return;
    }
    if (!paired) {
      setError("Pehle JARVIS PC se connect karo.");
      return;
    }
    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.lang = "en-IN";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => { setListening(true); setError(""); setMode("LISTENING"); };
      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || "";
        if (transcript.trim()) sendCommand(transcript);
      };
      recognition.onerror = (event) => setError(`Voice input: ${event.error || "failed"}. Text command bhi use kar sakte ho.`);
      recognition.onend = () => setListening(false);
      recognition.start();
    } catch (err) {
      setListening(false);
      setError(String(err?.message || "Microphone start nahi hua."));
    }
  };

  const stopVoice = () => {
    try { recognitionRef.current?.stop(); } catch {}
    setListening(false);
  };

  const disconnect = () => {
    localStorage.removeItem(TOKEN_KEY);
    setPaired(false);
    setToken("");
    setConnection("PAIRING REQUIRED");
    try { wsRef.current?.close(); } catch {}
    addActivity("MOBILE DEVICE UNPAIRED");
  };

  return (
    <main className="jm-shell">
      <div className="jm-grid" aria-hidden="true" />
      <header className="jm-header">
        <div className="jm-brand"><span className="jm-brand-mark">J</span><div><b>JARVIS</b><small>MOBILE COMPANION</small></div></div>
        <div className={`jm-status ${paired ? "is-online" : ""}`}><i />{connection}</div>
      </header>

      {!token ? (
        <section className="jm-pair-card">
          <div className="jm-kicker">SECURE DEVICE PAIRING</div>
          <h1>Connect your<br /><em>JARVIS Core.</em></h1>
          <p>PC par JARVIS Mobile Gateway start karne ke baad terminal mein dikhne wala pairing code yahan paste karo.</p>
          <form onSubmit={savePairing}>
            <label htmlFor="jm-token">PAIRING CODE</label>
            <input id="jm-token" value={tokenDraft} onChange={(e) => setTokenDraft(e.target.value)} placeholder="Paste secure pairing code" autoCapitalize="none" autoCorrect="off" />
            <button className="jm-primary" type="submit">PAIR DEVICE <span>→</span></button>
          </form>
          {error && <p className="jm-error">{error}</p>}
          <p className="jm-footnote">Code is stored only in this browser on this iPhone. Kisi aur ke saath share mat karna.</p>
        </section>
      ) : (
        <>
          <section className="jm-core-card">
            <div className="jm-orb-wrap"><div className={`jm-orb ${listening ? "is-listening" : ""}`}><span /><b>J</b></div></div>
            <div className="jm-kicker">PERSONAL AI SYSTEM</div>
            <h1>{listening ? "I’m listening." : paired ? "At your command." : "Connecting…"}</h1>
            <div className="jm-mode">{mode}</div>
            <p className="jm-message">{message}</p>
            <button className={`jm-voice ${listening ? "is-active" : ""}`} onClick={listening ? stopVoice : startVoice} disabled={!paired}>
              <span className="jm-mic">{listening ? "Ⅱ" : "●"}</span>
              {listening ? "STOP LISTENING" : "TAP TO SPEAK"}
            </button>
            {!voiceSupported && <div className="jm-hint">Voice recognition is not available in this browser. Text command use karo.</div>}
          </section>

          <form className="jm-command" onSubmit={(e) => { e.preventDefault(); sendCommand(command); }}>
            <input value={command} onChange={(e) => setCommand(e.target.value)} placeholder="Talk to JARVIS…" autoComplete="off" />
            <button type="submit" aria-label="Send command" disabled={!paired || !command.trim()}>↑</button>
          </form>

          {error && <div className="jm-error jm-error-box">{error}</div>}

          <section className="jm-activity">
            <div className="jm-section-title"><span>LIVE ACTIVITY</span><small>{activity.length.toString().padStart(2, "0")} EVENTS</small></div>
            {activity.length ? activity.map((item, index) => <div className="jm-event" key={`${item.time}-${index}`}><time>{item.time}</time><span>{item.text}</span></div>) : <div className="jm-empty">JARVIS activity yahan appear hogi.</div>}
          </section>

          <footer className="jm-footer">
            <label className="jm-toggle"><input type="checkbox" checked={speakReplies} onChange={(e) => setSpeakReplies(e.target.checked)} /><span /> READ REPLIES ALOUD</label>
            <button onClick={disconnect}>UNPAIR DEVICE</button>
          </footer>
        </>
      )}
      <div className="jm-bottom-label">LOCAL-FIRST INTELLIGENCE <span>•</span> SECURE LINK</div>
    </main>
  );
}
