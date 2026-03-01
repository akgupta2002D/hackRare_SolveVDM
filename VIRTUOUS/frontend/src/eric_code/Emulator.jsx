import React from "react";
import { useNavigate } from "react-router-dom";
import "./emulator.css";
import emulatorQrCode from "./emulator_qr_code.svg";

const Emulator = () => {
  const navigate = useNavigate();

  return (
    <div className="emulatorPage">
      <button
        className="virtuousBtn emulatorBackBtn"
        onClick={() => navigate("/")}
      >
        Back
      </button>
      <div className="emulatorSplit">
        <section className="emulatorLeft card">
          <div className="emulatorLeftInner">
            <h1 className="emulatorTitle">Perception Emulator</h1>
            <p className="emulatorSubtitle">
              Scan this code on your phone to connect to the emulator workflow.
            </p>

            <div className="emulatorInfoBlock card card--raised">
              <h2 className="emulatorInfoTitle">How to start</h2>
              <ol className="emulatorInfoList">
                <li>
                  Download <strong>Expo Go</strong> on your phone (iOS or
                  Android).
                </li>
                <li>Scan the QR code on this page.</li>
                <li>
                  Follow the in-app prompts to begin your floater capture
                  session.
                </li>
              </ol>
            </div>

            <div className="emulatorInfoBlock card card--raised">
              <h2 className="emulatorInfoTitle">What this emulator does</h2>
              <p className="emulatorInfoText">
                The emulator lets users draw what their floaters look like and
                overlay those floaters on the phone camera feed. Floater motion
                is simulated to approximate vitreous behavior, including lag and
                snap-back effects in vision.
              </p>
              <p className="emulatorInfoText">
                Session images are saved so clinicians can request and review
                patient-specific floater appearances, while also building a
                public source of representative floater images for broader
                research and reference.
              </p>
            </div>
          </div>
        </section>

        <section className="emulatorRight">
          <div className="emulatorQrCard card card--raised">
            <div className="emulatorQrHeader">Mobile Pairing QR</div>
            <img
              className="emulatorQr"
              src={emulatorQrCode}
              alt="Emulator QR code"
            />
            <div className="emulatorQrHint">Point your phone camera here</div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Emulator;
