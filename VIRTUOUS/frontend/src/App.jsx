import { useEffect, useState } from "react";

// ✅ This is the NEW modular entrypoint (the wrapper/layout)
// Adjust the import path to match where you placed it.
import BackgroundEffectsLayout from "./effects/backgroundFloaters/BackgroundEffectsLayout";
import SplitLanding from "./components/SplitLanding";

export default function App() {
  const [msg, setMsg] = useState("Loading...");

  useEffect(() => {
    fetch("http://localhost:5050/ping")
      .then((res) => res.text())
      .then(setMsg)
      .catch((err) => setMsg("Error: " + err.message));
  }, []);

  return (
    <BackgroundEffectsLayout showToggle={true} defaultEnabled={true}>
      <SplitLanding msg={msg} />
    </BackgroundEffectsLayout>
  );
}