import React, { useEffect, useMemo, useRef, useState } from "react";
import ChatMode from "./ChatMode.jsx";
import "./hud.css";
import "./hud_upgrade.css";
import ImageStudio from "./ImageStudio.jsx";
import "./image_generation_core.css";
import MusicOverlay from "./MusicOverlay.jsx";
import MusicHUD from "./MusicHUD.jsx";
import GalleryOverlay from "./GalleryOverlay.jsx";
import JarvisAvatar from "./components/JarvisAvatar.jsx";
import "./music_gallery.css";

const STATES = [
  "STARTING",
  "IDLE",
  "LISTENING",
  "THINKING",
  "SPEAKING",
  "EXECUTING",
];


function Icon({ type, size = 18 }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };

  const paths = {
    home: (
      <>
        <path d="m3 10 9-7 9 7" />
        <path d="M5 9.5V21h14V9.5" />
        <path d="M9 21v-7h6v7" />
      </>
    ),
    system: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
      </>
    ),
    apps: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    browser: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3c2.4 2.5 3.5 5.5 3.5 9S14.4 18.5 12 21c-2.4-2.5-3.5-5.5-3.5-9S9.6 5.5 12 3Z" />
      </>
    ),
    youtube: (
      <>
        <rect x="3" y="6" width="18" height="12" rx="3" />
        <path d="m10 9 5 3-5 3Z" />
      </>
    ),
    tools: (
      <>
        <path d="m14 7 3-3 3 3-3 3" />
        <path d="m11 14-7 7" />
        <path d="M14 10 7 17" />
        <path d="M8 6a5 5 0 0 0 6 6" />
      </>
    ),
    notes: (
      <>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="M8 8h8M8 12h8M8 16h5" />
      </>
    ),
    chat: (
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v7a2.5 2.5 0 0 1-2.5 2.5H11l-4.8 4v-4.2A2.5 2.5 0 0 1 4 12.5Z" />
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 13.5a7.9 7.9 0 0 0 0-3l2-1.3-2-3.4-2.3 1a8.1 8.1 0 0 0-2.6-1.5L13.7 3h-3.4l-.4 2.3a8.1 8.1 0 0 0-2.6 1.5l-2.3-1-2 3.4 2 1.3a7.9 7.9 0 0 0 0 3l-2 1.3 2 3.4 2.3-1a8.1 8.1 0 0 0 2.6 1.5l.4 2.3h3.4l.4-2.3a8.1 8.1 0 0 0 2.6-1.5l2.3 1 2-3.4Z" />
      </>
    ),
    mic: (
      <>
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8" />
      </>
    ),
    wave: (
      <>
        <path d="M3 12h2M7 9v6M11 6v12M15 8v8M19 10v4M21 12h0" />
      </>
    ),
    brain: (
      <>
        <path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 3 3" />
        <path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-3 3" />
        <path d="M9 4v16M15 4v16M9 9h6M9 15h6" />
      </>
    ),
    gear: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1" />
      </>
    ),
    check: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m8 12 2.5 2.5L16 9" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 5 5" />
      </>
    ),
    code: <path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 4l-4 16" />,
    music: (
      <>
        <path d="M9 18V5l10-2v13" />
        <circle cx="6" cy="18" r="3" />
        <circle cx="16" cy="16" r="3" />
      </>
    ),
    monitor: (
      <>
        <rect x="3" y="4" width="18" height="12" rx="1.5" />
        <path d="M9 20h6M12 16v4" />
      </>
    ),
    grid: (
      <>
        <rect x="4" y="4" width="6" height="6" />
        <rect x="14" y="4" width="6" height="6" />
        <rect x="4" y="14" width="6" height="6" />
        <rect x="14" y="14" width="6" height="6" />
      </>
    ),
    image: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <circle cx="8.5" cy="9" r="1.5" />
        <path d="m5 17 4.5-4.5 3 3 2.5-2.5L19 17" />
      </>
    ),
  };

  return <svg {...common}>{paths[type] || paths.system}</svg>;
}

function Orb({
  mode, result, connected, imageStudioRef, imagePhase, imageUrl, musicState, galleryImageUrl,
  musicMode,
  onImageReady, onImagePhaseChange, onImageRemove,
}) {
  const active = mode !== "IDLE" && mode !== "STARTING";
  const generating = imagePhase === "generating";
  const ready = imagePhase === "result" && imageUrl;
  let label = "JARVIS";
  if (!connected) label = "JARVIS ONLINE";
  else if (generating) label = "GENERATING IMAGE";
  else if (ready) label = "IMAGE READY";
  else if (mode === "THINKING") label = "THINKING";
  else if (mode === "EXECUTING") label = "EXECUTING";
  else if (result) label = "EXECUTED";
  return (
    <div className={`orb-scene orb-${String(mode).toLowerCase()} ${result ? "orb-result" : ""} ${generating ? "orb-image-generating" : ""} ${ready ? "orb-image-ready" : ""}`}>
      <div className="ring ring-1" />
      <div className="core-shell">
        <div className="core-grid" /><div className="core-glow" /><div className="core-dot" />
        {galleryImageUrl && (
          <div className="jarvis-core-gallery-image">
            <img
              src={galleryImageUrl}
              alt="JARVIS Gallery"
            />
          </div>
        )}
        <MusicOverlay
          active={musicMode}
          playing={musicState?.playing}
          title={musicState?.title}
          artist={musicState?.artist}
          lyric={musicState?.lyric}
          progress={musicState?.duration ? (musicState.position / musicState.duration) * 100 : 0}
        />
        <ImageStudio
          ref={imageStudioRef}
          embedded
          onPhaseChange={onImagePhaseChange}
          onImageReady={onImageReady}
          onRemove={onImageRemove}
        />
        {!generating && !ready && (
          <div className={`core-label ${!connected ? "core-connecting" : ""}`}>
            <span>{label}</span>{!connected && <small>CONNECTING...</small>}
          </div>
        )}
        {ready && (
          <div className="jarvis-inline-image-actions">
            <button type="button" onClick={() => imageStudioRef.current?.save?.()}>SAVE</button>
            <button type="button" className="remove" onClick={() => imageStudioRef.current?.remove?.()}>REMOVE</button>
          </div>
        )}
      </div>
      {active && !generating && !ready && <div className="spark-field" />}
    </div>
  );
}

