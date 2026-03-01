import React, { useMemo, useState } from "react";
import BackgroundFloatersLayer from "./BackgroundFloatersLayer";

/**
 * BackgroundEffectsLayout
 * -----------------------
 * This component is meant to wrap your entire app ONE TIME.
 *
 * It:
 *  1) mounts the background floaters layer behind everything
 *  2) provides a consistent "UI layer" above it (zIndex: 1)
 *  3) includes an optional toggle button you can move or remove
 *
 * Usage:
 *  <BackgroundEffectsLayout>
 *    <YourApp />
 *  </BackgroundEffectsLayout>
 */
export default function BackgroundEffectsLayout({
  children,
  showToggle = true,
  defaultEnabled = true,
}) {
  const [enabled, setEnabled] = useState(defaultEnabled);

  // Patient-focused messages, stored locally for now.
  // You can swap this out later with a fetch call if needed.
  const messages = useMemo(
    () => [
      "You’re not alone in this—support is here.",
      "One step at a time. You’re doing your best.",
      "It’s okay to rest. Healing isn’t linear.",
      "You deserve care that listens to you.",
      "Breathe. You’ve made it through hard days before.",
      "Your feelings are real—and they matter.",
      "You are more than your symptoms.",
      "You’re not alone in this—support is here.",
      "One step at a time. You’re doing your best.",
      "It’s okay to rest. Healing isn’t linear.",
      "You deserve care that listens to you.",
      "Breathe. You’ve made it through hard days before.",
      "Your feelings are real—and they matter.",
      "You are more than your symptoms.",
      "You’re not alone in this—support is here.",
      "One step at a time. You’re doing your best.",
      "It’s okay to rest. Healing isn’t linear.",
      "You deserve care that listens to you.",
      "Breathe. You’ve made it through hard days before.",
      "Your feelings are real—and they matter.",
      "You are more than your symptoms.",
      "You’re not alone in this—support is here.",
      "One step at a time. You’re doing your best.",
      "It’s okay to rest. Healing isn’t linear.",
      "You deserve care that listens to you.",
      "Breathe. You’ve made it through hard days before.",
      "Your feelings are real—and they matter.",
      "You are more than your symptoms.",
      "You’re not alone in this—support is here.",
      "One step at a time. You’re doing your best.",
      "It’s okay to rest. Healing isn’t linear.",
      "You deserve care that listens to you.",
      "Breathe. You’ve made it through hard days before.",
      "Your feelings are real—and they matter.",
      "You are more than your symptoms.",
    ],
    []
  );

  return (
    <div style={layoutStyles.page}>
      {/* 1) Background visual layer (behind everything) */}
      <BackgroundFloatersLayer enabled={enabled} messages={messages} revealThreshold={40} messageDurationMs={1500} />

      {/* 2) Foreground UI layer */}
      <div style={layoutStyles.uiLayer}>
        {showToggle && (
          <div style={layoutStyles.toggleWrap} data-interactive="true">
            {/* data-interactive ensures hover over toggle never spawns floaters */}
            <button style={layoutStyles.toggleBtn} onClick={() => setEnabled((v) => !v)}>
              {enabled ? "Disable background effect" : "Enable background effect"}
            </button>
          </div>
        )}

        {/* Your app lives here, above the floaters */}
        {children}
      </div>
    </div>
  );
}

const layoutStyles = {
  page: {
    position: "relative",
    minHeight: "100vh",
  },

  // Everything inside this div is above the floaters
  uiLayer: {
    position: "relative",
    zIndex: 1,
    minHeight: "100vh",
  },

  toggleWrap: {
    position: "fixed",
    bottom: 16,
    right: 16,
    zIndex: 2,
  },

  toggleBtn: {
    padding: "10px 14px",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.2)",
    background: "rgba(0,0,0,0.35)",
    color: "white",
    cursor: "pointer",
  },
};