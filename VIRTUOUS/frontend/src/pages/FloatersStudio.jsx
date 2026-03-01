import React, { useEffect, useMemo, useRef, useState } from "react";
import "./floatersStudio.css";

const PRESETS = [
  { id: "specks", label: "Specks", radius: [2, 5], alpha: [0.15, 0.35], blur: [0, 1] },
  { id: "strings", label: "Strings", radius: [2, 4], alpha: [0.12, 0.28], blur: [0, 1], stringy: true },
  { id: "cloud", label: "Cloud", radius: [10, 32], alpha: [0.05, 0.14], blur: [6, 14] },
  { id: "ring", label: "Ring", radius: [18, 40], alpha: [0.06, 0.14], blur: [2, 8], ring: true },
];

function rand(a, b) {
  return a + Math.random() * (b - a);
}

function clamp(v, a, b) {
  return Math.max(a, Math.min(b, v));
}

function makeFloaterFromPreset(preset, w, h) {
  const x = rand(w * 0.2, w * 0.8);
  const y = rand(h * 0.2, h * 0.8);

  const r = rand(preset.radius[0], preset.radius[1]);
  const alpha = rand(preset.alpha[0], preset.alpha[1]);
  const blur = rand(preset.blur[0], preset.blur[1]);

  // velocity is subtle; we’ll “steer” it with gyro offset
  const vx = rand(-0.2, 0.2);
  const vy = rand(-0.2, 0.2);

  return {
    id: `${preset.id}_${Math.random().toString(16).slice(2)}`,
    type: preset.id,
    x,
    y,
    r,
    alpha,
    blur,
    vx,
    vy,
    ring: !!preset.ring,
    stringy: !!preset.stringy,
    // for strings
    theta: rand(0, Math.PI * 2),
    len: rand(r * 3, r * 9),
  };
}

function drawFloater(ctx, f) {
  ctx.save();

  ctx.globalAlpha = f.alpha;

  // blur (optical softness)
  ctx.filter = `blur(${f.blur}px)`;

  // a subtle neutral “floater” tone using rgba white
  // (uses alpha for intensity; keeps consistent with dark UI)
  const stroke = `rgba(255,255,255,${clamp(f.alpha + 0.1, 0.08, 0.5)})`;
  const fill = `rgba(255,255,255,${clamp(f.alpha, 0.04, 0.35)})`;

  if (f.stringy) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = Math.max(1, f.r * 0.35);

    const x2 = f.x + Math.cos(f.theta) * f.len;
    const y2 = f.y + Math.sin(f.theta) * f.len;

    ctx.beginPath();
    ctx.moveTo(f.x, f.y);
    // slight curve
    const cx = (f.x + x2) / 2 + Math.cos(f.theta + 1.2) * (f.len * 0.18);
    const cy = (f.y + y2) / 2 + Math.sin(f.theta + 1.2) * (f.len * 0.18);
    ctx.quadraticCurveTo(cx, cy, x2, y2);
    ctx.stroke();
  } else if (f.ring) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = Math.max(2, f.r * 0.14);
    ctx.beginPath();
    ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
    ctx.stroke();

    // faint inner haze
    ctx.fillStyle = fill;
    ctx.beginPath();
    ctx.arc(f.x, f.y, f.r * 0.55, 0, Math.PI * 2);
    ctx.fill();
  } else {
    // “speck / cloud” = circle-ish blob
    ctx.fillStyle = fill;
    ctx.beginPath();
    ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
}

function useGyroOrMouse() {
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    let enabled = false;

    function onMouseMove(e) {
      if (enabled) return;
      // map mouse position to an offset (-1..1)
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = (e.clientY / window.innerHeight) * 2 - 1;
      setOffset({ x: nx, y: ny });
    }

    function onDeviceOrientation(e) {
      enabled = true;
      // gamma: left-right, beta: front-back
      const gamma = e.gamma ?? 0; // -90..90
      const beta = e.beta ?? 0; // -180..180
      setOffset({
        x: clamp(gamma / 30, -1, 1),
        y: clamp(beta / 30, -1, 1),
      });
    }

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("deviceorientation", onDeviceOrientation);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("deviceorientation", onDeviceOrientation);
    };
  }, []);

  return offset;
}