function greetingForHour(hour) {
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  if (hour < 21) return "Good Evening";
  return "Good Night";
}

function isIndianMarketOpen(date) {
  const ist = new Date(date.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
  const day = ist.getDay();
  const mins = ist.getHours() * 60 + ist.getMinutes();
  return day >= 1 && day <= 5 && mins >= 9 * 60 + 15 && mins <= 15 * 60 + 30;
}

function formatMarketPrice(value) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatMarketChange(value) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  const n = Number(value);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}`;
}

function formatMarketPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  const n = Number(value);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

async function fetchYahooQuote(symbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1d&interval=5m`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`Market request failed: ${response.status}`);
  const payload = await response.json();
  const meta = payload?.chart?.result?.[0]?.meta;
  if (!meta) throw new Error("Market quote missing");
  const price = meta.regularMarketPrice ?? meta.previousClose;
  const change = meta.regularMarketChange ?? null;
  const percent = meta.regularMarketChangePercent ?? null;
  return { symbol, price, change, percent };
}

const MARKET_STOCKS = [
  ["RELIANCE.BO", "Reliance"],
  ["HDFCBANK.BO", "HDFC Bank"],
  ["TCS.BO", "TCS"],
  ["ICICIBANK.BO", "ICICI Bank"],
  ["INFY.BO", "Infosys"],
];

const MARKET_INDICES = [
  ["^BSESN", "Sensex"],
  ["^NSEI", "Nifty 50"],
  ["^NSEBANK", "Bank Nifty"],
  ["^CNXIT", "Nifty IT"],
];

function Movable({ id, editMode, positions, setPositions, children, className = "" }) {
  const pos = positions[id] || { x: 0, y: 0 };
  const dragRef = useRef(null);

  const updatePos = (x, y) => {
    setPositions((prev) => ({ ...prev, [id]: { x, y } }));
  };

  const onPointerDown = (e) => {
    if (!editMode) return;
    if (e.target.closest("button, input, textarea, a, select")) {
      e.currentTarget.focus();
      return;
    }

    e.currentTarget.focus();
    dragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      baseX: pos.x,
      baseY: pos.y,
    };
    e.currentTarget.setPointerCapture?.(e.pointerId);
    e.preventDefault();
  };

  const onPointerMove = (e) => {
    const d = dragRef.current;
    if (!d || d.pointerId !== e.pointerId) return;
    updatePos(
      Math.round(d.baseX + e.clientX - d.startX),
      Math.round(d.baseY + e.clientY - d.startY),
    );
  };

  const endDrag = (e) => {
    if (dragRef.current?.pointerId === e.pointerId) dragRef.current = null;
  };

  const onKeyDown = (e) => {
    if (!editMode) return;
    const step = e.shiftKey ? 20 : 8;
    let dx = 0;
    let dy = 0;
    if (e.key === "ArrowLeft") dx = -step;
    else if (e.key === "ArrowRight") dx = step;
    else if (e.key === "ArrowUp") dy = -step;
    else if (e.key === "ArrowDown") dy = step;
    else return;
    e.preventDefault();
    updatePos(pos.x + dx, pos.y + dy);
  };

  return (
    <div
      className={`layout-movable ${editMode ? "layout-editable" : ""} ${className}`}
      style={{ transform: `translate3d(${pos.x}px, ${pos.y}px, 0)` }}
      tabIndex={editMode ? 0 : -1}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onKeyDown={onKeyDown}
      data-layout-id={id}
    >
      {editMode && <div className="layout-grip" aria-hidden="true">DRAG</div>}
      {children}
    </div>
  );
}

function Panel({ title, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-title">
        <span>{title}</span>
        <i />
      </div>
      {children}
    </section>
  );
}

function formatPlaybackTime(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value < 0) return "00:00";
  const total = Math.floor(value);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
    : `${minutes}:${String(secs).padStart(2, "0")}`;
}

