import React, { useEffect, useMemo, useRef, useState } from "react";
import "./floaterPerception.css";

const PRESETS = [
  { id: "specks", label: "Specks", radius: [2, 5], alpha: [0.12, 0.30], blur: [0, 1] },
  { id: "strings", label: "Strings", radius: [2, 4], alpha: [0.10, 0.22], blur: [0, 1], stringy: true },
  { id: "cloud", label: "Cloud", radius: [10, 28], alpha: [0.05, 0.12], blur: [6, 14] },
  { id: "ring", label: "Ring", radius: [18, 40], alpha: [0.06, 0.14], blur: [2, 8], ring: true },
];

function rand(a, b) {
  return a + Math.random() * (b - a);
}
function clamp(v, a, b) {
  return Math.max(a, Math.min(b, v));
}

function makeFloaterFromPreset(preset, w, h) {
  const x = rand(w * 0.15, w * 0.85);
  const y = rand(h * 0.15, h * 0.85);

  const r = rand(preset.radius[0], preset.radius[1]);
  const alpha = rand(preset.alpha[0], preset.alpha[1]);
  const blur = rand(preset.blur[0], preset.blur[1]);

  return {
    id: `${preset.id}_${Math.random().toString(16).slice(2)}`,
    type: preset.id,
    x,
    y,
    baseR: r,
    baseAlpha: alpha,
    baseBlur: blur,
    vx: rand(-0.18, 0.18),
    vy: rand(-0.18, 0.18),
    ring: !!preset.ring,
    stringy: !!preset.stringy,
    theta: rand(0, Math.PI * 2),
    len: rand(r * 3, r * 9),

    // “depth layer” inside the eye (0..1). Used to vary response subtly.
    // Not physical units—just adds realism.
    z: Math.random(),
  };
}

