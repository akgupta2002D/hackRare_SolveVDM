import { useEffect, useRef, useState } from "react";
import { createClient } from "@supabase/supabase-js";


// ─── Supabase client ──────────────────────────────────────────────────────────
const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);


// ─── Design tokens (mirrored from tokens.css) ────────────────────────────────
const T = {
  bg:           "#0b0c10",
  surface:      "#111318",
  surface2:     "#161922",
  surface3:     "#1b2030",
  text:         "#e8eaf0",
  muted:        "#a7adbd",
  muted2:       "#7f879a",
  border:       "rgba(255,255,255,0.08)",
  borderStrong: "rgba(255,255,255,0.14)",
  accent:       "#7aa2ff",
  accent2:      "#9b8cff",
  green:        "#0f3a2b",
  green2:       "#14503c",
  greenText:    "#4ade80",
  navy:         "#0f2147",
  navy2:        "#143062",
  gold:         "#C8A96E",
  fontSans:     "'IBM Plex Sans', system-ui, sans-serif",
  fontMono:     "'IBM Plex Mono', ui-monospace, monospace",
};


// ─── Shared canvas drawing function ──────────────────────────────────────────
function drawEyeToCanvas(canvas, paths, srcW = 393, srcH = 671, displaySize = 80) {
  if (!canvas || !paths?.length) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const dH  = displaySize * (srcH / srcW);


  canvas.width        = displaySize * dpr;
  canvas.height       = dH * dpr;
  canvas.style.width  = displaySize + "px";
  canvas.style.height = dH + "px";


  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);


  const scale = displaySize / srcW;
  const cx = displaySize / 2, cy = dH / 2;
  const rx = displaySize * 0.44, ry = dH * 0.28;


  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, displaySize, dH);


  ctx.save();
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  ctx.clip();
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, displaySize, dH);


  ctx.save();
  ctx.scale(scale, scale);
  for (const p of paths) {
    const cmds = p.d.match(/[ML][^ML]*/g) || [];
    ctx.save();
    ctx.globalAlpha = Math.min(1, Math.max(0, p.opacity));
    ctx.strokeStyle = "rgba(13,27,42,1)";
    ctx.lineWidth   = p.strokeWidth;
    ctx.lineCap     = "round";
    ctx.lineJoin    = "round";
    ctx.beginPath();
    for (const cmd of cmds) {
      const nums = cmd.slice(1).trim().split(/[\s,]+/).map(Number);
      if (cmd[0] === "M") ctx.moveTo(nums[0], nums[1]);
      else if (cmd[0] === "L") ctx.lineTo(nums[0], nums[1]);
    }
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
  ctx.restore();


  ctx.save();
  ctx.strokeStyle = "#DDD8CE";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  ctx.ellipse(cx, cy, ry * 0.9, ry * 0.9, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.ellipse(cx, cy, ry * 0.36, ry * 0.36, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();


  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  ctx.strokeStyle = "#0D1B2A";
  ctx.lineWidth = 2;
  ctx.stroke();
}


// ─── Thumbnail ────────────────────────────────────────────────────────────────
function EyeThumb({ paths, canvasWidth, canvasHeight, size = 200 }) {
  const ref = useRef(null);
  const [ok, setOk] = useState(false);
  useEffect(() => {
    drawEyeToCanvas(ref.current, paths, canvasWidth, canvasHeight, size);
    setOk(true);
  }, [paths, size]);
  return (
    <canvas
      ref={ref}
      style={{ borderRadius: 8, opacity: ok ? 1 : 0, transition: "opacity .2s", display: "block" }}
    />
  );
}


// ─── Helpers ──────────────────────────────────────────────────────────────────
function parsePaths(raw) {
  if (Array.isArray(raw)) return raw;
  try { return JSON.parse(raw); } catch { return []; }
}


function parseArtifacts(raw) {
  if (!raw) return {};
  if (typeof raw === "object") return raw;
  try { return JSON.parse(raw); } catch { return {}; }
}


function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}


function eyeLabel(name) {
  const l = name.toLowerCase();
  if (l.includes("left"))  return { text: "L", color: T.gold };
  if (l.includes("right")) return { text: "R", color: T.accent };
  return { text: "·", color: T.muted2 };
}


// ─── Shared style fragments ───────────────────────────────────────────────────
const sectionLabel = {
  fontSize: 10, fontWeight: 700, color: T.muted2,
  letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 10,
  fontFamily: T.fontMono,
};


const imgThumbStyle = {
  width: 200,
  borderRadius: 8,
  display: "block",
  border: `1px solid ${T.border}`,
};


// ─── Overlay image cell ───────────────────────────────────────────────────────
function OverlayThumb({ session: s }) {
  const artifacts = parseArtifacts(s.analysis_artifacts);
  const url = artifacts?.overlay_url;


  if (!url) {
    return (
      <div style={{
        width: 200, height: 138, borderRadius: 8,
        backgroundColor: T.surface3,
        border: `1px dashed ${T.border}`,
        display: "grid", placeItems: "center",
        color: T.muted2, fontSize: 11, fontFamily: T.fontMono,
      }}>
        —
      </div>
    );
  }


  return (
    <img
      src={url}
      alt="overlay"
      style={imgThumbStyle}
      onError={e => { e.target.style.display = "none"; }}
    />
  );
}


// ─── Detail Drawer ────────────────────────────────────────────────────────────
function Drawer({ session: s, onClose }) {
  const canvasRef = useRef(null);
  const [png, setPng] = useState(null);
  const paths = parsePaths(s.paths).filter(p => p.d.length > 10);
  const artifacts = parseArtifacts(s.analysis_artifacts);


  useEffect(() => {
    if (!canvasRef.current || !paths.length) return;
    drawEyeToCanvas(canvasRef.current, paths, s.canvas_width, s.canvas_height, 280);
    setPng(canvasRef.current.toDataURL("image/png"));
  }, [s]);


  const meta = [
    ["ID",            s.id],
    ["Created",       fmtDate(s.created_at)],
    ["Analysed",      s.analysed_at ? fmtDate(s.analysed_at) : "—"],
    ["Canvas",        s.canvas_width ? `${Math.round(s.canvas_width)} × ${Math.round(s.canvas_height)} px` : "—"],
    ["Strokes",       paths.length],
    ["Floater types", Array.isArray(s.floater_types) && s.floater_types.length ? s.floater_types.join(", ") : "—"],
    ["Stored image",  s.image_url ? "✓ Yes" : "—"],
  ];


  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        backgroundColor: "rgba(0,0,0,0.65)",
        zIndex: 100, display: "flex", justifyContent: "flex-end",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 460, height: "100%",
          backgroundColor: T.surface,
          borderLeft: `1px solid ${T.borderStrong}`,
          overflowY: "auto",
          padding: "28px 24px", boxSizing: "border-box",
          fontFamily: T.fontSans,
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: T.text, marginBottom: 4 }}>{s.name}</div>
            <div style={{ fontSize: 10, color: T.muted2, letterSpacing: "0.08em", fontFamily: T.fontMono }}>
              {s.id.slice(0, 8)}…
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: `1px solid ${T.border}`,
              color: T.muted2, borderRadius: 8, padding: "4px 10px",
              cursor: "pointer", fontSize: 13, fontFamily: T.fontMono,
              transition: "border-color .15s",
            }}
          >✕</button>
        </div>


        {/* Drawing canvas */}
        <div style={{
          backgroundColor: "#F5F0E8", borderRadius: 12,
          padding: 16, border: `1px solid ${T.border}`,
        }}>
          <canvas ref={canvasRef} style={{ display: "block", borderRadius: 8, margin: "0 auto" }} />
        </div>


        {png && (
          <a
            href={png}
            download={s.name.replace(/\s+/g, "_") + ".png"}
            style={{
              display: "block", marginTop: 10, textAlign: "center",
              padding: "8px 0", border: `1px solid ${T.gold}`, borderRadius: 8,
              color: T.gold, fontSize: 11, fontWeight: 700,
              letterSpacing: "0.1em", textDecoration: "none", fontFamily: T.fontMono,
            }}
          >↓ Export PNG</a>
        )}


        {/* Original + Overlay side-by-side */}
        {(s.image_url || artifacts?.overlay_url) && (
          <div style={{ marginTop: 28 }}>
            <div style={sectionLabel}>Images</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {s.image_url && (
                <div>
                  <div style={{ fontSize: 10, color: T.muted2, marginBottom: 6, fontFamily: T.fontMono, letterSpacing: "0.08em" }}>ORIGINAL</div>
                  <img
                    src={s.image_url} alt="original"
                    style={{ width: "100%", borderRadius: 8, border: `1px solid ${T.border}`, display: "block" }}
                    onError={e => { e.target.style.display = "none"; }}
                  />
                </div>
              )}
              {artifacts?.overlay_url && (
                <div>
                  <div style={{ fontSize: 10, color: T.muted2, marginBottom: 6, fontFamily: T.fontMono, letterSpacing: "0.08em" }}>OVERLAY</div>
                  <img
                    src={artifacts.overlay_url} alt="overlay"
                    style={{ width: "100%", borderRadius: 8, border: `1px solid ${T.border}`, display: "block" }}
                    onError={e => { e.target.style.display = "none"; }}
                  />
                </div>
              )}
            </div>
          </div>
        )}


        {/* Metadata */}
        <div style={{ marginTop: 28 }}>
          <div style={sectionLabel}>Metadata</div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <tbody>
              {meta.map(([k, v]) => (
                <tr key={k} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <td style={{
                    padding: "7px 0", color: T.muted2, fontWeight: 700,
                    fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase",
                    width: 130, fontFamily: T.fontMono,
                  }}>{k}</td>
                  <td style={{ padding: "7px 0", color: T.text, wordBreak: "break-all" }}>{String(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>


        {/* Analysis JSON */}
        {s.analysis_json && (
          <div style={{ marginTop: 28 }}>
            <div style={sectionLabel}>Analysis JSON</div>
            <pre style={{
              backgroundColor: T.bg, border: `1px solid ${T.border}`,
              borderRadius: 10, padding: 14, fontSize: 11, color: T.greenText,
              overflowX: "auto", margin: 0, lineHeight: 1.6,
              fontFamily: T.fontMono,
            }}>
              {typeof s.analysis_json === "string" ? s.analysis_json : JSON.stringify(s.analysis_json, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Main Page ────────────────────────────────────────────────────────────────
export default function SessionsPage() {
  const [sessions, setSessions] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [search,   setSearch]   = useState("");
  const [active,   setActive]   = useState(null);
  const [sort,     setSort]     = useState({ col: "created_at", dir: -1 });


  useEffect(() => {
    supabase
      .from("drawings")
      .select("*")
      .order("created_at", { ascending: false })
      .then(({ data, error }) => {
        if (error) setError(error.message);
        else setSessions(data || []);
        setLoading(false);
      });
  }, []);


  const toggleSort = col => setSort(s => ({ col, dir: s.col === col ? -s.dir : -1 }));


  const rows = [...sessions]
    .filter(s => s.name.toLowerCase().includes(search.toLowerCase()) || s.id.includes(search))
    .sort((a, b) => {
      const av = a[sort.col] ?? "", bv = b[sort.col] ?? "";
      return av < bv ? sort.dir : av > bv ? -sort.dir : 0;
    });


  // 4 columns: Original | Overlay | Info | Status
  const cols = [
    { key: "num",         label: "#",         sortable: false },
    { key: "drawing",     label: "Original",  sortable: false },
    { key: "overlay",     label: "Overlay",   sortable: false },
    { key: "info",        label: "Details",      sortable: true, sortKey: "name" },
    { key: "patient",     label: "Patient Info", sortable: false },
    { key: "status",      label: "Status",       sortable: true, sortKey: "analysed_at" },
  ];


  return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: T.bg,
      color: T.text,
      fontFamily: T.fontSans,
    }}>


      {/* ── Top bar ── */}
      <div style={{
        borderBottom: `1px solid ${T.borderStrong}`,
        padding: "18px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16,
        backgroundColor: T.surface,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div>
            <span style={{
              fontSize: 15, fontWeight: 700, letterSpacing: "0.22em",
              textTransform: "uppercase", fontFamily: T.fontMono,
            }}>Virtuous</span>
            <span style={{ fontSize: 12, color: T.muted2, marginLeft: 14, fontFamily: T.fontMono }}>
              {loading ? "Loading…" : `${sessions.length} records`}
            </span>
          </div>
        </div>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search name or ID…"
          style={{
            backgroundColor: T.surface2,
            border: `1px solid ${T.borderStrong}`,
            borderRadius: 10,
            color: T.text,
            padding: "8px 14px",
            fontSize: 13,
            outline: "none",
            width: 280,
            fontFamily: T.fontMono,
          }}
        />
      </div>


      {/* ── Description banner ── */}
      <div style={{
        backgroundColor: T.surface2,
        borderBottom: `1px solid ${T.border}`,
        padding: "20px 32px",
        display: "flex",
        alignItems: "flex-start",
        gap: 20,
      }}>


        <div>
          <div style={{
            fontSize: 14, fontWeight: 700, color: T.text,
            marginBottom: 6, letterSpacing: "0.02em",
          }}>
            Eye Floater Drawing Sessions
          </div>
          <p style={{
            margin: 0,
            fontSize: 13.5,
            color: T.muted,
            lineHeight: 1.7,
            maxWidth: 780,
          }}>
            This dashboard tracks patient-submitted drawings of visual floaters — the shapes, strands, and dots that
            appear in their field of vision. Each session captures a freehand sketch of what the patient sees,
            alongside an AI-generated overlay that maps and classifies the floater types detected. Use the table
            below to browse sessions, inspect individual drawings, and review analysis results.
          </p>
          <div style={{
            marginTop: 10,
            display: "flex", gap: 20, flexWrap: "wrap",
          }}>
            {[
              { label: "Total sessions", value: sessions.length || "…" },
              { label: "Analysed", value: sessions.filter(s => s.analysed_at).length || "…" },
              { label: "Pending", value: sessions.filter(s => !s.analysed_at).length || "…" },
            ].map(stat => (
              <div key={stat.label} style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                <span style={{
                  fontSize: 20, fontWeight: 700, color: T.accent,
                  fontFamily: T.fontMono, lineHeight: 1,
                }}>{stat.value}</span>
                <span style={{ fontSize: 11, color: T.muted2, fontFamily: T.fontMono, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  {stat.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>


      {/* ── Loading ── */}
      {loading && (
        <div style={{ padding: "80px 0", textAlign: "center" }}>
 
          <div style={{ color: T.muted2, fontSize: 13, fontFamily: T.fontMono }}>Fetching sessions…</div>
          <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
      )}


      {/* ── Error ── */}
      {error && (
        <div style={{
          margin: 32, padding: "16px 20px",
          backgroundColor: "rgba(90,20,22,0.3)",
          border: "1px solid rgba(122,28,31,0.6)",
          borderRadius: 10, color: "#f87171", fontSize: 13,
        }}>
          <strong>Supabase error:</strong> {error}
        </div>
      )}


      {/* ── Table ── */}
      {!loading && !error && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ backgroundColor: T.surface }}>
                {cols.map(c => {
                  const activeKey = c.sortKey || c.key;
                  const isActive  = sort.col === activeKey;
                  return (
                    <th
                      key={c.key}
                      onClick={() => c.sortable && toggleSort(activeKey)}
                      style={{
                        padding: "12px 18px", textAlign: "left",
                        borderBottom: `1px solid ${T.borderStrong}`,
                        color: isActive ? T.accent : T.muted2,
                        fontSize: 11, fontWeight: 700,
                        letterSpacing: "0.14em", textTransform: "uppercase",
                        whiteSpace: "nowrap", fontFamily: T.fontMono,
                        cursor: c.sortable ? "pointer" : "default",
                        userSelect: "none",
                        // Keep thumbnail columns narrow; status column tight
                        width: c.key === "num" ? 40
                             : c.key === "drawing" || c.key === "overlay" ? 216
                             : c.key === "info" ? 220
                             : c.key === "patient" ? 170
                             : c.key === "status" ? 130
                             : "auto",
                      }}
                    >
                      {c.label}{c.sortable && isActive ? (sort.dir === -1 ? " ↓" : " ↑") : ""}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((s, i) => {
                const paths     = parsePaths(s.paths).filter(p => p.d.length > 10);
                const artifacts = parseArtifacts(s.analysis_artifacts);
                const side      = eyeLabel(s.name);
                const base      = i % 2 === 0 ? T.surface2 : T.surface;
                const analysed  = !!s.analysed_at;


                return (
                  <tr
                    key={s.id}
                    style={{ backgroundColor: base, cursor: "pointer", transition: "background .12s" }}
                    onMouseEnter={e => e.currentTarget.style.backgroundColor = T.surface3}
                    onMouseLeave={e => e.currentTarget.style.backgroundColor = base}
                    onClick={() => setActive(s)}
                  >


                    {/* ── Col 0: Row number ── */}
                    <td style={{ padding: "6px 10px 6px 14px", borderBottom: `1px solid ${T.border}`, verticalAlign: "middle", width: 40, textAlign: "center" }}>
                      <span style={{
                        fontSize: 11, fontWeight: 700, color: T.muted2,
                        fontFamily: T.fontMono,
                      }}>{i + 1}</span>
                    </td>


                    {/* ── Col 1: Original drawing ── */}
                    <td style={{ padding: "6px 8px", borderBottom: `1px solid ${T.border}`, verticalAlign: "middle" }}>
                      {paths.length > 0
                        ? <EyeThumb paths={paths} canvasWidth={s.canvas_width} canvasHeight={s.canvas_height} size={200} />
                        : s.image_url
                          ? <img src={s.image_url} alt="" style={imgThumbStyle} />
                          : <div style={{
                              width: 200, height: 138, borderRadius: 8,
                              backgroundColor: T.surface3,
                              border: `1px dashed ${T.border}`,
                              display: "grid", placeItems: "center",
                              color: T.muted2, fontSize: 22,
                            }}>◎</div>
                      }
                    </td>


                    {/* ── Col 2: Overlay image ── */}
                    <td style={{ padding: "6px 8px", borderBottom: `1px solid ${T.border}`, verticalAlign: "middle" }}>
                      <OverlayThumb session={s} />
                    </td>


                    {/* ── Col 3: Merged info ── */}
                    <td style={{ padding: "6px 10px", borderBottom: `1px solid ${T.border}`, verticalAlign: "middle", width: 220 }}>
                      {/* Name + eye badge */}
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
                        <span style={{
                          fontSize: 10, fontWeight: 800,
                          border: `1px solid ${side.color}`, borderRadius: 4,
                          padding: "2px 6px", color: side.color,
                          flexShrink: 0, fontFamily: T.fontMono,
                          letterSpacing: "0.06em",
                        }}>
                          {side.text}
                        </span>
                        <span style={{ color: T.text, fontWeight: 600, fontSize: 15 }}>{s.name}</span>
                      </div>


                      {/* ID */}
                      <div style={{ fontSize: 12, color: T.muted2, fontFamily: T.fontMono, marginBottom: 6 }}>
                        {s.id.slice(0, 8)}…
                      </div>


                      {/* Strokes + floater types inline */}
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 6 }}>
                        <span style={{
                          backgroundColor: T.navy, color: T.accent,
                          borderRadius: 20, padding: "3px 11px",
                          fontSize: 12, fontWeight: 700, fontFamily: T.fontMono,
                        }}>
                          {paths.length} strokes
                        </span>
                        {Array.isArray(s.floater_types) && s.floater_types.map(ft => (
                          <span key={ft} style={{
                            backgroundColor: "rgba(155,140,255,0.12)",
                            color: T.accent2, borderRadius: 20,
                            padding: "3px 11px", fontSize: 12,
                            fontWeight: 600, fontFamily: T.fontMono,
                          }}>
                            {ft}
                          </span>
                        ))}
                      </div>


                      {/* Dates */}
                      <div style={{ fontSize: 12, color: T.muted2, fontFamily: T.fontMono, lineHeight: 1.7 }}>
                        <span style={{ color: T.muted, marginRight: 4 }}>created</span>{fmtDate(s.created_at)}
                      </div>
                      {s.analysed_at && (
                        <div style={{ fontSize: 12, color: T.greenText, fontFamily: T.fontMono, lineHeight: 1.7 }}>
                          <span style={{ color: T.muted, marginRight: 4 }}>analysed</span>{fmtDate(s.analysed_at)}
                        </div>
                      )}
                    </td>


                    {/* ── Col 4: Patient Info ── */}
                    <td style={{ padding: "6px 10px", borderBottom: `1px solid ${T.border}`, verticalAlign: "middle", width: 170 }}>
                      {[
                        { label: "Have floaters for", value: null },
                        { label: "Age",               value: null },
                        { label: "Gender",            value: null },
                      ].map(({ label, value }) => (
                        <div key={label} style={{ marginBottom: 5 }}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, color: T.muted2,
                            fontFamily: T.fontMono, letterSpacing: "0.08em",
                            textTransform: "uppercase", marginRight: 6,
                          }}>{label}:</span>
                          <span style={{
                            fontSize: 11, color: T.muted2,
                            fontFamily: T.fontMono, fontStyle: "italic",
                            opacity: 0.6,
                          }}>* To be updated</span>
                        </div>
                      ))}
                    </td>


                    {/* ── Col 5: Status ── */}
                    <td style={{ padding: "6px 14px", borderBottom: `1px solid ${T.border}`, verticalAlign: "middle", width: 140 }}>
                      <span style={{
                        fontSize: 12, fontWeight: 700, borderRadius: 20,
                        padding: "5px 14px", display: "inline-block",
                        fontFamily: T.fontMono, letterSpacing: "0.06em",
                        whiteSpace: "nowrap",
                        ...(analysed
                          ? { backgroundColor: "rgba(15,58,43,0.6)", color: T.greenText, border: `1px solid rgba(74,222,128,0.2)` }
                          : { backgroundColor: T.surface3, color: T.muted2, border: `1px solid ${T.border}` })
                      }}>
                        {analysed ? "✓ Analysed" : "Pending"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>


          {rows.length === 0 && (
            <div style={{ padding: "80px 0", textAlign: "center" }}>
              <div style={{ fontSize: 48, color: T.surface3, marginBottom: 16 }}>◎</div>
              <div style={{ color: T.muted2, fontSize: 14, fontFamily: T.fontMono }}>
                No sessions match "{search}"
              </div>
            </div>
          )}
        </div>
      )}


      {/* ── Slide-in drawer ── */}
      {active && <Drawer session={active} onClose={() => setActive(null)} />}
    </div>
  );
}

