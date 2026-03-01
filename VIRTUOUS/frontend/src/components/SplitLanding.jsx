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

            {/* NEW: 3-word statement */}
            <div className="virtuousStatementRow" aria-label="Virtuous values">
              <div className="virtuousStatement virtuousStatementNavy">Acknowledge</div>
              <div className="virtuousStatement virtuousStatementRed">Believe</div>
              <div className="virtuousStatement virtuousStatementGreen">Community</div>
            </div>

            <div className="virtuousSpacer" />

            {/* <div className="virtuousStatus card card--raised">
              <div className="virtuousStatusLabel">Backend says</div>
              <pre className="virtuousPre">{msg}</pre>
            </div> */}
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
              <button className="blue_border virtuousBtn   " onClick={() => navigate("/emulator")}>Patient: Emulator</button>
              <p className="virtuousToolDescription">An interactive emulator that lets you draw and simulate your eye floaters—bringing to life what standard scans often fail to capture.
Track, visualize, and share your experience in real time, turning something invisible and isolating into something seen, understood, and validated.</p>
              <button className="red_border virtuousBtn   " onClick={() => navigate("/clinical")}>Clinicians: Info and Data</button>
              <p className="virtuousToolDescription">A clinician-and-researcher platform that converts patient drawings into standardized, classified datasets—building a growing database of floater patterns over time.
By pairing user-reported visuals with optical modeling, we aim to turn subjective symptoms into shareable data for clinical insight and future research.</p>
              {/* <button className="virtuousBtn " onClick={() => navigate("/floaters")}>
                HeatMap
            </button> */}

            </div>

          </div>
        </main>
      </div>
    </div>
  );
}