function drawFloater(ctx, f, appearance) {
  const { r, alpha, blur } = appearance;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.filter = `blur(${blur}px)`;

  const stroke = `rgba(255,255,255,${clamp(alpha + 0.12, 0.08, 0.55)})`;
  const fill = `rgba(255,255,255,${clamp(alpha, 0.03, 0.35)})`;

  if (f.stringy) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = Math.max(1, r * 0.35);

    const x2 = f.x + Math.cos(f.theta) * (f.len * (r / f.baseR));
    const y2 = f.y + Math.sin(f.theta) * (f.len * (r / f.baseR));

    ctx.beginPath();
    ctx.moveTo(f.x, f.y);
    const cx = (f.x + x2) / 2 + Math.cos(f.theta + 1.2) * (f.len * 0.18);
    const cy = (f.y + y2) / 2 + Math.sin(f.theta + 1.2) * (f.len * 0.18);
    ctx.quadraticCurveTo(cx, cy, x2, y2);
    ctx.stroke();
  } else if (f.ring) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = Math.max(2, r * 0.14);
    ctx.beginPath();
    ctx.arc(f.x, f.y, r, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = fill;
    ctx.beginPath();
    ctx.arc(f.x, f.y, r * 0.55, 0, Math.PI * 2);
    ctx.fill();
  } else {
    ctx.fillStyle = fill;
    ctx.beginPath();
    ctx.arc(f.x, f.y, r, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
}

/**
 * Perception model:
 * - focusDistance: 0..1  (0 = near, 1 = far)
 * - gaze: {x,y} in canvas px
 * - stronger effect near gaze; weaker off-axis
 *
 * User spec: closer -> smaller, farther -> larger
 */
function computeAppearance(f, focusDistance, gaze, canvas) {
  const w = canvas.width;
  const h = canvas.height;

  // distance from gaze point (0..1)
  const dx = (f.x - gaze.x) / w;
  const dy = (f.y - gaze.y) / h;
  const d = Math.sqrt(dx * dx + dy * dy);

  // influence strongest at gaze, falls off smoothly
  const influence = Math.exp(-Math.pow(d / 0.22, 2)); // tweak for feel

  // core scaling per your request:
  // near(0) => 0.65x .. far(1) => 1.55x (stronger near gaze)
  const baseScale = 0.65 + focusDistance * 0.90; // 0.65..1.55
  const scale = 1 + (baseScale - 1) * (0.35 + 0.65 * influence);

  // subtle depth layer response so not all floaters behave identically
  const zBias = 0.90 + f.z * 0.20; // 0.90..1.10

  const r = f.baseR * scale * zBias;

  // optical presence: when far focus, floaters slightly more “present”
  // (alpha up a bit, blur up a bit)
  const alphaBoost = (focusDistance - 0.5) * 0.10; // -0.05..+0.05
  const alpha = clamp(f.baseAlpha + alphaBoost * (0.25 + 0.75 * influence), 0.02, 0.6);

  const blurBoost = focusDistance * 2.2; // far => more haze
  const blur = clamp(f.baseBlur + blurBoost * (0.15 + 0.85 * influence), 0, 18);

  return { r, alpha, blur };
}

function useGyroOrMouse() {
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    let usingGyro = false;

    function onMouseMove(e) {
      if (usingGyro) return;
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = (e.clientY / window.innerHeight) * 2 - 1;
      setOffset({ x: nx, y: ny });
    }

    function onDeviceOrientation(e) {
      usingGyro = true;
      const gamma = e.gamma ?? 0;
      const beta = e.beta ?? 0;
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

export default function FloaterPerception() {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  const gyro = useGyroOrMouse();

  const [viewMode, setViewMode] = useState("combined"); // left | right | combined
  const [tool, setTool] = useState("brush"); // preset | brush | erase
  const [activePresetId, setActivePresetId] = useState("specks");

  // 0..1: 0=near, 1=far
  const [focusDistance, setFocusDistance] = useState(0.65);

  // gaze point (canvas px)
  const gazeRef = useRef({ x: 0, y: 0 });

  const [speed, setSpeed] = useState(1.0);

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
    return [leftFloaters, setLeftFloaters]; // combined draws into left by default (you can change later)
  }

  function addPresetFloater() {
    const c = canvasRef.current;
    if (!c) return;
    const [items, setItems] = getActiveSetters();
    setItems([...items, makeFloaterFromPreset(activePreset, c.width, c.height)]);
  }

  function clearActive() {
    if (viewMode === "left") return setLeftFloaters([]);
    if (viewMode === "right") return setRightFloaters([]);
    setLeftFloaters([]);
    setRightFloaters([]);
  }

  function eraseAt(x, y) {
    const radius = 30;
    function filterOut(list) {
      return list.filter((f) => {
        const dx = f.x - x;
        const dy = f.y - y;
        return Math.sqrt(dx * dx + dy * dy) > Math.max(radius, f.baseR + 10);
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

    const [items, setItems] = getActiveSetters();

    const dots = Array.from({ length: activePreset.stringy ? 1 : 2 }, () => {
      const f = makeFloaterFromPreset(activePreset, c.width, c.height);
      f.x = x + rand(-6, 6);
      f.y = y + rand(-6, 6);
      f.vx *= 0.35;
      f.vy *= 0.35;
      return f;
    });

    setItems([...items, ...dots]);
  }

  function pointerToCanvasXY(e) {
    const c = canvasRef.current;
    if (!c) return null;
    const rect = c.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (c.width / rect.width);
    const y = (e.clientY - rect.top) * (c.height / rect.height);
    return { x, y };
  }

  function handlePointerDown(e) {
    const p = pointerToCanvasXY(e);
    if (!p) return;

    // update gaze
    gazeRef.current = p;

    isDrawingRef.current = true;

    if (tool === "preset") addPresetFloater();
    if (tool === "brush") brushAt(p.x, p.y);
    if (tool === "erase") eraseAt(p.x, p.y);
  }

  function handlePointerMove(e) {
    const p = pointerToCanvasXY(e);
    if (!p) return;

    // always track gaze (even when not drawing)
    gazeRef.current = p;

    if (!isDrawingRef.current) return;

    if (tool === "brush") brushAt(p.x, p.y);
    if (tool === "erase") eraseAt(p.x, p.y);
  }

  function handlePointerUp() {
    isDrawingRef.current = false;
  }

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

      // initialize gaze center on first resize
      if (gazeRef.current.x === 0 && gazeRef.current.y === 0) {
        gazeRef.current = { x: c.width / 2, y: c.height / 2 };
      }
    }

    resize();
    window.addEventListener("resize", resize);

    const ctx = c.getContext("2d");

    function tick() {
      if (!ctx) return;

      ctx.clearRect(0, 0, c.width, c.height);

      // “white wall” background (subtle)
      ctx.save();
      ctx.globalAlpha = 0.06;
      ctx.fillStyle = "rgba(255,255,255,1)";
      for (let i = 0; i < 60; i++) {
        const x = (i * c.width) / 60;
        ctx.fillRect(x, 0, 1, c.height);
      }
      ctx.restore();

      const toDraw =
        viewMode === "left"
          ? leftFloaters
          : viewMode === "right"
          ? rightFloaters
          : [
              ...leftFloaters,
              ...rightFloaters.map((f) => ({ ...f, baseAlpha: f.baseAlpha * 0.9 })),
            ];

      const gx = gyro.x * 1.2 * speed;
      const gy = gyro.y * 1.2 * speed;

      const gaze = gazeRef.current;

      for (const f of toDraw) {
        // drift + gyro parallax
        f.x += (f.vx + gx * 0.08) * dpr;
        f.y += (f.vy + gy * 0.08) * dpr;

        // wrap
        if (f.x < -80) f.x = c.width + 80;
        if (f.x > c.width + 80) f.x = -80;
        if (f.y < -80) f.y = c.height + 80;
        if (f.y > c.height + 80) f.y = -80;

        // perception
        const appearance = computeAppearance(f, focusDistance, gaze, c);
        drawFloater(ctx, f, appearance);
      }

      // Combined binocular mask + vignette
      if (viewMode === "combined") {
        ctx.save();
        ctx.globalCompositeOperation = "destination-in";
        const w = c.width;
        const h = c.height;
        const cx = w / 2;
        const cy = h / 2;

        ctx.beginPath();
        ctx.ellipse(cx - w * 0.14, cy, w * 0.34, h * 0.42, 0, 0, Math.PI * 2);
        ctx.ellipse(cx + w * 0.14, cy, w * 0.34, h * 0.42, 0, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,1)";
        ctx.fill();
        ctx.restore();

        ctx.save();
        ctx.globalAlpha = 0.72;
        const g = ctx.createRadialGradient(cx, cy, Math.min(w, h) * 0.2, cx, cy, Math.max(w, h) * 0.65);
        g.addColorStop(0, "rgba(0,0,0,0)");
        g.addColorStop(1, "rgba(0,0,0,0.86)");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        ctx.restore();
      }

      // Optional gaze indicator (very subtle)
      ctx.save();
      ctx.globalAlpha = 0.09;
      ctx.strokeStyle = "rgba(255,255,255,1)";
      ctx.beginPath();
      ctx.arc(gaze.x, gaze.y, 18, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();

      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("resize", resize);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [viewMode, gyro.x, gyro.y, speed, focusDistance, leftFloaters, rightFloaters]);

  return (
    <div className="floaterPerceptionPage">
      <div className="floaterPerceptionGrid">
        <aside className="floaterPerceptionLeft card">
          <div className="floaterPerceptionHeader">
            <div>
              <div className="floaterPerceptionTitle">Perception Emulator</div>
              <div className="floaterPerceptionSub">
                Move your “gaze” over the canvas. Adjust focus distance to emulate size shift.
              </div>
            </div>
          </div>

          <div className="floaterPerceptionSection">
            <div className="floaterPerceptionSectionLabel">View</div>
            <div className="floaterPerceptionRow">
              <button
                className={`virtuousBtn ${viewMode === "left" ? "floaterPerceptionBtnActive" : ""}`}
                onClick={() => setViewMode("left")}
              >
                Left Eye
              </button>
              <button
                className={`virtuousBtn ${viewMode === "right" ? "floaterPerceptionBtnActive" : ""}`}
                onClick={() => setViewMode("right")}
              >
                Right Eye
              </button>
              <button
                className={`virtuousBtn ${viewMode === "combined" ? "floaterPerceptionBtnActive" : ""}`}
                onClick={() => setViewMode("combined")}
              >
                Combined
              </button>
            </div>
          </div>

          <div className="floaterPerceptionSection">
            <div className="floaterPerceptionSectionLabel">Tool</div>
            <div className="floaterPerceptionRow">
              <button
                className={`virtuousBtn ${tool === "preset" ? "floaterPerceptionBtnActive" : ""}`}
                onClick={() => setTool("preset")}
              >
                Preset Click
              </button>
              <button
                className={`virtuousBtn ${tool === "brush" ? "floaterPerceptionBtnActive" : ""}`}
                onClick={() => setTool("brush")}
              >
                Brush
              </button>
              <button
                className={`virtuousBtn ${tool === "erase" ? "floaterPerceptionBtnActive" : ""}`}
                onClick={() => setTool("erase")}
              >
                Erase
              </button>
            </div>
          </div>

          <div className="floaterPerceptionSection">
            <div className="floaterPerceptionSectionLabel">Floater Types</div>
            <div className="floaterPerceptionRowWrap">
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  className={`virtuousBtn ${activePresetId === p.id ? "floaterPerceptionBtnActive" : ""}`}
                  onClick={() => setActivePresetId(p.id)}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <div className="floaterPerceptionRow">
              <button className="virtuousBtn virtuousBtnPrimary" onClick={addPresetFloater}>
                Add Floater
              </button>
              <button className="virtuousBtn" onClick={clearActive}>
                Clear
              </button>
            </div>
          </div>

          <div className="floaterPerceptionSection">
            <div className="floaterPerceptionSectionLabel">Perception</div>

            <div className="floaterPerceptionSliderRow">
              <div className="floaterPerceptionSliderLabel">Focus</div>
              <input
                className="floaterPerceptionSlider"
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={focusDistance}
                onChange={(e) => setFocusDistance(parseFloat(e.target.value))}
              />
              <div className="floaterPerceptionSliderValue">
                {focusDistance < 0.33 ? "NEAR" : focusDistance > 0.67 ? "FAR" : "MID"}
              </div>
            </div>

            <div className="floaterPerceptionHint">
              Per your spec: <b>Near focus → smaller</b>, <b>Far focus → larger</b>, strongest near your gaze.
            </div>
          </div>

          <div className="floaterPerceptionSection">
            <div className="floaterPerceptionSectionLabel">Motion</div>
            <div className="floaterPerceptionSliderRow">
              <div className="floaterPerceptionSliderLabel">Speed</div>
              <input
                className="floaterPerceptionSlider"
                type="range"
                min="0"
                max="3"
                step="0.05"
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
              />
              <div className="floaterPerceptionSliderValue">{speed.toFixed(2)}×</div>
            </div>

            <div className="floaterPerceptionHint">
              Uses device orientation when available; otherwise mouse movement.
            </div>
          </div>
        </aside>

        <main className="floaterPerceptionRight card card--raised">
          <div className="floaterPerceptionCanvasWrap">
            <canvas
              ref={canvasRef}
              className="floaterPerceptionCanvas"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerLeave={handlePointerUp}
            />
          </div>

          <div className="floaterPerceptionFooter">
            <div>
              <div className="floaterPerceptionFooterLabel">How to test</div>
              <div className="floaterPerceptionFooterText">
                Move your cursor to “look” around. Slide Focus toward FAR and watch floaters near your gaze grow.
              </div>
            </div>

            <div className="floaterPerceptionFooterRight">
              <span className="floaterPerceptionPill">{viewMode.toUpperCase()}</span>
              <span className="floaterPerceptionPill">{tool.toUpperCase()}</span>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}