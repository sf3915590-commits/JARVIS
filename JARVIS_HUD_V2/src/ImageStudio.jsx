import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import "./ImageStudio.css";

/*
  JARVIS IMAGE STUDIO
  -------------------
  Standalone module. It does NOT modify Core.jsx.

  Visual states:
    idle       -> normal JARVIS core
    generating -> rotating black/blue particle field inside core
    result     -> generated image replaces the inner core
    saved      -> result remains visible
    dismissed  -> returns control to the parent

  Parent integration can be added later with:
    <ImageStudio
      active={imageGenerationActive}
      prompt={imagePrompt}
      onClose={() => ...}
      onSaved={(url) => ...}
    />
*/

const PUTER_SCRIPT = "https://js.puter.com/v2/";
function loadPuter() {
  return new Promise((resolve, reject) => {
    if (window.puter?.ai?.txt2img) {
      resolve(window.puter);
      return;
    }

    const old = document.querySelector('script[data-jarvis-puter="true"]');
    if (old) old.remove();

    const script = document.createElement("script");
    script.src = PUTER_SCRIPT;
    script.async = true;
    script.dataset.jarvisPuter = "true";

    const timer = setTimeout(() => {
      script.remove();
      reject(new Error("Puter AI connection timeout. Please reconnect and try again."));
    }, 15000);

    script.onload = () => {
      clearTimeout(timer);
      if (window.puter?.ai?.txt2img) {
        resolve(window.puter);
      } else {
        script.remove();
        reject(new Error("Puter AI API connected nahi hua."));
      }
    };

    script.onerror = () => {
      clearTimeout(timer);
      script.remove();
      reject(new Error("Puter AI connection failed. Internet/session check karo."));
    };

    document.head.appendChild(script);
  });
}
function makeParticles(count = 54) {
  return Array.from({ length: count }, (_, i) => {
    const angle = (i / count) * Math.PI * 2;
    const radius = 28 + Math.random() * 54;

    return {
      id: i,
      x: 50 + Math.cos(angle) * radius,
      y: 50 + Math.sin(angle) * radius,
      delay: Math.random() * 1.4,
      duration: 1.4 + Math.random() * 1.8,
      size: 2 + Math.random() * 4,
    };
  });
}

