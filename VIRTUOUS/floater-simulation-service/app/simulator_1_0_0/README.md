# simulator_1_0_0 (MVP) — short docs

This folder holds the MVP “forward model” building blocks.
It turns:

`disturbance + optical_context -> percept_output`

## What each module contains

- `disturbance.py`: data model for the numerical disturbance input
  - `depthZ`, `size`, `opacity`
- `optical_context.py`: data model for eye/environment conditions
  - `ambientBrightness`, `pupilSize`
- `percept_output.py`: data model for the model outputs (no computation)
  - `apparentSize`, `apparentBlur`, `apparentDarkness`
- `constraints.py`: input validation / bounds checking
  - ensures inputs are inside allowed MVP ranges before math runs
- `core_model.py`: the only place that does forward-model math
  - `compute_forward_model(disturbance, optical_context) -> PerceptOutput`

## Data flow (how information moves)

1. **Inputs arrive** (from API layer / request body)
2. **Build objects**
   - create a `Disturbance(depthZ, size, opacity)` (from `disturbance.py`)
   - create an `OpticalContext(ambientBrightness, pupilSize)` (from `optical_context.py`)
3. **Validate**
   - `constraints.validate_inputs(disturbance, optical_context)`
4. **Compute (forward model math)**
   - `core_model.compute_forward_model(disturbance, optical_context)`
5. **Return outputs**
   - a `PerceptOutput(apparentSize, apparentBlur, apparentDarkness)` (from `percept_output.py`)

## Notes (MVP behavior)

- The math is intentionally simple for MVP.
- `optical_context` is accepted by the core model so we can expand the relationships later (without changing the public function signature).

## Experiments & visualization

- **`experiments/depth_sweep_test.py`** — sweeps 5 `depthZ` values with fixed `size` / `opacity` / context; runs `compute_forward_model`, prints a table, and asserts monotonic trends (far → near).
- **`experiments/visualization/visualization.py`** — Matplotlib **1×5** figure: one panel per depth; maps `apparentSize` → circle size, `apparentBlur` → edge softness, `apparentDarkness` → intensity. Run from `floater-simulation-service`:  
  `.venv/bin/python app/simulator_1_0_0/experiments/visualization/visualization.py --save path/to/out.png`
- **`experiments/visualization/depth_sweep.png`** — example output from that script.

Deps for visualization live in the service root **`requirements.txt`** (`matplotlib`, `numpy`). Matplotlib cache dirs (e.g. `.mpl_cache`) are ignored at repo root via `.gitignore`.
