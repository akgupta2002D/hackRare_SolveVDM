## Overview

This repository is the HackRare project “VIRTUOUS,” an integrative platform for patients and clinicians/researchers around early‑onset idiopathic eye floaters. It includes a web app, a floater physics emulator, an image‑based floater classifier, and Reddit‑scale qualitative analysis pipelines.

---

## Ankit - VIRTUOUS Web App

**Location**: `VIRTUOUS/frontend`, `VIRTUOUS/backend`  
**What it is**: A React + Vite frontend with a small Node/Express backend for education, perception experiments, emulator access, and clinical/analytic views.

- **Frontend (`src/App.jsx`)**: Route shell wiring the main experiences:
  - `/` → `SplitLanding`
  - `/emergency` → `Emergency`
  - `/emulator` → `Emulator`
  - `/floaters` → `FloatersStudio`
  - `/perception` → `FloaterPerception`
  - `/sessions` → `SessionsPage`
  - `/clinical` → `ClinicalDataPage`
  - `/resources` → `VirtuousResourcesPage`
  - `/api_docs` → `FloatersApiDocs`
  - `/exam/floater-heatmap` → `HeatMapExam`
- **Background effects**: `BackgroundEffectsLayout` and related components provide optional animated floater backgrounds.
- **Backend (`backend/server.js`)**:
  - Routes: `/`, `/ping`, `/vdm`, `/debug/env`
  - Cross‑origin support for the Vite dev server, request logging, and simple text responses.

**Design choices**: Thin backend for now, React routing for clear separation of features, and a dedicated layout wrapper to keep background visual effects reusable.

### Extended details

- **Frontend (React + Vite)**
  - `VIRTUOUS/frontend/src/App.jsx`:
    - Imports all main pages (`SplitLanding`, `Emergency`, `Emulator`, `FloatersStudio`, `FloaterPerception`, `SessionsPage`, `ClinicalDataPage`, `VirtuousResourcesPage`, `FloatersApiDocs`, `HeatMapExam`).
    - Wraps all routes in `BackgroundEffectsLayout` so ambient floater visuals can be toggled on/off once for the whole app.
    - On mount, calls `fetch("http://localhost:5050/ping")` and passes the status text (`msg`) into `SplitLanding` so the landing can reflect backend health.
  - Page structure:
    - All pages live under `src/pages`, each with its own CSS (e.g., `floaterPerception.css`, `floatersStudio.css`, `heatmapexam.css`, `clinicaldatapage.module.css`, `resourcepage.css`).
    - Shared design tokens and globals are centralized in `src/styles/tokens.css` and `src/styles/global.css` for consistent typography, color, and spacing.
  - Background floaters:
    - Implemented via `src/effects/backgroundFloaters/BackgroundEffectsLayout.jsx`, `BackgroundFloatersLayer.jsx`, `Interactive.jsx`, and `useBackgroundFloaters.js`.
    - Keeps the effect logic isolated so any page can opt into the same immersive background without duplicating code.

- **Backend (Node + Express)**
  - `VIRTUOUS/backend/server.js`:
    - Loads configuration from `.env` (`PORT`, `CLIENT_ORIGIN`, optional `NODE_ENV`).
    - Adds a lightweight request logger that prints method, URL, status code, and latency for every request.
    - Configures CORS to allow the Vite frontend origin and common HTTP methods.
    - Exposes:
      - `GET /` → `"VIRTUOUS backend is running."`
      - `GET /ping` → `"pong from VIRTUOUS backend"` (used by the frontend health check).
      - `GET /vdm` → `"VIRTUOUS is live for VDM."`
      - `GET /debug/env` → plain‑text dump of `PORT`, `CLIENT_ORIGIN`, and `NODE_ENV` for quick debugging.
    - Ends with explicit 404 and error handlers that always return plain text, making failures easy to see in dev tools and logs.


---

## Azizul and Eric: Floater MVP Physics Prototype

**Location**: `eric_folder/floater_mvp`  
**What it is**: A browser‑based canvas emulator that turns any uploaded floater image into a physics‑driven, gaze‑coupled floater.

- **Key file**: `floater_mvp_app.js` — wires the canvas, lag slider, field‑of‑view controls, and file upload into a single simulation loop that calls `stepPhysics` and `drawFrame`.
- **Key engine**: `floater_mvp_physics.js` — defines `makeFloaterFromImage`, `getLagModel`, and `stepPhysics`, modeling floater motion as a spring‑damped, gaze‑driven system with a tunable “lag” parameter.
- **Design choice**: Physics, scene, and rendering live in separate modules so the same model can be dropped into other UIs (e.g., the `Emulator` React page) without rewriting core math.

### Extended details

- **Canvas‑based floater emulator**
  - `floater_mvp_app.js` initializes the canvas (`cv`), 2D context, sliders, and UI elements (`lag`, `fovShape`, `info`, file input).
  - Maintains simulation `state` with:
    - `view` (offset/zoom), `rawViewVel`, `viewVel`, `prevViewVel`, `stationaryTime`.
    - `floaters` (array of floater objects), `loadedImage` (source sprite), and `sceneObjects` from `initSceneObjects()`.
  - Handles:
    - Resize (`resizeCanvasToDevicePixels`) with device‑pixel‑ratio awareness.
    - Mouse drag for panning and injecting gaze velocity.
    - File upload → `handleImageUpload` → `rebuildFloater` to create a floater from an image.
    - `animationLoop` that calls `stepPhysics(state, lagPercent, dt, nowSec)` and `drawFrame(...)` every frame.

