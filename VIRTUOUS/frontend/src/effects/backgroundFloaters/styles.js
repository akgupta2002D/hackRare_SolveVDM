/**
 * Keep styles in one place so you can theme/tweak easily later.
 * (You can replace with Tailwind/CSS Modules whenever you want.)
 */
export const layerStyles = {
  container: {
    position: "fixed",
    inset: 0,
    zIndex: 0,

    /**
     * pointerEvents none is crucial:
     * - Background effects never block clicks
     * - Hover/click goes to your UI layer above
     */
    pointerEvents: "none",
    overflow: "hidden",
  },

  floater: {
    position: "absolute",
    borderRadius: 999,
    background: "rgba(255,255,255,0.9)",
    boxShadow: "0 0 18px rgba(255,255,255,0.15)",
    willChange: "transform, opacity",
  },

  messageWrap: {
    position: "absolute",
    left: "50%",
    bottom: "9%",
    transform: "translateX(-50%)",
    width: "min(820px, 92vw)",
    textAlign: "center",
    pointerEvents: "none",
  },

  message: {
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
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
};