import { useEffect, useState } from "react";

// ✅ This is the NEW modular entrypoint (the wrapper/layout)
// Adjust the import path to match where you placed it.
import BackgroundEffectsLayout from "./effects/backgroundFloaters/BackgroundEffectsLayout";

export default function App() {
  const [msg, setMsg] = useState("Loading...");

  useEffect(() => {
    fetch("http://localhost:5050/ping")
      .then((res) => res.text())
      .then(setMsg)
      .catch((err) => setMsg("Error: " + err.message));
  }, []);

  return (
    <BackgroundEffectsLayout>
      <div style={{ minHeight: "100vh", padding: 40 }}>

        {/* Only block specific UI regions */}
        <div className="noFloatersEffect">
          <h1>VIRTUOUS</h1>
          <p>Platform for VDM</p>
        </div>

        <div style={{ height: 200 }} />
        {/* This empty area will allow floaters */}

        <div className="noFloatersEffect">
          <h2>Backend says:</h2>
          <pre style={{ background: "#111", color: "#eee", padding: 16 }}>
            {msg}
          </pre>
        </div>

      </div>
    </BackgroundEffectsLayout>
  );
}