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

Generate synthetic data

```bash
python -m floater_demo.cli synth --outdir artifacts/synth --n 20 --seed 42
```

Run the balanced benchmark

```bash
python -m floater_demo.closed_loop --outdir artifacts/closed_loop_eval --rounds 1 --seed 42 --n 100
```

This writes:
- `report.json`
- `confusion.csv`
- `confusion_row_normalized.csv`
- `confusion_matrix.json`
- `confusion_matrix.png`
- `presentation_metrics.json`
- `stress_metrics.json`

The benchmark is balanced by design:
- equal synthetic support for `dots`, `strands`, `membranes`, and `rings`
- one harder reference suite per class
- `confusion_matrix.png` is row-normalized for presentation, so each ground-truth row sums to 100%
- `stress_metrics.json` reports extra overlap-sensitive checks outside the main matrix

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

## Supabase Listener

You can run a local worker that polls Supabase, renders the `paths` payload to a PNG if needed, runs inference, uploads derived analysis artifacts to storage, and writes the segmentation back to the row.

Expected env vars in `.env`:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-secret-service-role-key
SUPABASE_INPUT_TABLE=drawings
SUPABASE_OUTPUT_BUCKET=analyses
```

Incremental mode:
- default and safest mode
- only processes rows where `analysed_at` is null
- use this when testing is done

```bash
python -m floater_demo.cli listen-supabase --once --write-mode incremental
```

Overwrite-all mode:
- reprocesses every row in the source table
- overwrites analysis columns for the same `id`
- storage uploads reuse deterministic paths and `x-upsert=true`, so derived files are overwritten in place

```bash
python -m floater_demo.cli listen-supabase --once --write-mode overwrite_all
```

Full test reset mode:
- only for testing
- deletes all files in the configured analysis output bucket before reprocessing every row
- leaves the source rows and raw drawing data alone

```bash
python -m floater_demo.cli listen-supabase --once --write-mode overwrite_all --wipe-output-bucket
```

Run continuously in incremental mode:

```bash
python -m floater_demo.cli listen-supabase
```

By default the worker tries to update these columns on the source row:

- `analysis_json`
- `segmentation_json`
- `floater_types`
- `floater_type_counts`
- `analysis_artifacts`
- `analysed_at`

If those columns do not exist yet, it falls back to updating only `analysed_at`.
