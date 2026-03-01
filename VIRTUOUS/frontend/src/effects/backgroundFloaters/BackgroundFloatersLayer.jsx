import React from "react";
import { layerStyles } from "./styles";
import useBackgroundFloaters from "./useBackgroundFloaters";

/**
 * BackgroundFloatersLayer
 * -----------------------
 * Pure view component: it renders floaters + a message.
 *
 * All logic (mouse tracking, spawning, animation) lives in the hook.
 */
export default function BackgroundFloatersLayer({
  enabled,
  messages,
  revealThreshold = 160,
  messageDurationMs = 3000, // per your ask
}) {
  // ✅ hook returns typedMessage (not "message")
  const { containerRef, floaters, messageVisible, typedMessage } =
    useBackgroundFloaters({
      enabled,
      messages,
      revealThreshold,
      messageDurationMs,
    });

  return (
    <div ref={containerRef} style={layerStyles.container} aria-hidden="true">
      {/* Floaters */}
      {floaters.map((f) => (
        <span
          key={f.id}
          style={{
            ...layerStyles.floater,
            width: f.size,
            height: f.size,
            transform: `translate(${f.x}px, ${f.y}px) rotate(${f.rot}deg)`,
            opacity: f.opacity,
          }}
        />
      ))}

      {/* ✅ Typed message shows only when triggered */}
      {messageVisible && (
        <div style={layerStyles.messageWrap}>
          <div style={layerStyles.message}>{typedMessage}</div>
        </div>
      )}
    </div>
  );
}