export const layerStyles = {
  container: {
    position: "fixed",
    inset: 0,
    zIndex: 0,
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
    right: "3%",                 // occupy right side
    bottom: "10%",             // 5% from bottom
    width: "35vw",            // right 35% of screen
    display: "flex",
    justifyContent: "center", // keep message centered in its zone
    pointerEvents: "none",
  },

  message: {
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    fontSize: "clamp(14px, 1.4vw, 18px)", // smaller font
    fontWeight: 600,
    letterSpacing: "-0.01em",
    color: "rgba(255,255,255,0.95)",
    textShadow: "0 6px 18px rgba(0,0,0,0.55)",
    padding: "8px 12px",
    borderRadius: 14,
    backdropFilter: "blur(6px)",
    background: "rgba(0,0,0,0.22)",
    display: "inline-block",
  },
};