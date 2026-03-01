import React from "react";
import "./splitLanding.css";
import VirtuousLeftNav from "./VirtuousLeftNav";
import { useNavigate } from "react-router-dom";

export default function SplitLanding({ msg }) {

  const navigate = useNavigate();

  return (
    <div className="virtuousPage">
      <div className="virtuousSplit">
        <aside className="virtuousLeft noFloatersEffect">
          <VirtuousLeftNav />

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

        <main className="virtuousRight">
          <div className="virtuousTopCard cardTitle noFloatersEffect">
            <div className="virtuousRightTitle">Our Tools</div>
            <div className="virtuousRightSubtitle">
              Towards a more accepting and validating clinical and patient stories.
            </div>
          </div>

          <div className="virtuousRightCenter">
            <div className="virtuousButtonRow noFloatersEffect" data-interactive="true">
              <button className="virtuousBtn virtuousBtnPrimary" onClick={() => navigate("/emulator")}>Patient: Emulator</button>
              <button className="virtuousBtn virtuousBtnSecondary">Clinicians: Info and Data</button>
              <button className="virtuousBtn virtuousBtnPrimary" onClick={() => navigate("/floaters")}>
                HeatMap
            </button>

            </div>
          </div>

          <div className="virtuousRightBottom">
            <button className="virtuousBtn virtuousBtnCorner noFloatersEffect" data-interactive="true">
              Contact
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}