import { useEffect, useRef, useState } from "react";
import { createClient } from "@supabase/supabase-js";

// ─── Supabase client ──────────────────────────────────────────────────────────
// Add these two to your .env file:
//   VITE_SUPABASE_URL=https://yourproject.supabase.co
//   VITE_SUPABASE_ANON_KEY=your-anon-key
const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);

// ─── Shared canvas drawing function ──────────────────────────────────────────
function drawEyeToCanvas(canvas, paths, srcW = 393, srcH = 671, displaySize = 80) {
  if (!canvas || !paths?.length) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const dH  = displaySize * (srcH / srcW);

  canvas.width        = displaySize * dpr;
  canvas.height       = dH * dpr;
  canvas.style.width  = displaySize + "px";
  canvas.style.height = dH + "px";

  const ctx   = canvas.getContext("2d");
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
function EyeThumb({ paths, canvasWidth, canvasHeight }) {
  const ref = useRef(null);
  const [ok, setOk] = useState(false);
  useEffect(() => {
    drawEyeToCanvas(ref.current, paths, canvasWidth, canvasHeight, 72);
    setOk(true);
  }, [paths]);
  return <canvas ref={ref} style={{ borderRadius: 6, opacity: ok ? 1 : 0, transition: "opacity .2s", display: "block" }} />;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function parsePaths(raw) {
  if (Array.isArray(raw)) return raw;
  try { return JSON.parse(raw); } catch { return []; }
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
  if (l.includes("left"))  return { text: "L", color: "#C8A96E" };
  if (l.includes("right")) return { text: "R", color: "#7EB8D4" };
  return { text: "·", color: "#8A9BB0" };
}

// ─── Detail Drawer ────────────────────────────────────────────────────────────
function Drawer({ session: s, onClose }) {
  const canvasRef = useRef(null);
  const [png, setPng] = useState(null);
  const paths = parsePaths(s.paths).filter(p => p.d.length > 10);

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
    ["Artifacts",     Array.isArray(s.analysis_artifacts) && s.analysis_artifacts.length ? s.analysis_artifacts.length : "—"],
    ["Stored image",  s.image_url ? "✓ Yes" : "—"],
  ];

  return (
    <div
      onClick={onClose}
      style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.55)", zIndex: 100, display: "flex", justifyContent: "flex-end" }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 440, height: "100%", backgroundColor: "#111E2D",
          borderLeft: "1px solid #243447", overflowY: "auto",
          padding: "28px 24px", boxSizing: "border-box",
          fontFamily: "'DM Mono','Courier New',monospace",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#F5F0E8", marginBottom: 4 }}>{s.name}</div>
            <div style={{ fontSize: 10, color: "#8A9BB0", letterSpacing: 1 }}>{s.id.slice(0, 8)}…</div>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "1px solid #243447", color: "#8A9BB0", borderRadius: 6, padding: "4px 10px", cursor: "pointer", fontSize: 13, fontFamily: "inherit" }}
          >✕</button>
        </div>

        {/* Canvas preview */}
        <div style={{ backgroundColor: "#F5F0E8", borderRadius: 12, padding: 16, border: "1px solid #243447" }}>
          <canvas ref={canvasRef} style={{ display: "block", borderRadius: 8, margin: "0 auto" }} />
        </div>

        {png && (
          <a
            href={png}
            download={s.name.replace(/\s+/g, "_") + ".png"}
            style={{
              display: "block", marginTop: 10, textAlign: "center",
              padding: "8px 0", border: "1px solid #C8A96E", borderRadius: 6,
              color: "#C8A96E", fontSize: 11, fontWeight: 700, letterSpacing: 1, textDecoration: "none",
            }}
          >↓ Export PNG</a>
        )}

        {/* Stored image */}
        {s.image_url && (
          <div style={{ marginTop: 28 }}>
            <div style={sectionLabel}>Stored Image</div>
            <img
              src={s.image_url} alt="stored"
              style={{ width: "100%", maxWidth: 280, borderRadius: 8, border: "1px solid #243447", display: "block" }}
              onError={e => { e.target.style.display = "none"; }}
            />
          </div>
        )}

        {/* Metadata table */}
        <div style={{ marginTop: 28 }}>
          <div style={sectionLabel}>Metadata</div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <tbody>
              {meta.map(([k, v]) => (
                <tr key={k} style={{ borderBottom: "1px solid #1E3048" }}>
                  <td style={{ padding: "7px 0", color: "#8A9BB0", fontWeight: 700, fontSize: 10, letterSpacing: 1, textTransform: "uppercase", width: 130 }}>{k}</td>
                  <td style={{ padding: "7px 0", color: "#F5F0E8", wordBreak: "break-all" }}>{String(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Analysis JSON */}
        {s.analysis_json && (
          <div style={{ marginTop: 28 }}>
            <div style={sectionLabel}>Analysis JSON</div>
            <pre style={{ backgroundColor: "#0D1B2A", border: "1px solid #243447", borderRadius: 8, padding: 14, fontSize: 11, color: "#8EC6A0", overflowX: "auto", margin: 0, lineHeight: 1.6 }}>
              {typeof s.analysis_json === "string" ? s.analysis_json : JSON.stringify(s.analysis_json, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

const sectionLabel = {
  fontSize: 9, fontWeight: 700, color: "#8A9BB0",
  letterSpacing: 2, textTransform: "uppercase", marginBottom: 10,
};

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

  const cols = [
    { key: "drawing",      label: "Drawing",    sortable: false },
    { key: "name",         label: "Name",        sortable: true  },
    { key: "strokes",      label: "Strokes",     sortable: false },
    { key: "canvas_width", label: "Dimensions",  sortable: false },
    { key: "created_at",   label: "Created",     sortable: true  },
    { key: "analysed_at",  label: "Analysed",    sortable: true  },
    { key: "status",       label: "Status",      sortable: false },
  ];

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0D1B2A", color: "#F5F0E8", fontFamily: "'DM Mono','Courier New',monospace" }}>

      {/* Top bar */}
      <div style={{ borderBottom: "1px solid #243447", padding: "18px 32px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <span style={{ fontSize: 26, color: "#C8A96E" }}>◉</span>
          <div>
            <span style={{ fontSize: 17, fontWeight: 800, letterSpacing: 6 }}>SESSIONS</span>
            <span style={{ fontSize: 11, color: "#4A6080", marginLeft: 14 }}>
              {loading ? "Loading…" : `${sessions.length} records`}
            </span>
          </div>
        </div>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search name or ID…"
          style={{
            backgroundColor: "#162438", border: "1px solid #243447", borderRadius: 7,
            color: "#F5F0E8", padding: "8px 14px", fontSize: 13,
            outline: "none", width: 280, fontFamily: "inherit",
          }}
        />
      </div>

      {/* Loading state */}
      {loading && (
        <div style={{ padding: "80px 0", textAlign: "center" }}>
          <div style={{ fontSize: 36, color: "#243447", marginBottom: 16, animation: "spin 2s linear infinite", display: "inline-block" }}>◉</div>
          <div style={{ color: "#4A6080", fontSize: 13 }}>Fetching sessions…</div>
          <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div style={{ margin: 32, padding: "16px 20px", backgroundColor: "rgba(200,80,80,0.1)", border: "1px solid rgba(200,80,80,0.3)", borderRadius: 8, color: "#E08080", fontSize: 13 }}>
          <strong>Supabase error:</strong> {error}
        </div>
      )}

      {/* Table */}
      {!loading && !error && (
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ backgroundColor: "#091624" }}>
              {cols.map(c => (
                <th
                  key={c.key}
                  onClick={() => c.sortable && toggleSort(c.key)}
                  style={{
                    padding: "11px 16px", textAlign: "left",
                    borderBottom: "1px solid #243447",
                    color: sort.col === c.key ? "#C8A96E" : "#8A9BB0",
                    fontSize: 10, fontWeight: 700, letterSpacing: 2,
                    textTransform: "uppercase", whiteSpace: "nowrap",
                    cursor: c.sortable ? "pointer" : "default", userSelect: "none",
                  }}
                >
                  {c.label}{c.sortable && sort.col === c.key ? (sort.dir === -1 ? " ↓" : " ↑") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((s, i) => {
              const paths = parsePaths(s.paths).filter(p => p.d.length > 10);
              const side  = eyeLabel(s.name);
              const base  = i % 2 === 0 ? "#162438" : "#122030";

              return (
                <tr
                  key={s.id}
                  style={{ backgroundColor: base, cursor: "pointer" }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = "#1c2e44"}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = base}
                  onClick={() => setActive(s)}
                >
                  {/* Thumbnail */}
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #1a2a3a", verticalAlign: "middle" }}>
                    {paths.length > 0
                      ? <EyeThumb paths={paths} canvasWidth={s.canvas_width} canvasHeight={s.canvas_height} />
                      : s.image_url
                        ? <img src={s.image_url} alt="" style={{ width: 72, borderRadius: 6, display: "block" }} />
                        : <div style={{ width: 72, height: 50, borderRadius: 6, backgroundColor: "#1E3048", display: "grid", placeItems: "center", color: "#4A6080" }}>◎</div>
                    }
                  </td>

                  {/* Name + badge */}
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #1a2a3a", verticalAlign: "middle" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 10, fontWeight: 800, border: `1px solid ${side.color}`, borderRadius: 4, padding: "2px 7px", color: side.color, flexShrink: 0 }}>
                        {side.text}
                      </span>
                      <div>
                        <div style={{ color: "#F5F0E8", fontWeight: 600, marginBottom: 2 }}>{s.name}</div>
                        <div style={{ color: "#4A6080", fontSize: 11 }}>{s.id.slice(0, 8)}…</div>
                      </div>
                    </div>
                  </td>

                  {/* Strokes */}
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #1a2a3a", verticalAlign: "middle" }}>
                    <span style={{ backgroundColor: "#1E3048", color: "#C8A96E", borderRadius: 20, padding: "3px 11px", fontSize: 12, fontWeight: 700, display: "inline-block" }}>
                      {paths.length}
                    </span>
                  </td>

                  {/* Dimensions */}
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #1a2a3a", verticalAlign: "middle", color: "#8A9BB0" }}>
                    {s.canvas_width ? `${Math.round(s.canvas_width)} × ${Math.round(s.canvas_height)}` : "—"}
                  </td>

                  {/* Created */}
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #1a2a3a", verticalAlign: "middle", color: "#8A9BB0", fontSize: 12 }}>
                    {fmtDate(s.created_at)}
                  </td>

                  {/* Analysed */}
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #1a2a3a", verticalAlign: "middle", fontSize: 12, color: s.analysed_at ? "#8EC6A0" : "#2e4a66" }}>
                    {s.analysed_at ? fmtDate(s.analysed_at) : "—"}
                  </td>

                  {/* Status */}
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #1a2a3a", verticalAlign: "middle" }}>
                    <span style={{
                      fontSize: 11, fontWeight: 700, borderRadius: 20, padding: "3px 11px", display: "inline-block",
                      ...(s.analysed_at
                        ? { backgroundColor: "rgba(142,198,160,0.1)", color: "#8EC6A0" }
                        : { backgroundColor: "rgba(42,60,90,0.4)",     color: "#4A6080" })
                    }}>
                      {s.analysed_at ? "✓ Analysed" : "Pending"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {rows.length === 0 && (
          <div style={{ padding: "80px 0", textAlign: "center" }}>
            <div style={{ fontSize: 48, color: "#1E3048", marginBottom: 16 }}>◎</div>
            <div style={{ color: "#4A6080", fontSize: 14 }}>No sessions match "{search}"</div>
          </div>
        )}
      </div>

      )}

      {/* Slide-in drawer */}
      {active && <Drawer session={active} onClose={() => setActive(null)} />}
    </div>
  );
}