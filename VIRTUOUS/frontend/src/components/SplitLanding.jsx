import React from "react";
import "./splitLanding.css";

export default function SplitLanding({ msg }) {
  return (
    <div className="virtuousPage">
      <div className="virtuousSplit">
        {/* LEFT 65% (opaque panel, blocked from floaters) */}
        <aside className="virtuousLeft noFloatersEffect">
          <div className="virtuousLeftInner">
            <h1 className="virtuousBrand">VIRTUOUS</h1>
            <p className="virtuousMission">
              Our mission is to help VDM teams move faster, stay aligned, and
              build with clarity—through simple tools that feel good to use.
            </p>

            <div className="virtuousSpacer" />

            <div className="virtuousStatus card card--raised">
              <div className="virtuousStatusLabel">Backend says</div>
              <pre className="virtuousPre">{msg}</pre>
            </div>
          </div>
        </aside>

        {/* RIGHT 35% (transparent canvas so floaters show in empty space) */}
        <main className="virtuousRight">
          {/* Top text sits on a token surface (blocked so floaters don't spawn on it) */}
          <div className="virtuousTopCard card noFloatersEffect">
            <div className="virtuousRightTitle">Welcome back</div>
            <div className="virtuousRightSubtitle">
              Choose an action to continue.
            </div>
          </div>

          {/* Middle buttons (blocked) */}
          <div className="virtuousRightCenter">
            <div className="virtuousButtonRow noFloatersEffect" data-interactive="true">
              <button className="virtuousBtn virtuousBtnPrimary">Get started</button>
              <button className="virtuousBtn virtuousBtnSecondary">Learn more</button>
            </div>
          </div>

          {/* Bottom-right button (blocked) */}
          <div className="virtuousRightBottom">
            <button
              className="virtuousBtn virtuousBtnCorner noFloatersEffect"
              data-interactive="true"
            >
              Contact
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}