import { useEffect, useState } from "react";

export default function App() {
  const [msg, setMsg] = useState("Loading...");

  useEffect(() => {
    fetch("http://localhost:5050/ping")
      .then((res) => res.text())
      .then(setMsg)
      .catch((err) => setMsg("Error: " + err.message));
  }, []);

  return (
    <div style={{ fontFamily: "system-ui", padding: 24 }}>
      <h1>VIRTUOUS</h1>
      <p>Platform for VDM</p>

      <h2>Backend says:</h2>
      <pre style={{ background: "#111", color: "#eee", padding: 16, borderRadius: 12 }}>
        {msg}
      </pre>
    </div>
  );
}