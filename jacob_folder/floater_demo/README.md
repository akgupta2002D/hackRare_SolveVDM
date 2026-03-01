# Floater Demo

Fast demo-safe Python project for segmenting eye floater drawings from raw white-canvas PNG exports and assigning one of four shape labels: `dots`, `strands`, `membranes`, or `rings`.

## Setup

```bash
cd floater_demo
python -m pip install -e .
```

## Command

Infer from a local PNG

```bash
python -m floater_demo.cli infer-local --image path/to/canvas.png --outdir artifacts/run_local
```

## Synthetic Data

Generate soft gray synthetic training-style examples with raw images, highlighted overlays, JSON annotations, and a quick inference self-check:

```bash
python -m floater_demo.cli synth --outdir artifacts/synth --n 2000 --seed 42
```

## Notes

- Input must be a raw PNG export with a white background and gray strokes.
- The CLI prints JSON to stdout and saves `overlay.png`, `result.json`, and `expo_result.json` in the output directory.
- `expo_result.json` is the strict mobile contract: only image size, class counts, and absolute/normalized bbox and contour coordinates for direct SVG or canvas rendering.
- Classification is purely shape-based and deterministic.
- Labels are morphological heuristics only. This project makes no medical claims.