const ImageStudio = forwardRef(function ImageStudio({
  active = false,
  embedded = false,
  prompt = "",
  onClose,
  onSaved,
  onPhaseChange,
  onImageReady,
}, ref) {
  const [localPrompt, setLocalPrompt] = useState(prompt);
  const [phase, setPhase] = useState("idle");
  const [imageUrl, setImageUrl] = useState("");
  const [error, setError] = useState("");
  const [particles] = useState(() => makeParticles());
  const [saved, setSaved] = useState(false);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (prompt) setLocalPrompt(prompt);
  }, [prompt]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startProgress = () => {
    setProgress(4);

    if (timerRef.current) clearInterval(timerRef.current);

    timerRef.current = setInterval(() => {
      setProgress((value) => {
        if (value >= 93) return value;
        const step = value < 35 ? 5 : value < 70 ? 3 : 1;
        return Math.min(93, value + step);
      });
    }, 650);
  };

  const stopProgress = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setProgress(100);
  };

  const generate = async (requestedPrompt) => {
    const text = String(requestedPrompt ?? localPrompt).trim();

    if (!text) {
      setError("Boss, image kis cheez ki generate karni hai?");
      return;
    }

    setError("");
    setSaved(false);
    setImageUrl("");
    setPhase("generating");
    onPhaseChange?.("generating");
    startProgress();

    try {
      const started = Date.now();

      const src = await new Promise((resolve, reject) => {
        const check = async () => {
          try {
            const response = await fetch(
              `/jarvis-generated.png?ts=${Date.now()}`,
              { cache: "no-store" }
            );

            if (response.ok) {
              resolve(`/jarvis-generated.png?ts=${Date.now()}`);
              return;
            }
          } catch {}

          if (Date.now() - started >= 180000) {
            reject(new Error("Pollinations image generation timeout."));
            return;
          }

          setTimeout(check, 1000);
        };

        check();
      });

      stopProgress();
      setImageUrl(src);
      onImageReady?.(src);
      setPhase("result");
      onPhaseChange?.("result");
    } catch (err) {
      stopProgress();
      setPhase("idle");
      onPhaseChange?.("idle");
      setError(err?.message || "Image generation failed.");
    }
  };
  useImperativeHandle(ref, () => ({
    generate: (text) => generate(text),
    save: () => saveImage(),
    remove: () => removeImage(),
  }), [imageUrl]);

  if (embedded) {
    return (
      <div className={`jarvis-image-embedded ${phase}`}>
        {phase === "generating" && (
          <div className="jarvis-generation-field">
            <div className="jarvis-generation-ring ring-a" />
            <div className="jarvis-generation-ring ring-b" />
            <div className="jarvis-generation-ring ring-c" />
            {particles.map((particle) => (
              <span
                key={particle.id}
                className="jarvis-particle"
                style={{
                  left: `${particle.x}%`,
                  top: `${particle.y}%`,
                  width: `${particle.size}px`,
                  height: `${particle.size}px`,
                  animationDelay: `${particle.delay}s`,
                  animationDuration: `${particle.duration}s`,
                }}
              />
            ))}
            <div className="jarvis-generation-scan" />
            <div className="jarvis-generation-text">
              <strong>JARVIS</strong>
              <span>GENERATING IMAGE</span>
              <small>{Math.round(progress)}%</small>
            </div>
          </div>
        )}

        {error && (
          <div className="jarvis-image-error" style={{position:"absolute",zIndex:20,left:"6%",right:"6%",bottom:"8%",padding:"10px",borderRadius:"10px",background:"rgba(0,0,0,.9)",color:"#ff9b9b",fontSize:"12px",textAlign:"center"}}>{error}</div>
        )}

        {phase === "result" && imageUrl && (
          <div className="jarvis-image-result">
            <img src={imageUrl} alt="JARVIS generated result" />
            <div className="jarvis-result-shine" />
          </div>
        )}
      </div>
    );
  }

  if (!active) return null;

  return (
    <div className={`jarvis-image-layer ${phase}`}>
      <div className="jarvis-image-core-stage">
        <div className="jarvis-image-core-glow" />

        <div className="jarvis-image-core">
          {phase === "generating" && (
            <div className="jarvis-generation-field">
              <div className="jarvis-generation-ring ring-a" />
              <div className="jarvis-generation-ring ring-b" />
              <div className="jarvis-generation-ring ring-c" />

              {particles.map((particle) => (
                <span
                  key={particle.id}
                  className="jarvis-particle"
                  style={{
                    left: `${particle.x}%`,
                    top: `${particle.y}%`,
                    width: `${particle.size}px`,
                    height: `${particle.size}px`,
                    animationDelay: `${particle.delay}s`,
                    animationDuration: `${particle.duration}s`,
                  }}
                />
              ))}

              <div className="jarvis-generation-scan" />

              <div className="jarvis-generation-text">
                <strong>JARVIS</strong>
                <span>GENERATING IMAGE</span>
                <small>{Math.round(progress)}%</small>
              </div>
            </div>
          )}

          {error && (
          <div className="jarvis-image-error" style={{position:"absolute",zIndex:20,left:"6%",right:"6%",bottom:"8%",padding:"10px",borderRadius:"10px",background:"rgba(0,0,0,.9)",color:"#ff9b9b",fontSize:"12px",textAlign:"center"}}>{error}</div>
        )}

        {phase === "result" && imageUrl && (
            <div className="jarvis-image-result">
              <img src={imageUrl} alt="JARVIS generated result" />
              <div className="jarvis-result-shine" />
            </div>
          )}

          {phase === "idle" && (
            <div className="jarvis-image-idle">
              <div className="jarvis-idle-mark">J</div>
              <span>IMAGE ENGINE READY</span>
            </div>
          )}
        </div>

        <div className="jarvis-image-status">
          {phase === "generating" && (
            <>
              <b>EXECUTING</b>
              <span>JARVIS IMAGE ENGINE</span>
            </>
          )}

          {phase === "result" && (
            <>
              <b>IMAGE GENERATED</b>
              <span>RESULT READY</span>
            </>
          )}

          {phase === "idle" && (
            <>
              <b>JARVIS</b>
              <span>IMAGE ENGINE</span>
            </>
          )}
        </div>
      </div>

      <div className="jarvis-image-command">
        <textarea
          value={localPrompt}
          onChange={(event) => setLocalPrompt(event.target.value)}
          placeholder="Describe the image you want JARVIS to create..."
          disabled={phase === "generating"}
          onKeyDown={(event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
              generate();
            }
          }}
        />

        <div className="jarvis-image-command-row">
          <span>Ctrl + Enter to generate</span>

          <button
            type="button"
            onClick={generate}
            disabled={phase === "generating"}
          >
            {phase === "generating" ? "GENERATING..." : "GENERATE"}
          </button>
        </div>

        {error && <div className="jarvis-image-error">{error}</div>}
      </div>

      {phase === "result" && imageUrl && (
        <div className="jarvis-image-actions">
          <button type="button" className="danger" onClick={removeImage}>
            REMOVE
          </button>

          <button type="button" className="primary" onClick={saveImage}>
            {saved ? "SAVED" : "SAVE"}
          </button>
        </div>
      )}

      {phase !== "generating" && (
        <button type="button" className="jarvis-image-close" onClick={close}>
          Ã—
        </button>
      )}
    </div>
  );
});

export default ImageStudio;







