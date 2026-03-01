import React from "react";

/**
 * Interactive
 * -----------
 * Wrap any custom clickable div/card/menu item so the background
 * effects DON'T spawn when the cursor is over it.
 *
 * Example:
 *  <Interactive className="card" onClick={...}>
 *    ...
 *  </Interactive>
 */
export default function Interactive({ as: Comp = "div", children, ...props }) {
  return (
    <Comp data-interactive="true" {...props}>
      {children}
    </Comp>
  );
}