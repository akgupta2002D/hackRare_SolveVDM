import { useEffect, useMemo, useRef, useState } from "react";

/**
 * useBackgroundFloaters
 * ---------------------
 * This hook owns ALL behavior:
 *  - "Only spawn floaters when enabled"
 *  - "Do NOT spawn floaters when hovering interactive UI"
 *  - "Spawn chains along mouse movement"
 *  - "Float briefly then fall down"
 *  - "After enough floaters 'fall', show a message briefly then hide it"
 *
 * It returns render-ready state for BackgroundFloatersLayer:
 *  - containerRef: the full-screen background container
 *  - floaters: array of floater particles
 *  - messageVisible + typedMessage: reveal message logic
 */
export default function useBackgroundFloaters({
  enabled,
  messages,
  revealThreshold,
  messageDurationMs,
}) {
  const [floaters, setFloaters] = useState([]);

  const [typedMessage, setTypedMessage] = useState("");
  const [messageIndex, setMessageIndex] = useState(0);
  const [messageVisible, setMessageVisible] = useState(false);

  const messageVisibleRef = useRef(false);

  useEffect(() => {
    messageVisibleRef.current = messageVisible;
  }, [messageVisible]);

  const containerRef = useRef(null);

  // Timers so we can reliably cancel them on unmount / retrigger
  const typingIntervalRef = useRef(null);
  const hideTimeoutRef = useRef(null);

  /**
   * Mouse tracking state:
   *  - lastPosRef: last known cursor position + timestamp
   *  - chainBudgetRef: accumulates distance moved so slow moves still produce floaters
   */
  const lastPosRef = useRef({ x: 0, y: 0, t: 0 });
  const chainBudgetRef = useRef(0);

  /**
   * Particle bookkeeping:
   *  - nextIdRef: unique id counter for stable rendering keys
   *  - rafRef: requestAnimationFrame handle so we can cancel on unmount
   */
  const nextIdRef = useRef(1);
  const rafRef = useRef(null);

  /**
   * Reveal bookkeeping:
   * fallCountRef tracks how many floaters "finished falling" since last message.
   * When it crosses revealThreshold, we show the message.
   */
  const fallCountRef = useRef(0);

  /**
   * Current message based on index.
   */
  const message = useMemo(
    () => messages[messageIndex % messages.length],
    [messages, messageIndex]
  );

  /**
   * isBlockedTarget(el)
   * -------------------
   * Determines whether floaters should NOT spawn.
   */
  function isBlockedTarget(el) {
    if (!el) return false;

    return Boolean(
      el.closest(
        [
          "button",
          "a",
          "input",
          "textarea",
          "select",
          "[role='button']",
          "[role='dialog']",
          ".noFloatersEffect",
        ].join(",")
      )
    );
  }

  /**
   * startTypewriter(fullText)
   * -------------------------
   * Shows the message bubble, types it out, then hides it after `messageDurationMs`
   * once typing is finished.
   */
  function startTypewriter(fullText, messageDurationMs) {
    if (typingIntervalRef.current) {
      window.clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }
    if (hideTimeoutRef.current) {
      window.clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }

    setMessageVisible(true);
    messageVisibleRef.current = true;
    setTypedMessage("");

    const charDelay = 22;

    let i = 0;
    typingIntervalRef.current = window.setInterval(() => {
      i += 1;
      setTypedMessage(fullText.slice(0, i));

      if (i >= fullText.length) {
        window.clearInterval(typingIntervalRef.current);
        typingIntervalRef.current = null;

        hideTimeoutRef.current = window.setTimeout(() => {
          setMessageVisible(false);
          messageVisibleRef.current = false;
          setTypedMessage("");
          setMessageIndex((idx) => idx + 1);
          hideTimeoutRef.current = null;
        }, messageDurationMs);
      }
    }, charDelay);
  }

  /**
   * spawnFloater(x, y, vx, vy)
   * --------------------------
   * Creates a new particle object.
   */
  function spawnFloater(x, y, vx, vy) {
    const id = nextIdRef.current++;
    const createdAt = performance.now();

    const lifeMs = 1800 + Math.random() * 900;

    return {
      id,
      x,
      y,

      vx,
      vy,

      size: 6 + Math.random() * 10,
      rot: Math.random() * 360,
      rotV: -60 + Math.random() * 120,
      opacity: 0.3 + Math.random() * 0.6,

      phase: "float",
      createdAt,
      floatUntil: createdAt + lifeMs,

      fallVy: 80 + Math.random() * 120,
    };
  }

  /**
   * spawnChain(from, to)
   * --------------------
   * Given two cursor points, we place a "chain" of floaters along the path.
   */
  function spawnChain(from, to) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 2) return;

    chainBudgetRef.current += dist;

    const step = 18;
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

      const jx = -ny * (Math.random() * 10 - 5);
      const jy = nx * (Math.random() * 10 - 5);

      const vx = nx * (20 + Math.random() * 30) + (Math.random() * 20 - 10);
      const vy = ny * (20 + Math.random() * 30) + (Math.random() * 20 - 10);

      chain.push(spawnFloater(px + jx, py + jy, vx, vy));
    }

    setFloaters((prev) => {
      const merged = [...prev, ...chain];
      const max = 240;
      return merged.length > max ? merged.slice(merged.length - max) : merged;
    });
  }

  /**
   * ✅ FULL ANIMATION LOOP
   * - updates particles each frame
   * - counts "finished falling"
   * - triggers typed message when threshold reached
   */
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
            const rot = f.rot + f.rotV * dt;

            // PHASE 1: FLOAT
            if (f.phase === "float") {
              const x = f.x + f.vx * dt;
              const y = f.y + f.vy * dt;

              const vx = f.vx * (1 - 0.8 * dt);
              const vy = f.vy * (1 - 0.8 * dt);

              if (now >= f.floatUntil) {
                return { ...f, x, y, vx, vy, rot, phase: "fall" };
              }
              return { ...f, x, y, vx, vy, rot };
            }

            // PHASE 2: FALL
            if (f.phase === "fall") {
              const fallVy = f.fallVy + 600 * dt;

              const y = f.y + fallVy * dt;
              const x = f.x + f.vx * dt * 0.2;

              const opacity = Math.max(0, f.opacity - 0.6 * dt);

              if (y > height + 40 || opacity <= 0.02) {
                fallenThisFrame += 1;
                return { ...f, x, y, fallVy, rot, opacity, phase: "dead" };
              }

              return { ...f, x, y, fallVy, rot, opacity };
            }

            return f;
          })
          .filter((f) => f.phase !== "dead");

        // REVEAL LOGIC
        if (fallenThisFrame > 0) {
          fallCountRef.current += fallenThisFrame;

          if (
            !messageVisibleRef.current &&
            fallCountRef.current >= revealThreshold
          ) {
            fallCountRef.current = 0;

            // prevent double-trigger while state is pending
            messageVisibleRef.current = true;

            startTypewriter(message, messageDurationMs);
          }
        }

        return next;
      });

      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);

      if (typingIntervalRef.current)
        window.clearInterval(typingIntervalRef.current);
      if (hideTimeoutRef.current) window.clearTimeout(hideTimeoutRef.current);

      typingIntervalRef.current = null;
      hideTimeoutRef.current = null;
    };

    // ✅ IMPORTANT FIX:
    // Removing `messageVisible` prevents the RAF effect cleanup from
    // killing the typewriter timers the instant the message is shown.
  }, [revealThreshold, messageDurationMs, message]);

  /**
   * Mouse tracking
   * --------------
   * Spawns chains along the mouse movement path IF:
   *  - enabled is true
   *  - hovered element is not interactive
   */
  useEffect(() => {
    function onMove(e) {
      if (!enabled) return;

      if (isBlockedTarget(e.target)) {
        lastPosRef.current = {
          x: e.clientX,
          y: e.clientY,
          t: performance.now(),
        };
        return;
      }

      const now = performance.now();
      const last = lastPosRef.current;
      if (now - last.t < 12) return;

      const from = { x: last.x, y: last.y };
      const to = { x: e.clientX, y: e.clientY };

      spawnChain(from, to);

      lastPosRef.current = { x: to.x, y: to.y, t: now };
    }

    function onEnter(e) {
      lastPosRef.current = { x: e.clientX, y: e.clientY, t: performance.now() };
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mouseenter", onEnter);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseenter", onEnter);
    };
  }, [enabled]);

  return { containerRef, floaters, messageVisible, typedMessage };
}