export default function FloaterStudio() {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  const gyro = useGyroOrMouse();

  const [showOnboarding, setShowOnboarding] = useState(true);
  const [viewMode, setViewMode] = useState("combined"); // left | right | combined
  const [tool, setTool] = useState("preset"); // preset | brush | erase
  const [activePresetId, setActivePresetId] = useState(PRESETS[0].id);

  const [speed, setSpeed] = useState(1.0);

  // separate floaters per eye
  const [leftFloaters, setLeftFloaters] = useState([]);
  const [rightFloaters, setRightFloaters] = useState([]);

  const activePreset = useMemo(
    () => PRESETS.find((p) => p.id === activePresetId) || PRESETS[0],
    [activePresetId]
  );

  const isDrawingRef = useRef(false);

  function getActiveSetters() {
    if (viewMode === "left") return [leftFloaters, setLeftFloaters];
    if (viewMode === "right") return [rightFloaters, setRightFloaters];
    // combined = draw into both by default (you can change this later)
    return [leftFloaters, setLeftFloaters];
  }

  function addPresetFloater() {
    const c = canvasRef.current;
    if (!c) return;
    const [items, setItems] = getActiveSetters();
    const f = makeFloaterFromPreset(activePreset, c.width, c.height);
    setItems([...items, f]);
  }

  function clearActive() {
    if (viewMode === "left") return setLeftFloaters([]);
    if (viewMode === "right") return setRightFloaters([]);
    // combined clears both
    setLeftFloaters([]);
    setRightFloaters([]);
  }

  function eraseAt(x, y) {
    const radius = 28;
    function filterOut(list) {
      return list.filter((f) => {
        const dx = f.x - x;
        const dy = f.y - y;
        return Math.sqrt(dx * dx + dy * dy) > Math.max(radius, f.r + 8);
      });
    }

    if (viewMode === "left") setLeftFloaters((prev) => filterOut(prev));
    else if (viewMode === "right") setRightFloaters((prev) => filterOut(prev));
    else {
      setLeftFloaters((prev) => filterOut(prev));
      setRightFloaters((prev) => filterOut(prev));
    }
  }

  function brushAt(x, y) {
    const c = canvasRef.current;
    if (!c) return;

    // Brush “paints” specks by default (patient draws what they see)
    const preset = activePreset || PRESETS[0];
    const [items, setItems] = getActiveSetters();

    // place a few particles per stroke point
    const dots = Array.from({ length: preset.stringy ? 1 : 2 }, () => {
      const f = makeFloaterFromPreset(preset, c.width, c.height);
      f.x = x + rand(-6, 6);
      f.y = y + rand(-6, 6);
      f.vx *= 0.4;
      f.vy *= 0.4;
      return f;
    });

    setItems([...items, ...dots]);
  }

  function handlePointerDown(e) {
    const c = canvasRef.current;
    if (!c) return;
    const rect = c.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (c.width / rect.width);
    const y = (e.clientY - rect.top) * (c.height / rect.height);

    isDrawingRef.current = true;

    if (tool === "preset") {
      addPresetFloater();
    } else if (tool === "brush") {
      brushAt(x, y);
    } else if (tool === "erase") {
      eraseAt(x, y);
    }
  }

  function handlePointerMove(e) {
    if (!isDrawingRef.current) return;
    const c = canvasRef.current;
    if (!c) return;
    const rect = c.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (c.width / rect.width);
    const y = (e.clientY - rect.top) * (c.height / rect.height);

    if (tool === "brush") brushAt(x, y);
    if (tool === "erase") eraseAt(x, y);
  }

  function handlePointerUp() {
    isDrawingRef.current = false;
  }

  // draw loop
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;

    const dpr = window.devicePixelRatio || 1;

    function resize() {
      const parent = c.parentElement;
      if (!parent) return;

      const rect = parent.getBoundingClientRect();
      c.width = Math.floor(rect.width * dpr);
      c.height = Math.floor(rect.height * dpr);
    }

    resize();
    window.addEventListener("resize", resize);

    const ctx = c.getContext("2d");

    function tick() {
      if (!ctx) return;

      // Clear
      ctx.clearRect(0, 0, c.width, c.height);

      // faint “wall” background pattern (very subtle)
      ctx.save();
      ctx.globalAlpha = 0.08;
      ctx.fillStyle = "rgba(255,255,255,1)";
      for (let i = 0; i < 60; i++) {
        const x = (i * c.width) / 60;
        ctx.fillRect(x, 0, 1, c.height);
      }
      ctx.restore();

      // combine based on viewMode
      const toDraw =
        viewMode === "left"
          ? leftFloaters
          : viewMode === "right"
          ? rightFloaters
          : [...leftFloaters, ...rightFloaters.map((f) => ({ ...f, alpha: f.alpha * 0.9 }))];

      // “physics”: subtle drift + gyro parallax
      const gx = gyro.x * 1.2 * speed;
      const gy = gyro.y * 1.2 * speed;

      // Move + draw
      for (const f of toDraw) {
        f.x += (f.vx + gx * 0.08) * dpr;
        f.y += (f.vy + gy * 0.08) * dpr;

        // keep in bounds
        if (f.x < -50) f.x = c.width + 50;
        if (f.x > c.width + 50) f.x = -50;
        if (f.y < -50) f.y = c.height + 50;
        if (f.y > c.height + 50) f.y = -50;

        drawFloater(ctx, f);
      }

      // non-rectangular FOV mask in combined mode (optional effect)
      if (viewMode === "combined") {
        ctx.save();
        ctx.globalCompositeOperation = "destination-in";
        ctx.filter = "blur(0px)";
        ctx.globalAlpha = 1;

        const w = c.width;
        const h = c.height;

        const cx = w / 2;
        const cy = h / 2;

        // an organic “binocular” mask: two overlapping ovals
        ctx.beginPath();
        ctx.ellipse(cx - w * 0.14, cy, w * 0.34, h * 0.42, 0, 0, Math.PI * 2);
        ctx.ellipse(cx + w * 0.14, cy, w * 0.34, h * 0.42, 0, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,1)";
        ctx.fill();

        ctx.restore();

        // edge vignette
        ctx.save();
        ctx.globalAlpha = 0.7;
        const g = ctx.createRadialGradient(cx, cy, Math.min(w, h) * 0.2, cx, cy, Math.max(w, h) * 0.65);
        g.addColorStop(0, "rgba(0,0,0,0)");
        g.addColorStop(1, "rgba(0,0,0,0.85)");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        ctx.restore();
      }

      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("resize", resize);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, gyro.x, gyro.y, speed, leftFloaters, rightFloaters]);

  return (
    <div className="floaterStudioPage">
      <div className="floaterStudioGrid">
        {/* Left controls */}
        <aside className="floaterStudioLeft card">
          <div className="floaterStudioHeader">
            <div>
              <div className="floaterStudioTitle">Floater Studio</div>
              <div className="floaterStudioSub">
                Represent what you see — by preset or brush — per eye or combined.
              </div>
            </div>

            <button className="virtuousBtn" onClick={() => setShowOnboarding(true)}>
              Onboarding
            </button>
          </div>

          <div className="floaterStudioSection">
            <div className="floaterStudioSectionLabel">View</div>
            <div className="floaterStudioRow">
              <button
                className={`virtuousBtn ${viewMode === "left" ? "floaterStudioBtnActive" : ""}`}
                onClick={() => setViewMode("left")}
              >
                Left Eye
              </button>
              <button
                className={`virtuousBtn ${viewMode === "right" ? "floaterStudioBtnActive" : ""}`}
                onClick={() => setViewMode("right")}
              >
                Right Eye
              </button>
              <button
                className={`virtuousBtn ${viewMode === "combined" ? "floaterStudioBtnActive" : ""}`}
                onClick={() => setViewMode("combined")}
              >
                Combined
              </button>
            </div>
          </div>

          <div className="floaterStudioSection">
            <div className="floaterStudioSectionLabel">Tool</div>
            <div className="floaterStudioRow">
              <button
                className={`virtuousBtn ${tool === "preset" ? "floaterStudioBtnActive" : ""}`}
                onClick={() => setTool("preset")}
              >
                Preset Click
              </button>
              <button
                className={`virtuousBtn ${tool === "brush" ? "floaterStudioBtnActive" : ""}`}
                onClick={() => setTool("brush")}
              >
                Brush
              </button>
              <button
                className={`virtuousBtn ${tool === "erase" ? "floaterStudioBtnActive" : ""}`}
                onClick={() => setTool("erase")}
              >
                Erase
              </button>
            </div>
          </div>

          <div className="floaterStudioSection">
            <div className="floaterStudioSectionLabel">Floater Types</div>
            <div className="floaterStudioRowWrap">
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  className={`virtuousBtn ${activePresetId === p.id ? "floaterStudioBtnActive" : ""}`}
                  onClick={() => setActivePresetId(p.id)}
                >
                  {p.label}
                </button>
              ))}
              <button className="virtuousBtn" title="Placeholder for your feature request flow">
                Request Type
              </button>
            </div>

            <div className="floaterStudioRow">
              <button className="virtuousBtn virtuousBtnPrimary" onClick={addPresetFloater}>
                Add Floater
              </button>
              <button className="virtuousBtn" onClick={clearActive}>
                Clear
              </button>
            </div>
          </div>

          <div className="floaterStudioSection">
            <div className="floaterStudioSectionLabel">Motion</div>
            <div className="floaterStudioSliderRow">
              <div className="floaterStudioSliderLabel">Speed</div>
              <input
                className="floaterStudioSlider"
                type="range"
                min="0"
                max="3"
                step="0.05"
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
              />
              <div className="floaterStudioSliderValue">{speed.toFixed(2)}×</div>
            </div>
            <div className="floaterStudioHint">
              Motion uses device orientation when available; otherwise mouse movement.
            </div>
          </div>
        </aside>

        {/* Right canvas */}
        <main className="floaterStudioRight card card--raised">
          <div className="floaterStudioCanvasWrap">
            <canvas
              ref={canvasRef}
              className="floaterStudioCanvas"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerLeave={handlePointerUp}
            />
          </div>

          <div className="floaterStudioFooter">
            <div className="floaterStudioFooterLeft">
              <div className="floaterStudioFooterLabel">Instructions</div>
              <div className="floaterStudioFooterText">
                {tool === "preset" && "Click to add preset floaters. Use View to draw per eye."}
                {tool === "brush" && "Drag to paint floaters. Close one eye for eye-specific mode."}
                {tool === "erase" && "Drag to erase nearby floaters."}
              </div>
            </div>
            <div className="floaterStudioFooterRight">
              <span className="floaterStudioPill">{viewMode.toUpperCase()}</span>
              <span className="floaterStudioPill">{tool.toUpperCase()}</span>
            </div>
          </div>
        </main>
      </div>

      {/* Onboarding modal */}
      {showOnboarding && (
        <div className="floaterModalOverlay" role="dialog" aria-modal="true">
          <div className="floaterModal card modal--info">
            <div className="floaterModalTitle">Standardized Onboarding</div>
            <ol className="floaterModalList">
              <li>Stand ~20 ft from a plain white wall (or bright blank screen).</li>
              <li>Relax your gaze; notice floaters drifting.</li>
              <li>Select <b>Left Eye</b> and close your right eye. Draw what you see.</li>
              <li>Select <b>Right Eye</b> and close your left eye. Draw again.</li>
              <li>Switch to <b>Combined</b> to review binocular appearance.</li>
            </ol>
            <div className="floaterModalActions">
              <button className="virtuousBtn" onClick={() => setShowOnboarding(false)}>
                Close
              </button>
              <button
                className="virtuousBtn virtuousBtnPrimary"
                onClick={() => {
                  setShowOnboarding(false);
                  setViewMode("left");
                  setTool("brush");
                }}
              >
                Start Left Eye Brush
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}