- **Physics engine details**
  - `floater_mvp_physics.js` exports:
    - `PHYSICS_CONSTANTS` (e.g., `BASE_PARALLAX`, `GAZE_COUPLING`).
    - `makeFloaterFromImage(img, rng)` to build floater objects with depth, parallax, lag/return scales, and micro‑motion parameters.
    - `getLagModel(lagPercent)` to map the 0–100 lag slider into spring/damping/return parameters and input model settings.
    - `stepPhysics(state, lagPercent, dt, nowSec)` to:
      - Smooth pointer‑derived view velocity and compute view acceleration.
      - Ramp in a “return to baseline” force when gaze is stationary.
      - Apply a dead‑zoned, gaze‑coupled drive to each floater, plus micro‑motion sinusoids.
  - Uses semi‑implicit Euler integration and clearly documented equations at the top of the file so domain experts can audit and tune the model.

---


## Jacob: Floater Demo (Rule‑Based Image Inference)

**Location**: `jacob_folder/floater_demo`  
**What it is**: A rule‑based floater image classifier that segments each floater, computes features, and assigns an interpretable label with an explanation.

- **Key file**: `floater_demo/infer.py` — `infer_image(...)` runs preprocess → segmentation → feature extraction → rule‑based classification and returns both a detailed JSON result and a compact `build_expo_payload(...)` for viewers.
- **Key helpers**: `floater_demo/utils.py` — utilities like `mask_to_bbox`, `mask_to_contour`, and `normalize_*` that convert masks into normalized geometry for downstream UIs.
- **Artifacts**: `artifacts/` holds synthetic and curated examples plus Supabase listener outputs; `tests/test_rules.py` locks in rule behavior with regression tests.

### Extended details

- **End‑to‑end inference pipeline**
  - `infer_image(png_path, config, save_debug_masks=False, debug_instance_dir=None)`:
    1. Preprocesses the input image via `preprocess_image(png_path, config.preprocess)`.
    2. Segments floater instances with `segment_instances(pre.binary_mask, config.segment)`.
    3. For each component:
       - Computes features using `compute_features(pre.grayscale, component, ...)`.
       - Classifies via `classify_instance(features, config.rules)` (rule‑based classifier with label, confidence, explanation).
       - Builds per‑instance metadata:
         - Raw and normalized bounding box (`bbox`, `bbox_normalized`).
         - Raw and normalized contour (`contour`, `contour_normalized`).
         - Area, serialized features, label, confidence, explanation, and optional mask.
    4. Assembles a top‑level result with:
       - `image` (path, width, height).
       - `summary` (instance count and label counts).
       - `expo` payload for lightweight viewers.
       - Full `instances` list and optional `debug`/`_render` fields.
  - `build_expo_payload(result)` trims the full result down to a compact schema for frontends.

- **Utility and artifact structure**
  - `floater_demo/utils.py` provides:
    - `ensure_dir`, `stable_color`, `mask_to_bbox`, `mask_to_contour`, `normalize_bbox`, `normalize_contour`, `stem_id`, `json_dumps`, `is_png`.
    - Normalization is rounded to fixed precision and guarded against zero width/height.
  - `artifacts/` contains:
    - `synth/` synthetic cases.
    - `closed_loop_eval_demo/` curated examples (`true_dot_clean`, `thick_strand_long`, `membrane_cloud_faint`, `small_ring_clean`).
    - `supabase_listener/` serialized payloads used in external demos.
  - `tests/test_rules.py` provides regression coverage for the rule set so label behavior stays stable over time.

---



## How These Pieces Fit Together (and Why They Matter)

- **Ankit – VIRTUOUS Web App (frontend + backend)**  
  - **Role in the system**: This is the single entry point patients, clinicians, and researchers actually touch. It stitches together all the other work into one coherent experience: landing, education, emulator, perception experiments, and future data/clinic views.  
  - **Why it matters**: Without this layer, the project would just be disconnected prototypes and scripts. VIRTUOUS turns them into a product that can onboard users, surface safety messaging (Emergency page), host experiments, and eventually accept real‑world exam data and sessions.

- **Azizul & Eric – Floater MVP Physics Prototype**  
  - **Role in the system**: Provides the physically‑motivated motion engine behind the “MVP Emulator” experience. It shows what patients actually see when floaters drift, lag, and catch up with gaze.  
  - **Why it matters**: The physics model makes the emulator feel legitimate to both patients and clinicians—grounded in a tunable, audited model instead of arbitrary animation. It is the core of how sufferers can *show* their visual disturbance, not just describe it in words.

- **Jacob – Floater Demo (Rule‑Based Image Inference)**  
  - **Role in the system**: Takes real floater images and turns them into structured instances (dots, strands, membranes, rings) with interpretable labels and explanations. This can back future “upload my floater photo” flows.  
  - **Why it matters**: It anchors the project in image‑level understanding, not just subjective reports. Clinicians and researchers can see consistent, rule‑based categorization that could eventually tie emulator presets and educational content to actual image findings.

- **Reddit scrapping pipelines (Eric & Jacob)**  
  - **Role in the system**: Mine large‑scale patient narratives from Reddit and convert them into structured themes, statistics, and quotebooks. These outputs can drive resource pages, risk language, and clinician guidance inside VIRTUOUS.  
  - **Why it matters**: This gives the project a real‑world voice: how people describe floaters, what scares them, what doctors say, and where care breaks down. It keeps the product grounded in lived experience and lets future analytics modules show population‑level patterns, not just one‑off anecdotes.

Together, these pieces form a loop: **Reddit pipelines** surface real concerns and language → inform **VIRTUOUS content and experiments** → **physics MVP** makes those experiences visually honest → **image inference** connects what patients see on scans or photos to how we render and talk about floaters.