export default function App() {
  const [mode, setMode] = useState("STARTING");
  const [message, setMessage] = useState("JARVIS CORE INITIALIZING...");
  const [command, setCommand] = useState("");
  const [commandTime, setCommandTime] = useState("");
  const [responseTime, setResponseTime] = useState("");
  const [promptOpen, setPromptOpen] = useState(false);
  const [promptText, setPromptText] = useState("");
  const [result, setResult] = useState("");
  const [chatgptImageUrl, setChatgptImageUrl] = useState("");
  const [sourceFixReport, setSourceFixReport] = useState(null);
  const [activity, setActivity] = useState([]);
  const [connected, setConnected] = useState(false);
  const [greeting] = useState(() => greetingForHour(new Date().getHours()));
  const [now, setNow] = useState(() => new Date());
  const [editMode, setEditMode] = useState(false);
  const [musicMode, setMusicMode] = useState(false);
  const [chatMode, setChatMode] = useState(false);
  const [musicState, setMusicState] = useState({
    active: false,
    playing: false,
    title: "",
    artist: "",
    lyric: "",
    position: 0,
    duration: 0,
    volume: 0.85,
  });
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [galleryImages, setGalleryImages] = useState([]);
  const [gallerySelected, setGallerySelected] = useState(null);
  const [screenMode, setScreenMode] = useState(false);
  const [youtubeProgress, setYoutubeProgress] = useState(null);
  const lastYoutubeTitleRef = useRef("");
  const galleryInputRef = useRef(null);
  const [navActive, setNavActive] = useState("Home");
  const [positions, setPositions] = useState(() => {
    try {
      const raw = localStorage.getItem("jarvis-hud-layout");
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });

  const [system, setSystem] = useState({
    cpu: null,
    ram: null,
    gpu: null,
    battery: null,
    online: null,
  });

  const [market, setMarket] = useState({
    open: false,
    symbol: "BSE",
    sensex: null,
    change: null,
    percent: null,
    stocks: [],
    indices: [],
    feed: "Yahoo Finance",
  });

  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const imageStudioRef = useRef(null);
  const commandInputRef = useRef(null);
  const [imagePhase, setImagePhase] = useState("idle");
  const [imageUrl, setImageUrl] = useState("");

  const pushActivity = (text) => {
    const now = new Date();
    const time = now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    setActivity((prev) => [
      { time, text: String(text).slice(0, 100) },
      ...prev,
    ].slice(0, 8));
  };

  const openGallery = () => {
    const allowed = window.confirm(
      "Boss, JARVIS ko aapki Gallery access karne dena chahte ho?"
    );
    if (!allowed) {
      pushActivity("GALLERY // Access denied");
      return;
    }
    setNavActive("Gallery");
    setGalleryOpen(true);
    requestAnimationFrame(() => galleryInputRef.current?.click());
  };

  const copyGalleryImageToClipboard = async (file) => {
    try {
      if (!file || !navigator.clipboard || typeof ClipboardItem === "undefined") {
        throw new Error("Image clipboard API unavailable");
      }

      const blob = file instanceof Blob ? file : await fetch(file.url).then((r) => r.blob());
      const type = file.type || blob.type || "image/png";
      await navigator.clipboard.write([
        new ClipboardItem({ [type]: blob }),
      ]);

      pushActivity(`GALLERY // ${file.name || "Selected image"} ready for ChatGPT`);
      return true;
    } catch (error) {
      console.warn("[JARVIS Gallery] Clipboard image copy failed:", error);
      pushActivity("GALLERY // Image selected; clipboard permission unavailable");
      return false;
    }
  };

  const onGalleryFiles = (event) => {
    const files = Array.from(event.target.files || []).filter((file) =>
      file.type.startsWith("image/")
    );

    const next = files.map((file) => ({
      name: file.name,
      url: URL.createObjectURL(file),
      file,
    }));

    setGalleryImages((previous) => {
      previous.forEach((image) => {
        try {
          URL.revokeObjectURL(image.url);
        } catch {}
      });
      return next;
    });

    if (next.length) {
      const selected = next[0];
      setGallerySelected(selected);
      pushActivity(`GALLERY // ${next.length} image(s) loaded`);

      // Keep the selected original File available to the browser clipboard.
      // This lets the Python operator paste the exact image into ChatGPT later.
      void copyGalleryImageToClipboard(selected.file);
      pushActivity(`GALLERY // Selected: ${selected.name || "image"}`);
    }

    event.target.value = "";
  };

  const handleNav = (label) => {
    if (label === "Chat") { setNavActive("Chat"); setChatMode(true); return; }
    if (label === "Music") {
      setNavActive("Music");
      handleCommand("Play Music");
      return;
    }
    if (label === "Gallery") {
      openGallery();
      return;
    }
    setNavActive(label);
    pushActivity(`NAV // ${label}`);
  };

  const sendWebsitePrompt = () => {
    const text = String(promptText || "").trim();
    if (!text) return;
    handleCommand(text);
    setPromptOpen(false);
  };

  useEffect(() => {
    if (String(command || "").trim()) {
      setCommandTime(new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
      }));
    }
  }, [command]);

  useEffect(() => {
    if (String(result || message || "").trim()) {
      setResponseTime(new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
      }));
    }
  }, [result, message]);

  const startImageGeneration = (prompt) => {
    const clean = String(prompt || "").trim();
    if (!clean) {
      setCommand("generate image of ");
      requestAnimationFrame(() => commandInputRef.current?.focus());
      setMessage("Boss, image kis cheez ki generate karni hai?");
      return;
    }
    setCommand(`generate image of ${clean}`);
    setResult("");
    pushActivity(`IMAGE // ${clean}`);
    imageStudioRef.current?.generate?.(clean);
  };

  const handleCommand = (text) => {
    const clean = String(text || "").trim();
    if (!clean) return;
    const a = clean.match(/^(?:hey\s+)?jarvis[\s,\-:]*(?:please\s+)?(?:generate|create|make|banao|bana)\s+(?:an?\s+)?image(?:\s+of)?\s+(.+)$/i);
    const b = clean.match(/^(?:generate|create|make|banao|bana)\s+(?:an?\s+)?image(?:\s+of)?\s+(.+)$/i);
    const prompt = a?.[1]?.trim() || b?.[1]?.trim();
    if (prompt) { startImageGeneration(prompt); return; }
    sendToJarvis(clean);
  };

  const sendToJarvis = (text) => {
    const clean = String(text || "").trim();

    if (!clean) return;

    setCommand(clean);
    setResult("");
    pushActivity(`YOU // ${clean}`);

    if (
      wsRef.current &&
      wsRef.current.readyState === WebSocket.OPEN
    ) {
      wsRef.current.send(
        JSON.stringify({
          source: "HUD",
          type: "COMMAND",
          command: clean,
        })
      );
    } else {
      setResult("JARVIS bridge disconnected.");
      pushActivity("ERROR // Bridge disconnected");
    }
  };


  const stopJarvis = () => {
    setResult("");
    pushActivity("YOU // Stop");

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          source: "HUD",
          type: "COMMAND",
          command: "stop",
        })
      );
    }
  };

  useEffect(() => {
    let dead = false;

    const connect = () => {
      if (dead) return;

      let ws;

      try {
        const _jarvisWsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const _jarvisWsHost = window.location.hostname || "127.0.0.1";
ws = new WebSocket(`${_jarvisWsProtocol}//${_jarvisWsHost}:8765`);
        wsRef.current = ws;
      } catch {
        reconnectRef.current = setTimeout(connect, 2000);
        return;
      }

      ws.onopen = () => {
        setConnected(true);
        pushActivity("HUD BRIDGE CONNECTED");
      };

      ws.onclose = () => {
        setConnected(false);

        if (!dead) {
          reconnectRef.current = setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        setConnected(false);
      };

      ws.onmessage = (evt) => {
        try {
          const d = JSON.parse(evt.data || "{}");

          if (d.source !== "JARVIS") return;

          if (d.type === "STATE") {
            setMode(String(d.state || "IDLE").toUpperCase());
          }

          if (d.type === "MESSAGE") {
            setMessage(String(d.message || ""));
          }

          if (d.type === "ACTIVITY") {
            pushActivity(d.text || "");
          }

          if (d.type === "SYSTEM") {
            setSystem((p) => ({
              ...p,
              ...d,
            }));
          }

          if (d.type === "YOUTUBE_PROGRESS") {
            const title = String(d.title || "YouTube video");
            setYoutubeProgress({
              title,
              currentTime: Number(d.current_time || 0),
              duration: Number(d.duration || 0),
              paused: Boolean(d.paused),
              receivedMs: Date.now(),
            });
            if (title !== lastYoutubeTitleRef.current) {
              lastYoutubeTitleRef.current = title;
              pushActivity(`YOUTUBE // ${title}`);
            }
          }

          if (d.type === "WAKE") {
            pushActivity("WAKE // Hey Jarvis detected");
            setMode("LISTENING");
          }
          if (d.type === "COMMAND") {
            const c = String(d.text || d.command || "").trim();

            setCommand(c);
            setResult("");
            pushActivity(`YOU // ${c}`);

            const imageA = c.match(
              /^(?:hey\s+)?jarvis[\s,:-]*(?:please\s+)?(?:generate|create|make|banao|bana)\s+(?:an?\s+)?image(?:\s+of)?\s+(.+)$/i
            );
            const imageB = c.match(
              /^(?:generate|create|make|banao|bana)\s+(?:an?\s+)?image(?:\s+of)?\s+(.+)$/i
            );

            const imagePrompt = imageA?.[1]?.trim() || imageB?.[1]?.trim();

            if (imagePrompt) {
              startImageGeneration(imagePrompt);
            }
          }

          if (d.type === "RESULT") {
            const msg = String(
              d.message || "Execution finished"
            );

            setResult(msg);
            pushActivity(`RESULT // ${msg}`);
          }

          if (d.type === "MARKET") {
            setMarket((p) => ({
              ...p,
              ...d,
              stocks: Array.isArray(d.stocks) ? d.stocks : p.stocks,
              indices: Array.isArray(d.indices) ? d.indices : p.indices,
            }));
          }

          if (d.type === "MUSIC_MODE") {
            setMusicMode(Boolean(d.active));
            setNavActive(Boolean(d.active) ? "Music" : "Home");
            pushActivity(Boolean(d.active) ? "MUSIC MODE // ON" : "MUSIC MODE // OFF");
          }

          if (d.type === "MUSIC") {
            const track = d.track || {};
            const musicActive = Boolean(d.active);
            if (musicActive && d.auto_mode !== false) setMusicMode(true);
            if (!musicActive) setMusicMode(false);
            setMusicMode(Boolean(d.active));
            setMusicState({
              active: Boolean(d.active),
              playing: Boolean(d.playing),
              title: String(track.title || d.title || "Music"),
              artist: String(track.artist || d.artist || ""),
              lyric: String(d.lyric || ""),
              position: Number(d.position || 0),
              duration: Number(d.duration || track.duration || 0),
              volume: Number(d.volume ?? 0.85),
            });
            setNavActive(Boolean(d.active) ? "Music" : "Home");
            if (d.active && (track.title || d.title)) pushActivity(`MUSIC // ${track.title || d.title}`);
          }
        } catch {
          // Ignore malformed bridge messages.
        }
      };
    };

    connect();

    return () => {
      dead = true;

      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("jarvis-hud-layout", JSON.stringify(positions));
    } catch {
      // Layout persistence is optional.
    }
  }, [positions]);

  // Keep the command console reachable after older/saved layouts pushed it below the viewport.
  useEffect(() => {
    setPositions((prev) => {
      const current = prev?.command;
      if (!current || current.y > 120 || current.y < -120) {
        return { ...prev, command: { x: 0, y: 0 } };
      }
      return prev;
    });
  }, []);

  useEffect(() => {
    let dead = false;

    const loadMarket = async () => {
      try {
        const [stocks, indices] = await Promise.all([
          Promise.all(MARKET_STOCKS.map(async ([symbol, name]) => ({
            name,
            ...(await fetchYahooQuote(symbol)),
          }))),
          Promise.all(MARKET_INDICES.map(async ([symbol, name]) => ({
            name,
            ...(await fetchYahooQuote(symbol)),
          }))),
        ]);

        if (dead) return;
        const sensex = indices.find((x) => x.name === "Sensex");
        setMarket((prev) => ({
          ...prev,
          open: isIndianMarketOpen(new Date()),
          stocks,
          indices,
          sensex: sensex?.price ?? prev.sensex,
          change: sensex?.change ?? prev.change,
          percent: sensex?.percent ?? prev.percent,
          symbol: "BSE",
          feed: "Yahoo Finance",
        }));
      } catch {
        if (!dead) {
          setMarket((prev) => ({
            ...prev,
            open: isIndianMarketOpen(new Date()),
            feed: prev.stocks?.length ? prev.feed : "LIVE FEED UNAVAILABLE",
          }));
        }
      }
    };

    loadMarket();
    const timer = setInterval(loadMarket, 60000);
    return () => {
      dead = true;
      clearInterval(timer);
    };
  }, []);

  const flowIndex = useMemo(() => {
    if (mode === "LISTENING") return 0;
    if (mode === "THINKING") return 1;
    if (mode === "EXECUTING") return 2;
    if (mode === "SPEAKING") return 3;
    if (result) return 4;
    return -1;
  }, [mode, result]);

  const pct = (v) =>
    v == null ? "--" : `${Math.round(v)}%`;

  const timeString = now.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  const dateString = now.toLocaleDateString([], {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const modeText =
    mode === "STARTING"
      ? "INITIALIZING"
      : mode === "IDLE"
      ? "STANDBY"
      : mode;

  const quick = [
    ["image", "Image Generation", "IMAGE_GENERATION"],
    ["code", "Open VS Code", "Open VS Code"],
    ["browser", "Open Chrome", "Open Chrome"],
    ["youtube", "Open YouTube", "Open YouTube"],
    ["chat", "Open ChatGPT", "Open ChatGPT"],
    ["music", "Play Music", "Play Music"],
    ["monitor", "System Info", "System Info"],
  ];

  const nav = [
    ["home", "Home"],
    ["system", "System"],
    ["apps", "Apps"],
    ["music", "Music"],
    ["image", "Gallery"],
    ["tools", "Tools"],
    ["notes", "Notes"],
    ["chat", "Chat"],
    ["settings", "Settings"],
  ];

  if (chatMode && !musicMode) {
    return <ChatMode connected={connected} message={message} result={result} mode={mode}
      onCommand={sendToJarvis} onBack={() => { setChatMode(false); setNavActive("Home"); }} />;
  }
  if (musicMode) {
    return (
      <MusicHUD
        musicState={musicState}
        connected={connected}
        onCommand={sendToJarvis}
      />
    );
  }
  return (
    <div className={`jarvis-app mode-${mode.toLowerCase()} ${editMode ? "layout-editing" : ""}`}>
      <div className="background-stars" />
      <div className="background-haze" />
      <div className="landscape" />

      <header className="topbar">
        <Movable id="brand" editMode={editMode} positions={positions} setPositions={setPositions} className="brand-movable">
          <div className="brand">
            <div className="brand-main">JARVIS</div>
          </div>
        </Movable>

        <Movable id="slogan" editMode={editMode} positions={positions} setPositions={setPositions} className="slogan-movable">
          <div className="slogan">This is what Farhan's curiosity built.</div>
        </Movable>

        <Movable id="profile" editMode={editMode} positions={positions} setPositions={setPositions} className="profile-movable">
          <div className="profile">
            <div className="avatar">MF</div>
            <div>
              <b>Farhan</b>
              <small>{greeting}</small>
            </div>
            <span>MF</span>
          </div>
        </Movable>
      </header>

      <button
        type="button"
        onClick={() => setScreenMode((v) => !v)}
        style={{
          position: "fixed",
          top: 18,
          right: 24,
          zIndex: 10001,
          padding: "9px 15px",
          borderRadius: 999,
          border: screenMode
            ? "1px solid rgba(80,220,255,0.95)"
            : "1px solid rgba(80,180,255,0.45)",
          background: screenMode
            ? "rgba(20,100,130,0.35)"
            : "rgba(5,12,20,0.72)",
          color: "#bff7ff",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.12em",
          cursor: "pointer",
          boxShadow: screenMode
            ? "0 0 25px rgba(30,210,255,0.35)"
            : "0 8px 25px rgba(0,0,0,0.25)",
          backdropFilter: "blur(10px)",
        }}
      >
        {screenMode ? "SCREEN MODE ON" : "SCREEN MODE"}
      </button>

      {screenMode && (
        <div style={{
          position: "fixed", right: 18, bottom: 230, zIndex: 10002,
          display: "flex", gap: 7, pointerEvents: "auto",
        }}>
          <button type="button" onClick={() => sendToJarvis("describe my screen")} style={{
            border: "1px solid rgba(80,220,255,.65)", borderRadius: 8,
            background: "rgba(3,18,28,.92)", color: "#bff7ff", padding: "8px 10px",
            fontSize: 10, fontWeight: 700, letterSpacing: ".08em", cursor: "pointer",
          }}>ANALYZE SCREEN</button>
          <button type="button" onClick={() => sendToJarvis("save screen notes")} style={{
            border: "1px solid rgba(80,220,255,.65)", borderRadius: 8,
            background: "rgba(3,18,28,.92)", color: "#bff7ff", padding: "8px 10px",
            fontSize: 10, fontWeight: 700, letterSpacing: ".08em", cursor: "pointer",
          }}>SAVE STUDY NOTES</button>
        </div>
      )}

      {youtubeProgress && now.getTime() - youtubeProgress.receivedMs < 10000 && (
        <div style={{
          position: "fixed", top: 62, right: 24, zIndex: 10001, width: 280,
          padding: "10px 12px", border: "1px solid rgba(80,220,255,.45)",
          borderRadius: 10, background: "rgba(3,12,20,.88)", color: "#bff7ff",
          backdropFilter: "blur(12px)", boxShadow: "0 8px 24px rgba(0,0,0,.28)",
          pointerEvents: "none",
        }}>
          <div style={{ fontSize: 9, fontWeight: 800, letterSpacing: ".12em", opacity: .78 }}>YOUTUBE PLAYBACK</div>
          <div style={{ marginTop: 4, fontSize: 11, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{youtubeProgress.title}</div>
          <div style={{ marginTop: 4, fontSize: 10, opacity: .82 }}>
            {formatPlaybackTime(youtubeProgress.currentTime)} / {formatPlaybackTime(youtubeProgress.duration)} · {youtubeProgress.paused ? "PAUSED" : "PLAYING"}
          </div>
        </div>
      )}

      <div className={`layout-tools ${editMode ? "active" : ""}`}>
        <button type="button" onClick={() => setEditMode((v) => !v)}>
          {editMode ? "SAVE LAYOUT" : "EDIT LAYOUT"}
        </button>
        {editMode && <span>Click a panel, drag it, then use ÃƒÂ¢Ã¢â‚¬Â Ã‚Â ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Ëœ ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Å“</span>}
      </div>

      <aside className="sidebar">
        <Movable id="clock" editMode={editMode} positions={positions} setPositions={setPositions}>
          <div className="clock-block">
            <div className="big-time">{timeString}</div>
            <div>{dateString}</div>
          </div>
        </Movable>

        <Movable id="nav" editMode={editMode} positions={positions} setPositions={setPositions}>
          <div className="nav-list">
            {nav.map(([icon, label], i) => (
              <button
                key={label}
                className={navActive === label ? "active" : ""}
                onClick={() => handleNav(label)}
              >
                <Icon type={icon} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </Movable>

        <Movable id="quote" editMode={editMode} positions={positions} setPositions={setPositions}>
          <div className="quote">
            ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œProgress is a series of small wins.ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â
            <span>ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â JARVIS</span>
          </div>
        </Movable>
      </aside>

      <aside className="left-column">
        <Movable id="market" editMode={editMode} positions={positions} setPositions={setPositions} className="market-movable">
          <Panel title="BSE MARKET">
            <div className="market-status-row">
              <span className={isIndianMarketOpen(now) ? "market-live" : "market-closed-label"}>
                {isIndianMarketOpen(now) ? "MARKET OPEN" : "MARKET CLOSED"}
              </span>
              <small>{market.feed || "LIVE"}</small>
            </div>

            <div className="market-stocks">
              {(market.stocks?.length ? market.stocks : MARKET_STOCKS.map(([symbol, name]) => ({ symbol, name, price: null, change: null, percent: null }))).map((stock) => (
                <button
                  type="button"
                  className="market-stock"
                  key={stock.symbol}
                  onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(`${stock.name} stock market`)}`, "_blank", "noopener,noreferrer")}
                  title={`Open ${stock.name} in Google`}
                >
                  <span>
                    <b>{stock.name}</b>
                    <small>{stock.symbol.replace(".BO", "")}</small>
                  </span>
                  <span className="market-price">
                    <b>INR {formatMarketPrice(stock.price)}</b>
                    <small className={Number(stock.change) >= 0 ? "market-up" : "market-down"}>
                      {formatMarketChange(stock.change)} {formatMarketPercent(stock.percent)}
                    </small>
                  </span>
                </button>
              ))}
            </div>

            <div className="market-index-line" />

            <div className="market-indices">
              {(market.indices?.length ? market.indices : MARKET_INDICES.map(([symbol, name]) => ({ symbol, name, price: null, change: null, percent: null }))).map((index) => (
                <button
                  type="button"
                  className="market-index"
                  key={index.symbol}
                  onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(`${index.name} stock market`)}`, "_blank", "noopener,noreferrer")}
                  title={`Open ${index.name} in Google`}
                >
                  <span>{index.name}</span>
                  <b>{formatMarketPrice(index.price)}</b>
                </button>
              ))}
            </div>
          </Panel>
        </Movable>

        <Movable id="quick" editMode={editMode} positions={positions} setPositions={setPositions} className="quick-movable">
          <Panel title="QUICK ACTIONS">
            <div className="quick-grid">
              {quick.map(([icon, label, cmd]) => (
                <button key={label} onClick={() => cmd === "IMAGE_GENERATION" ? startImageGeneration("") : handleCommand(cmd)}>
                  <Icon type={icon} size={17} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </Panel>
        </Movable>
      </aside>

      <main className="center-stage">
        <Movable id="core" editMode={editMode} positions={positions} setPositions={setPositions} className="core-movable">
          <div className="center-header">
            <span>ARC REACTOR</span>
            <b>{modeText}</b>
          </div>

          <Orb
            mode={mode}
            result={result}
            connected={connected}
        galleryImageUrl={gallerySelected?.url || ""}
            imageStudioRef={imageStudioRef}
            imagePhase={imagePhase}
            imageUrl={imageUrl}
            musicState={musicState}
            musicMode={musicMode}
            onImagePhaseChange={setImagePhase}
            onImageReady={(url) => { setImageUrl(url); setResult("Image generated successfully."); pushActivity("IMAGE // Generated successfully"); }}
            onImageRemove={() => { setImageUrl(""); setImagePhase("idle"); setResult(""); pushActivity("IMAGE // Removed"); }}
          />

          <div className="core-response">
            <div className="core-response-main">
              {mode === "LISTENING" ? "Haan Boss" : message}
            </div>
            <div className="core-response-sub">
              {mode === "THINKING"
                ? "Analyzing command..."
                : mode === "EXECUTING"
                ? "Executing command..."
                : mode === "LISTENING"
                ? "Listening for your commandÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"
                : mode === "SPEAKING"
                ? "RespondingÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"
                : "Ready"}
            </div>
          </div>

          <div className="core-wave">
            <span /><span /><span /><span /><span /><span /><span /><span /><span />
          </div>
        </Movable>
      </main>

      {screenMode && (
        <div
          data-jarvis-screen-avatar="true"
          style={{
            position: "fixed",
            right: 18,
            bottom: 18,
            width: 170,
            height: 205,
            zIndex: 10000,
            pointerEvents: "none",
            background: "transparent",
          }}
        >
          <JarvisAvatar
            state="idle"
            width={170}
            height={205}
          />
          <div
            style={{
              position: "absolute",
              left: "50%",
              bottom: 8,
              transform: "translateX(-50%)",
              color: "#8eeaff",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.16em",
              textShadow: "0 0 12px rgba(40,220,255,0.8)",
              whiteSpace: "nowrap",
            }}
          >
            JARVIS // SCREEN VISION
          </div>
        </div>
      )}

      <aside className="right-column">
        <Movable id="system" editMode={editMode} positions={positions} setPositions={setPositions} className="right-movable system-movable">
          <Panel title="SYSTEM STATUS">
            <div className="metric">
              <span>CPU</span><b>{pct(system.cpu)}</b><i><em style={{ width: system.cpu == null ? "8%" : `${system.cpu}%` }} /></i>
            </div>
            <div className="metric">
              <span>RAM</span><b>{pct(system.ram)}</b><i><em style={{ width: system.ram == null ? "8%" : `${system.ram}%` }} /></i>
            </div>
            <div className="metric">
              <span>GPU</span><b>{pct(system.gpu)}</b><i><em style={{ width: system.gpu == null ? "8%" : `${system.gpu}%` }} /></i>
            </div>
            <div className="metric">
              <span>Battery</span><b>{pct(system.battery)}</b><i><em style={{ width: system.battery == null ? "8%" : `${system.battery}%` }} /></i>
            </div>
            <div className="system-triad">
              <div><b>NETWORK</b><span>{system.online === false ? "Offline" : "Connected"}</span><small>Network</small></div>
              <div><b>JARVIS</b><span>Online</span><small>JARVIS</small></div>
              <div><b>SECURITY</b><span>Normal</span><small>Security</small></div>
            </div>
          </Panel>
        </Movable>

        {chatgptImageUrl && (
          <div style={{
            position: "fixed", right: 24, bottom: 24, zIndex: 9999,
            width: 340, padding: 14, borderRadius: 14,
            background: "rgba(5,10,18,0.96)",
            border: "1px solid rgba(80,180,255,0.55)",
            boxShadow: "0 18px 55px rgba(0,0,0,0.45)",
          }}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
              <b>CHATGPT IMAGE RESULT</b>
              <button onClick={() => setChatgptImageUrl("")}>Ã—</button>
            </div>
            <img src={chatgptImageUrl} alt="ChatGPT result" style={{width:"100%",borderRadius:10,display:"block"}} />
          </div>
        )}

        {sourceFixReport && (
          <div style={{
            position: "fixed", left: 24, top: 24, zIndex: 9998,
            width: 430, maxHeight: "70vh", overflow: "auto", padding: 14, borderRadius: 14,
            background: "rgba(5,10,18,0.97)",
            border: "1px solid rgba(120,220,255,0.48)",
            boxShadow: "0 18px 55px rgba(0,0,0,0.45)",
          }}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
              <b>SOURCE CODE // CHATGPT REPORT</b>
              <button onClick={() => setSourceFixReport(null)}>Ã—</button>
            </div>
            <div style={{fontSize:12,opacity:.82,marginBottom:8}}>
              {String(sourceFixReport.status || "report").toUpperCase()}
            </div>
            <pre style={{whiteSpace:"pre-wrap",fontSize:11,lineHeight:1.45,margin:0}}>
              {JSON.stringify(sourceFixReport, null, 2)}
            </pre>
          </div>
        )}


        <Movable id="command" editMode={editMode} positions={positions} setPositions={setPositions} className="right-movable command-movable">
          <Panel title="JARVIS CHAT // COMMAND" className="console-panel">
            <div className="console-line"><b className="user-tag">You:</b><span>{command || "Waiting for command..."}{commandTime && <small className="chat-time">{commandTime}</small>}</span></div>
            <div className="console-line"><b className="jarvis-tag">Jarvis:</b><span>{mode === "THINKING" ? "Processing..." : mode === "EXECUTING" ? "Executingâ€¦" : result || message}{responseTime && <small className="chat-time">{responseTime}</small>}</span></div>
            <div className="console-line muted"><b>State:</b><span>{modeText}</span></div>
            <div style={{
              display: "flex",
              justifyContent: "flex-end",
              margin: "6px 10px 4px"
            }}>
              <button
                type="button"
                onClick={() => setPromptOpen(v => !v)}
                style={{
                  border: "1px solid rgba(55,164,204,.35)",
                  background: "rgba(10,35,48,.7)",
                  color: "#63d8ff",
                  borderRadius: "6px",
                  padding: "5px 10px",
                  fontSize: "9px",
                  letterSpacing: "1.5px",
                  cursor: "pointer"
                }}
              >
                PROMPT
              </button>
            </div>

            {promptOpen && (
              <div style={{
                margin: "6px 10px 8px",
                padding: "9px",
                border: "1px solid rgba(55,164,204,.3)",
                borderRadius: "8px",
                background: "rgba(2,15,23,.92)"
              }}>
                <div style={{
                  color: "#63d8ff",
                  fontSize: "9px",
                  letterSpacing: "1.8px",
                  marginBottom: "7px"
                }}>
                  WEBSITE / MASTER PROMPT
                </div>

                <textarea
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  placeholder="Paste your complete website prompt here..."
                  style={{
                    width: "100%",
                    minHeight: "130px",
                    resize: "vertical",
                    boxSizing: "border-box",
                    border: "1px solid rgba(55,164,204,.25)",
                    borderRadius: "6px",
                    background: "#020b11",
                    color: "#bdefff",
                    padding: "9px",
                    outline: "none",
                    fontSize: "10px",
                    lineHeight: "1.5",
                    fontFamily: "inherit"
                  }}
                />

                <div style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "6px",
                  marginTop: "7px"
                }}>
                  <button type="button" onClick={() => setPromptText("")}>CLEAR</button>
                  <button type="button" onClick={() => setPromptOpen(false)}>CLOSE</button>
                  <button type="button" onClick={sendWebsitePrompt}>BUILD / SEND PROMPT</button>
                </div>
              </div>
            )}

            <div className="console-input">
              <input
                ref={commandInputRef}
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && command.trim()) handleCommand(command);
                }}
                placeholder="Type a command or ask JARVIS..."
                aria-label="JARVIS command input"
                autoComplete="off"
              />
              <div className="console-buttons">
                <button type="button" onClick={() => handleCommand(command)} title="Send command"><Icon type="wave" size={17} /></button>
                <button type="button" className="console-stop" onClick={stopJarvis} title="Stop current command"><span>ÃƒÂ¢Ã¢â‚¬â€œÃ‚Â </span></button>
              </div>
            </div>
          </Panel>
        </Movable>
      </aside>

      <input
        ref={galleryInputRef}
        className="jarvis-hidden-file-input"
        type="file"
        accept="image/*"
        multiple
        onChange={onGalleryFiles}
      />

      <GalleryOverlay
        open={galleryOpen}
        images={galleryImages}
        onClose={() => setGalleryOpen(false)}
        onAdd={openGallery}
      />

      <Movable id="footer-actions" editMode={editMode} positions={positions} setPositions={setPositions} className="footer-actions-movable">
        <div className="footer-actions">
          {[
            ["browser", "Open Chrome", "Open Chrome"],
            ["youtube", "YouTube", "Open YouTube"],
            ["code", "VS Code", "Open VS Code"],
            ["music", "Play Music", "Play Music"],
            ["monitor", "System Info", "System Info"],
            ["grid", "More", "Help"],
          ].map(([icon, label, cmd]) => (
            <button key={label} onClick={() => sendToJarvis(cmd)}>
              <Icon type={icon} size={16} />
              {label}
            </button>
          ))}
        </div>
      </Movable>

      <Movable id="footer" editMode={editMode} positions={positions} setPositions={setPositions} className="footer-movable">
        <footer className="footer">
          <span>ESC // EMERGENCY STOP</span>
          <b>JARVIS ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â BUILD. LEARN. EVOLVE.</b>
          <span>LOCAL // SECURE // READY</span>
        </footer>
      </Movable>
    </div>
  );
}












