// src/components/HeatmapExam.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import "./heatmapexam.css";

/**
 * HeatmapExam
 * - Patient paints intensity where floaters appear
 * - Left eye, Right eye, Combined
 * - Soft brush that accumulates intensity
 * - Eraser subtracts intensity (implemented as "draw with destination-out")
 * - Undo/Redo per-eye
 *
 * Props:
 * - onComplete?: (payload) => void   // optional callback when patient finishes
 */
export default function HeatmapExam({ onComplete }) {
  const modes = useMemo(() => ["left", "right", "combined"], []);
  const [mode, setMode] = useState("left");

  const [brushSize, setBrushSize] = useState(44);
  const [strength, setStrength] = useState(0.22); // opacity per dab
  const [tool, setTool] = useState("brush"); // "brush" | "eraser"

  // Per-mode history (undo/redo)
  const [history, setHistory] = useState(() => ({
    left: { past: [], present: null, future: [] },
    right: { past: [], present: null, future: [] },
    combined: { past: [], present: null, future: [] },
  }));

  const [confidence, setConfidence] = useState(() => ({
    left: 3,
    right: 3,
    combined: 3,
  }));

  const canvasRef = useRef(null);
  const isDownRef = useRef(false);
  const lastPtRef = useRef(null);
  const dprRef = useRef(1);

  // ---- helpers ----
  function getCanvas() {
    return canvasRef.current;
  }
  function getCtx() {
    const c = getCanvas();
    return c ? c.getContext("2d") : null;
  }

  function snapshotToDataURL() {
    const c = getCanvas();
    if (!c) return null;
    return c.toDataURL("image/png");
  }

  function loadFromDataURL(dataUrl) {
    const c = getCanvas();
    const ctx = getCtx();
    if (!c || !ctx) return;

    ctx.clearRect(0, 0, c.width, c.height);

    // Always redraw base field (background, dot, vignette)
    drawBaseField(ctx, c);

    if (!dataUrl) return;

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, c.width, c.height);
    };
    img.src = dataUrl;
  }

  function pushHistory(newPresent) {
    setHistory((h) => {
      const cur = h[mode];
      const past = cur.present ? [...cur.past, cur.present] : [...cur.past];
      return {
        ...h,
        [mode]: { past, present: newPresent, future: [] },
      };
    });
  }

  function undo() {
    setHistory((h) => {
      const cur = h[mode];
      if (cur.past.length === 0) return h;
      const previous = cur.past[cur.past.length - 1];
      const newPast = cur.past.slice(0, -1);
      const future = cur.present ? [cur.present, ...cur.future] : [...cur.future];
      return {
        ...h,
        [mode]: { past: newPast, present: previous, future },
      };
    });
  }

  function redo() {
    setHistory((h) => {
      const cur = h[mode];
      if (cur.future.length === 0) return h;
      const next = cur.future[0];
      const newFuture = cur.future.slice(1);
      const past = cur.present ? [...cur.past, cur.present] : [...cur.past];
      return {
        ...h,
        [mode]: { past, present: next, future: newFuture },
      };
    });
  }

  function resetCurrent() {
    const ctx = getCtx();
    const c = getCanvas();
    if (!ctx || !c) return;

    ctx.clearRect(0, 0, c.width, c.height);
    drawBaseField(ctx, c);

    pushHistory(null); // record as cleared state
  }

  function nextMode() {
    const idx = modes.indexOf(mode);
    const next = modes[Math.min(idx + 1, modes.length - 1)];
    setMode(next);
  }

  function prevMode() {
    const idx = modes.indexOf(mode);
    const prev = modes[Math.max(idx - 1, 0)];
    setMode(prev);
  }

  function finalize() {
    const payload = {
      exam: "floater_heatmap",
      createdAt: new Date().toISOString(),
      images: {
        left: history.left.present,
        right: history.right.present,
        combined: history.combined.present,
      },
      confidence: { ...confidence },
      settings: { brushSize, strength },
    };
    onComplete?.(payload);
    // Also useful for quick dev visibility:
    // eslint-disable-next-line no-console
    console.log("HeatmapExam payload:", payload);
    alert("Saved heatmaps (see console payload).");
  }

  // ---- drawing ----
  function drawBaseField(ctx, c) {
    // Neutral field with subtle vignette + center fixation dot
    ctx.save();

    // Fill with transparent (so your floaters behind can show if desired),
    // but we still want a consistent interaction surface. Use a token-driven rgba:
    ctx.clearRect(0, 0, c.width, c.height);

    // Soft vignette
    const cx = c.width / 2;
    const cy = c.height / 2;
    const r = Math.min(c.width, c.height) * 0.52;

    const g = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r);
    g.addColorStop(0, "rgba(0,0,0,0.0)");
    g.addColorStop(1, "rgba(0,0,0,0.35)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, c.width, c.height);

    // Faint field boundary circle
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255,255,255,0.10)";
    ctx.lineWidth = Math.max(1, c.width * 0.002);
    ctx.stroke();

    // Fixation dot
    ctx.beginPath();
    ctx.arc(cx, cy, Math.max(3, c.width * 0.006), 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,255,255,0.70)";
    ctx.fill();

    ctx.restore();
  }

  function drawDab(ctx, x, y) {
    const c = getCanvas();
    if (!ctx || !c) return;

    // Heat color: keep it simple (white-ish) and rely on opacity to show intensity.
    // If you prefer blue/purple, you can change fillStyle here.
    const radius = brushSize * dprRef.current;

    ctx.save();

    if (tool === "eraser") {
      // Erase by punching out alpha
      ctx.globalCompositeOperation = "destination-out";
      ctx.globalAlpha = Math.min(1, strength * 1.4);
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = strength;
    }

    // Soft radial dab
    const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = grad;

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  function drawLine(ctx, a, b) {
    // Interpolate dabs for smooth strokes
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const step = Math.max(2, (brushSize * dprRef.current) / 3);
    const n = Math.max(1, Math.floor(dist / step));

    for (let i = 0; i <= n; i++) {
      const t = i / n;
      drawDab(ctx, a.x + dx * t, a.y + dy * t);
    }
  }

  function getPointFromEvent(e) {
    const c = getCanvas();
    if (!c) return null;
    const rect = c.getBoundingClientRect();
    const dpr = dprRef.current;

    const clientX = e.clientX ?? (e.touches?.[0]?.clientX ?? 0);
    const clientY = e.clientY ?? (e.touches?.[0]?.clientY ?? 0);

    return {
      x: (clientX - rect.left) * dpr,
      y: (clientY - rect.top) * dpr,
    };
  }

  function beginStroke(e) {
    const ctx = getCtx();
    if (!ctx) return;

    isDownRef.current = true;
    const pt = getPointFromEvent(e);
    lastPtRef.current = pt;
    if (pt) drawDab(ctx, pt.x, pt.y);
  }

  function moveStroke(e) {
    const ctx = getCtx();
    if (!ctx || !isDownRef.current) return;

    const pt = getPointFromEvent(e);
    const last = lastPtRef.current;
    if (!pt || !last) return;

    drawLine(ctx, last, pt);
    lastPtRef.current = pt;
  }

  function endStroke() {
    if (!isDownRef.current) return;
    isDownRef.current = false;
    lastPtRef.current = null;

    // Commit snapshot to history
    const url = snapshotToDataURL();
    pushHistory(url);
  }

  // ---- init canvas sizing + load history on mode change ----
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;

    const resize = () => {
      const rect = c.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      dprRef.current = dpr;

      c.width = Math.floor(rect.width * dpr);
      c.height = Math.floor(rect.height * dpr);

      const ctx = c.getContext("2d");
      if (!ctx) return;

      drawBaseField(ctx, c);

      // reload current mode image after resize
      const present = history[mode].present;
      if (present) loadFromDataURL(present);
    };

    resize();

    const ro = new ResizeObserver(resize);
    ro.observe(c);

    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    // Whenever mode changes, load its present snapshot (or blank base field)
    const present = history[mode].present;
    loadFromDataURL(present);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, history.left.present, history.right.present, history.combined.present]);

  const canUndo = history[mode].past.length > 0;
  const canRedo = history[mode].future.length > 0;

  return (
    <div className="heatmapPage">
      <div className="heatmapSplit">
        <aside className="heatmapLeft">
          <div className="heatmapLeftInner">
            <div className="heatmapHeader">
              <div className="heatmapTitle">Floater Heatmap</div>
              <div className="heatmapSubtitle">
                Paint where floaters interrupt your vision, and how strong they feel.
              </div>
            </div>

            <div className="heatmapStepCard card">
              <div className="heatmapStepLabel">Current step</div>
              <div className="heatmapModeRow">
                <ModePill active={mode === "left"} onClick={() => setMode("left")}>
                  Left Eye
                </ModePill>
                <ModePill active={mode === "right"} onClick={() => setMode("right")}>
                  Right Eye
                </ModePill>
                <ModePill active={mode === "combined"} onClick={() => setMode("combined")}>
                  Combined
                </ModePill>
              </div>

              <div className="heatmapInstructions">
                {mode === "left" && (
                  <>
                    <div className="heatmapInstructionTitle">Left Eye</div>
                    <ul>
                      <li>Cover your <b>right</b> eye.</li>
                      <li>Look at the center dot. Paint where floaters appear.</li>
                      <li>Use Light / Medium / Strong to reflect how noticeable they are.</li>
                    </ul>
                  </>
                )}
                {mode === "right" && (
                  <>
                    <div className="heatmapInstructionTitle">Right Eye</div>
                    <ul>
                      <li>Cover your <b>left</b> eye.</li>
                      <li>Look at the center dot. Paint where floaters appear.</li>
                      <li>Adjust brush size for broad vs precise areas.</li>
                    </ul>
                  </>
                )}
                {mode === "combined" && (
                  <>
                    <div className="heatmapInstructionTitle">Combined</div>
                    <ul>
                      <li>Use both eyes normally.</li>
                      <li>Paint what you experience overall.</li>
                      <li>If unsure, keep it light and set confidence lower.</li>
                    </ul>
                  </>
                )}
              </div>
            </div>

            <div className="heatmapControls card card--raised">
              <div className="heatmapControlsRow">
                <button
                  className={`heatBtn ${tool === "brush" ? "heatBtnActive" : ""}`}
                  onClick={() => setTool("brush")}
                >
                  Brush
                </button>
                <button
                  className={`heatBtn ${tool === "eraser" ? "heatBtnActive" : ""}`}
                  onClick={() => setTool("eraser")}
                >
                  Eraser
                </button>
              </div>

              <div className="heatmapSliderBlock">
                <div className="heatmapSliderLabelRow">
                  <div className="heatmapSliderLabel">Brush size</div>
                  <div className="heatmapSliderValue">{brushSize}px</div>
                </div>
                <input
                  className="heatmapSlider"
                  type="range"
                  min="12"
                  max="110"
                  value={brushSize}
                  onChange={(e) => setBrushSize(Number(e.target.value))}
                />
              </div>

              <div className="heatmapStrengthRow">
                <div className="heatmapSliderLabel">How noticeable?</div>
                <div className="heatmapStrengthBtns">
                  <button
                    className={`heatBtnSmall ${strength === 0.14 ? "heatBtnActive" : ""}`}
                    onClick={() => setStrength(0.14)}
                  >
                    Light
                  </button>
                  <button
                    className={`heatBtnSmall ${strength === 0.22 ? "heatBtnActive" : ""}`}
                    onClick={() => setStrength(0.22)}
                  >
                    Medium
                  </button>
                  <button
                    className={`heatBtnSmall ${strength === 0.32 ? "heatBtnActive" : ""}`}
                    onClick={() => setStrength(0.32)}
                  >
                    Strong
                  </button>
                </div>
              </div>

              <div className="heatmapControlsRow">
                <button className="heatBtn" onClick={undo} disabled={!canUndo}>
                  Undo
                </button>
                <button className="heatBtn" onClick={redo} disabled={!canRedo}>
                  Redo
                </button>
                <button className="heatBtn" onClick={resetCurrent}>
                  Reset
                </button>
              </div>

              <div className="heatmapSliderBlock">
                <div className="heatmapSliderLabelRow">
                  <div className="heatmapSliderLabel">Confidence (1–5)</div>
                  <div className="heatmapSliderValue">{confidence[mode]}</div>
                </div>
                <input
                  className="heatmapSlider"
                  type="range"
                  min="1"
                  max="5"
                  value={confidence[mode]}
                  onChange={(e) =>
                    setConfidence((c) => ({ ...c, [mode]: Number(e.target.value) }))
                  }
                />
              </div>
            </div>

            <div className="heatmapFooterRow">
              <button className="heatBtn" onClick={prevMode} disabled={mode === "left"}>
                Back
              </button>

              {mode !== "combined" ? (
                <button className="heatBtn heatBtnPrimary" onClick={nextMode}>
                  Save & Next
                </button>
              ) : (
                <button className="heatBtn heatBtnPrimary" onClick={finalize}>
                  Finish Exam
                </button>
              )}
            </div>
          </div>
        </aside>

        <main className="heatmapRight">
          <div className="heatmapCanvasWrap card noFloatersEffect" data-interactive="true">
            <div className="heatmapCanvasTopbar">
              <div className="heatmapCanvasTitle">
                {mode === "left" ? "Left Eye" : mode === "right" ? "Right Eye" : "Combined"}
              </div>
              <div className="heatmapCanvasHint">Paint on the field. Keep your gaze near the center dot.</div>
            </div>

            <div className="heatmapCanvasStage">
              <canvas
                ref={canvasRef}
                className="heatmapCanvas"
                onPointerDown={(e) => {
                  e.currentTarget.setPointerCapture(e.pointerId);
                  beginStroke(e);
                }}
                onPointerMove={moveStroke}
                onPointerUp={endStroke}
                onPointerCancel={endStroke}
                onPointerLeave={() => {
                  // If the pointer leaves while down, finalize stroke
                  endStroke();
                }}
              />
            </div>

            <div className="heatmapThumbRow">
              <HeatThumb label="L" active={mode === "left"} dataUrl={history.left.present} onClick={() => setMode("left")} />
              <HeatThumb label="R" active={mode === "right"} dataUrl={history.right.present} onClick={() => setMode("right")} />
              <HeatThumb
                label="C"
                active={mode === "combined"}
                dataUrl={history.combined.present}
                onClick={() => setMode("combined")}
              />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function ModePill({ active, children, onClick }) {
  return (
    <button className={`modePill ${active ? "modePillActive" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}

function HeatThumb({ label, active, dataUrl, onClick }) {
  return (
    <button className={`heatThumb ${active ? "heatThumbActive" : ""}`} onClick={onClick}>
      <div className="heatThumbLabel">{label}</div>
      <div className="heatThumbPreview">
        {dataUrl ? <img src={dataUrl} alt={`${label} preview`} /> : <div className="heatThumbEmpty">—</div>}
      </div>
    </button>
  );
}