import React, { useEffect, useRef, useState } from "react";
import "./chat-mode.css";

export default function ChatMode({ onCommand, connected, message, result, mode, onBack }) {
  const [input, setInput] = useState("");
  const [items, setItems] = useState([
    { role: "assistant", text: "Chat Mode online. Boss, mujhse kuch bhi pooch sakte ho." }
  ]);
  const [waiting, setWaiting] = useState(false);
  const endRef = useRef(null);
  const lastResponseRef = useRef("");
  const send = () => {
    const text = input.trim();
    if (!text || waiting) return;
    setItems(prev => [...prev, { role: "user", text }]);
    setInput("");
    setWaiting(true);
    lastResponseRef.current = "";
    onCommand?.(text);
  };
  useEffect(() => {
    const response = String(result || message || "").trim();
    if (!response || mode === "THINKING" || mode === "EXECUTING") return;
    if (response === lastResponseRef.current) return;
    if (response === "JARVIS CORE INITIALIZING..." || response === "I'M LISTENING, BOSS.") return;
    lastResponseRef.current = response;
    setItems(prev => {
      if (prev.length && prev[prev.length - 1].role === "assistant" && prev[prev.length - 1].text === response) return prev;
      return [...prev, { role: "assistant", text: response }];
    });
    setWaiting(false);
  }, [message, result, mode]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [items, waiting]);
  return (
    <main className="jarvis-chat-mode">
      <header className="jcm-top">
        <div><span className="jcm-eyebrow">JARVIS // NEURAL INTERFACE</span><h1>CHAT MODE</h1><small>{connected ? "● CORE CONNECTED" : "○ CONNECTING TO CORE"}</small></div>
        <button onClick={onBack} className="jcm-back">← OS MODE</button>
      </header>
      <section className="jcm-transcript">
        {items.map((item, i) => <article key={i} className={`jcm-message ${item.role}`}>
          <b>{item.role === "user" ? "YOU" : "JARVIS"}</b><p>{item.text}</p>
        </article>)}
        {waiting && <article className="jcm-message assistant"><b>JARVIS</b><p className="jcm-typing">Thinking<span>.</span><span>.</span><span>.</span></p></article>}
        <div ref={endRef} />
      </section>
      <footer className="jcm-compose">
        <textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Message JARVIS..." rows={1} />
        <button onClick={send} disabled={!input.trim() || waiting}>SEND ↗</button>
      </footer>
      <div className="jcm-hint">ENTER TO SEND · SHIFT + ENTER FOR NEW LINE</div>
    </main>
  );
}
