# How each major feature was built

Short notes (two to three lines each) on implementation—not user-facing marketing copy. Paths are from the repo root.

---

### VIRTUOUS web app (React + Express)

The **frontend** is a Vite + React app: `App.jsx` wires routes (landing, emergency, emulator, floaters studio, perception, clinical views, API docs, etc.) and wraps pages in a shared background-effects layout. **Styling** is split per page under `VIRTUOUS/frontend/src/pages` with shared tokens in `src/styles/`.

The **backend** is a thin Express server (`VIRTUOUS/backend/server.js`): CORS for the dev origin, logging, and a few health routes (`/ping`, `/vdm`, `/debug/env`). It is intentionally small so most logic stays in the browser or in dedicated Python services.

---

### “Perception Emulator” page (in the web app)

`VIRTUOUS/frontend/src/eric_code/Emulator.jsx` is a **landing + instructions** surface: it explains Expo Go, shows a **QR** (`final_emulator_qr_code.svg`) for pairing a phone, and describes draw-on-camera floater behavior in text. The **heavy simulation** for the in-browser MVP lives separately in `eric_folder/floater_mvp` (see below); this page is the VIRTUOUS entry point for the mobile workflow.

---

### Canvas physics emulator (MVP floater motion)

**Location:** `eric_folder/floater_mvp`. **`floater_mvp_physics.js`** implements the model: building floaters from an uploaded image, mapping a lag slider to spring/damping parameters, and **`stepPhysics`** (semi-implicit Euler, gaze-coupled drift, micro-motion). **`floater_mvp_app.js`** owns the canvas loop, resize/DPR handling, pointer-driven “gaze” velocity, and **`drawFrame`**.

Design: **physics, scene, and drawing are separate modules** so the same core can be reused (e.g. ideas carried into React pages) without duplicating the math.

---

### Floater simulation service (FastAPI) + forward model MVP

**HTTP API:** `VIRTUOUS/floater-simulation-service` — FastAPI app with Pydantic schemas, routes under `/api/v1/simulation/run`, and **`app/simulation.py`** implementing **`run_simulation_step`** (today a small **placeholder** that derives a fake floater count from intensity). **`app/simulator_1_0_0/`** is the separate **forward model**: typed inputs (`Disturbance`, `OpticalContext`), **`constraints.validate_inputs`**, and **`core_model.compute_forward_model`** mapping disturbance + lighting/pupil context to percept outputs (`apparentSize`, `apparentBlur`, `apparentDarkness`).

The service is structured so **HTTP stays in routes** and **math stays in `simulator_1_0_0`**, with experiments/scripts for sweeps and matplotlib visualization under that package.

---

### Rule-based floater image classifier (“floater demo”)

**Location:** `jacob_folder/floater_demo`. Pipeline: **`infer.py`** → **`infer_image`**: preprocess PNG → **segment** connected components → **per-instance features** (geometry, holes, elongation, etc.) → **`classify_instance`** in **`rules.py`** (threshold rules for rings, membranes, strands, dots, with confidence and a text **explanation**). Outputs are JSON-friendly dicts plus **`build_expo_payload`** for slim clients.

**`utils.py`** normalizes bboxes/contours for UIs; **`tests/test_rules.py`** regression-tests the rule layer. No deep-learning training loop—labels come from **interpretable rules** on engineered features.

---

### Reddit collection + semantic analysis pipelines

**Locations:** `eric_folder/reddit_scrapping` and **`jacob_folder/reddit_scrapping`** (parallel copies). **Collect** scripts pull threads/comments; **pipeline** runs **`analyze_text`** (VADER sentiment, regex/heuristic extractions for severity, lifestyle tags, medical flags, quote scoring) and **`build_themes`** (**TfidfVectorizer** + **KMeans** on post text). Results land in **processed CSVs**, **reports**, and **summary JSON**.

Jacob’s copy is what **`ankitgupta/semantic_analysis_viz`** reads by default (`post_analysis.csv`, `comment_analysis.csv`). See root **`SEMANTIC_ANALYSIS.md`** for deeper detail.

---

### Semantic analysis visualizations (charts + word cloud)

**Location:** `ankitgupta/semantic_analysis_viz`. **`grouped_trends_graph.py`** loads Jacob’s CSVs, merges post + comment counts, applies **regex buckets** (mental health, dismissal/clinical mismatch, floater-topic control) and **lifestyle_impacts** QoL tags, then **matplotlib** bar charts (minimal chrome as requested). **`floater_word_cloud.py`** filters text with the same floater-topic pattern, uses **`wordcloud`** plus a small **`VariableWeightWordCloud`** subclass (multiple font files + grayscale **`color_func`**) and writes **`floaters_wordcloud.png`**.

**`SEMANTIC_ANALYSIS_PROCESS.md`** holds the combined Mermaid overview of pipeline + viz.

---

### Other references

- **Single source of truth (simulator concept):** `VIRTUOUS/floater-simulation-service/single_source_of_truth.md`  
- **API contract for the Python service:** `VIRTUOUS/floater-simulation-service/API.md`  
- **Simulator package README:** `VIRTUOUS/floater-simulation-service/app/simulator_1_0_0/README.md`  
- **Narrative overview of how pieces connect:** root **`README.md`** (“How These Pieces Fit Together”).
