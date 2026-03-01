import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * BackgroundFloaters
 * - Tracks mouse movement only when not hovering interactive elements.
 * - Spawns short "chains" of floaters along the mouse path.
 * - Floaters drift briefly, then "fall" down.
 * - Fallen floaters contribute to revealing a message (simple reveal meter).
 *
 * Props:
 *  - messages: array of strings (empowering messages)
 *  - onMessageReveal: optional callback when a message is revealed
 */
export default function BackgroundFloaters({
  messages = [
    "You’re building something that matters.",
    "Small steps. Massive momentum.",
    "Your work has impact—keep going.",
  ],
  onMessageReveal,
}) {
  const [floaters, setFloaters] = useState([]);
  const [reveal, setReveal] = useState(0); // 0..1
  const [messageIndex, setMessageIndex] = useState(0);

  const containerRef = useRef(null);
  const lastPosRef = useRef({ x: 0, y: 0, t: 0 });
  const chainBudgetRef = useRef(0); // accumulates based on movement distance
  const nextIdRef = useRef(1);
  const rafRef = useRef(null);

  const message = useMemo(() => messages[messageIndex % messages.length], [messages, messageIndex]);

  // Helper: detect whether target is "interactive"
  function isInteractiveTarget(el) {
    if (!el) return false;
    return Boolean(
      el.closest(
        'button, a, input, textarea, select, [role="button"], [role="dialog"], [data-modal="true"], [data-interactive="true"]'
      )
    );
  }

  // Spawn a floater
  function spawnFloater(x, y, vx, vy) {
    const id = nextIdRef.current++;
    const lifeMs = 1800 + Math.random() * 900; // drift time
    const createdAt = performance.now();

    return {
      id,
      x,
      y,
      vx,
      vy,
      // visual variety
      size: 6 + Math.random() * 10,
      rot: Math.random() * 360,
      rotV: (-60 + Math.random() * 120),
      opacity: 0.3 + Math.random() * 0.6,
      phase: "float", // "float" -> "fall" -> "dead"
      createdAt,
      floatUntil: createdAt + lifeMs,
      // fall speed starts small, accelerates
      fallVy: 80 + Math.random() * 120,
    };
  }

  // Build a "chain" along the movement vector
  function spawnChain(from, to) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 2) return;

    // accumulate budget so slow moves still create occasional floaters
    chainBudgetRef.current += dist;

    // spawn every N pixels of movement
    const step = 18; // smaller = denser chains
    const count = Math.floor(chainBudgetRef.current / step);
    if (count <= 0) return;

    chainBudgetRef.current -= count * step;

    const nx = dx / dist;
    const ny = dy / dist;

    const chain = [];
    for (let i = 0; i < count; i++) {
      const u = (i + 1) / (count + 1);
      const px = from.x + dx * u;
      const py = from.y + dy * u;

      // slight sideways jitter
      const jx = (-ny) * (Math.random() * 10 - 5);
      const jy = (nx) * (Math.random() * 10 - 5);

      // initial drift velocity
      const vx = nx * (20 + Math.random() * 30) + (Math.random() * 20 - 10);
      const vy = ny * (20 + Math.random() * 30) + (Math.random() * 20 - 10);

      chain.push(spawnFloater(px + jx, py + jy, vx, vy));
    }

    // cap total floaters to avoid perf issues
    setFloaters((prev) => {
      const merged = [...prev, ...chain];
      const max = 240;
      return merged.length > max ? merged.slice(merged.length - max) : merged;
    });
  }

  // Animation loop
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let lastT = performance.now();

    function tick(now) {
      const dt = Math.min(0.032, (now - lastT) / 1000);
      lastT = now;

      const rect = el.getBoundingClientRect();
      const height = rect.height;

      setFloaters((prev) => {
        let fallenThisFrame = 0;

        const next = prev
          .map((f) => {
            // rotation
            const rot = f.rot + f.rotV * dt;

            if (f.phase === "float") {
              const x = f.x + f.vx * dt;
              const y = f.y + f.vy * dt;

              // gentle drag
              const vx = f.vx * (1 - 0.8 * dt);
              const vy = f.vy * (1 - 0.8 * dt);

              if (now >= f.floatUntil) {
                return { ...f, x, y, vx, vy, rot, phase: "fall" };
              }
              return { ...f, x, y, vx, vy, rot };
            }

            if (f.phase === "fall") {
              const fallVy = f.fallVy + 600 * dt; // accelerate
              const y = f.y + fallVy * dt;
              const x = f.x + f.vx * dt * 0.2; // tiny sideways drift
              const opacity = Math.max(0, f.opacity - 0.6 * dt);

              // once it crosses bottom (or fades), count as "fallen"
              if (y > height + 40 || opacity <= 0.02) {
                fallenThisFrame += 1;
                return { ...f, x, y, fallVy, rot, opacity, phase: "dead" };
              }
              return { ...f, x, y, fallVy, rot, opacity };
            }

            return f;
          })
          .filter((f) => f.phase !== "dead");

        if (fallenThisFrame > 0) {
          // increase reveal progress based on how many fell
          setReveal((r) => {
            const nr = Math.min(1, r + fallenThisFrame / 180);
            return nr;
          });
        }

        return next;
      });

      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // When reveal hits 1, swap message and reset reveal slowly
  useEffect(() => {
    if (reveal < 1) return;

    onMessageReveal?.(message);

    const timeout = setTimeout(() => {
      setMessageIndex((i) => i + 1);
      setReveal(0);
    }, 1200);

    return () => clearTimeout(timeout);
  }, [reveal, message, onMessageReveal]);

  // Mouse tracking: only spawn chains when not hovering interactive UI
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    function onMove(e) {
      const target = e.target;
      if (isInteractiveTarget(target)) {
        // reset last position so chain doesn't jump when leaving UI
        lastPosRef.current = { x: e.clientX, y: e.clientY, t: performance.now() };
        return;
      }

      const now = performance.now();
      const last = lastPosRef.current;

      // rate limit to avoid huge spawn on high Hz mice
      if (now - last.t < 12) return;

      const from = { x: last.x, y: last.y };
      const to = { x: e.clientX, y: e.clientY };

      spawnChain(from, to);

      lastPosRef.current = { x: to.x, y: to.y, t: now };
    }

    // Init last position (prevents first move jump)
    function onEnter(e) {
      lastPosRef.current = { x: e.clientX, y: e.clientY, t: performance.now() };
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mouseenter", onEnter);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseenter", onEnter);
    };
  }, []);

  return (
    <div ref={containerRef} style={styles.container} aria-hidden="true">
      {/* Floaters */}
      {floaters.map((f) => (
        <span
          key={f.id}
          style={{
            ...styles.floater,
            width: f.size,
            height: f.size,
            transform: `translate(${f.x}px, ${f.y}px) rotate(${f.rot}deg)`,
            opacity: f.opacity,
          }}
        />
      ))}

      {/* Message reveal (simple mask via clipPath width) */}
      <div style={styles.messageWrap}>
        <div style={{ ...styles.messageMask, width: `${Math.round(reveal * 100)}%` }}>
          <div style={styles.message}>{message}</div>
        </div>
        <div style={styles.messageGhost}>{message}</div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: "fixed",
    inset: 0,
    zIndex: 0,
    pointerEvents: "none", // important: doesn’t block clicks
    overflow: "hidden",
  },
  floater: {
    position: "absolute",
    borderRadius: 999,
    background: "rgba(255,255,255,0.9)",
    boxShadow: "0 0 18px rgba(255,255,255,0.15)",
    filter: "blur(0px)",
    willChange: "transform, opacity",
  },
  messageWrap: {
    position: "absolute",
    left: "50%",
    bottom: "9%",
    transform: "translateX(-50%)",
    width: "min(820px, 92vw)",
    textAlign: "center",
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    pointerEvents: "none",
  },
  message: {
    fontSize: "clamp(18px, 2.2vw, 28px)",
    fontWeight: 650,
    letterSpacing: "-0.01em",
    color: "rgba(255,255,255,0.95)",
    textShadow: "0 10px 30px rgba(0,0,0,0.55)",
    padding: "10px 14px",
    borderRadius: 16,
    backdropFilter: "blur(6px)",
    background: "rgba(0,0,0,0.22)",
    display: "inline-block",
  },
  messageGhost: {
    // subtle outline behind so unrevealed text is faint
    fontSize: "clamp(18px, 2.2vw, 28px)",
    fontWeight: 650,
    letterSpacing: "-0.01em",
    color: "rgba(255,255,255,0.12)",
    textShadow: "0 10px 30px rgba(0,0,0,0.45)",
    padding: "10px 14px",
    borderRadius: 16,
    display: "inline-block",
    position: "absolute",
    left: "50%",
    transform: "translateX(-50%)",
    bottom: 0,
    whiteSpace: "nowrap",
  },
  messageMask: {
    overflow: "hidden",
    display: "inline-block",
    whiteSpace: "nowrap",
  },
};