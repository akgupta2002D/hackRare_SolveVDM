import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";

import BackgroundEffectsLayout from "./effects/backgroundFloaters/BackgroundEffectsLayout";
import SplitLanding from "./components/SplitLanding";
import FloaterStudio from "./pages/FloatersStudio";
import FloaterPerception from "./pages/FloaterPerception";
import HeatmapExam from "./pages/HeatMapExam";
import Emulator from "./eric_code/Emulator";
import Emergency from "./pages/Emergency";
import SessionsPage from "./pages/Sessionpage";
import ClinicalDataPage from "./pages/ClinicalDataPage";
import VirtuousResourcesPage from "./pages/VirtuousResourcesPage";
import FloatersApiDocs from "./pages/FloatersApiDocs";

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
      <Routes>
        <Route path="/" element={<SplitLanding msg={msg} />} />
        <Route path="/emergency" element={<Emergency />} />
        <Route path="/emulator" element={<Emulator />} />
        <Route path="/floaters" element={<FloaterStudio />} />
        <Route path="/perception" element={<FloaterPerception />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/clinical" element={<ClinicalDataPage />} />
        <Route path="/resources" element={<VirtuousResourcesPage />} />
        <Route path="/api_docs" element={<FloatersApiDocs />} />
        <Route
          path="/exam/floater-heatmap"
          element={
            <HeatmapExam
              onComplete={(payload) => {
                // Send to backend later if you want.
                // For now, this logs + alerts.
                console.log("Exam complete payload:", payload);
              }}
            />
          }
        />
      </Routes>
    </BackgroundEffectsLayout>
  );
}