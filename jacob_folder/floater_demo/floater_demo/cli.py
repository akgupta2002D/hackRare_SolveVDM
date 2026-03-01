from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from .closed_loop import run_closed_loop
from .config import load_config
from .infer import build_expo_payload, infer_image
from .supabase_worker import SupabaseWorker, load_supabase_config
from .synth import generate_synth_dataset
from .utils import ensure_dir
from .visualize import save_debug_masks, save_overlay


app = typer.Typer(help="Local PNG inference CLI for 4-class floater shape classification.")
console = Console()


@app.command("infer-local")
def infer_local(
    image: Path = typer.Option(..., exists=True, dir_okay=False, help="Local PNG image."),
    outdir: Path = typer.Option(..., help="Output directory."),
    debug_masks: bool = typer.Option(False, help="Save binary and per-instance masks."),
) -> None:
    config = load_config()
    result = infer_image(image, config, save_debug_masks=True)
    _finalize_and_print(result, outdir, debug_masks)


@app.command("synth")
def synth(
    outdir: Path = typer.Option(..., help="Output directory for generated images and annotations."),
    n: int = typer.Option(2000, min=1, help="Number of synthetic images to generate."),
    seed: int = typer.Option(42, help="Random seed for deterministic generation."),
) -> None:
    payload = generate_synth_dataset(outdir=outdir, n=n, seed=seed, config=load_config())
    console.print_json(data=payload)


@app.command("listen-supabase")
def listen_supabase(
    once: bool = typer.Option(False, help="Process pending rows once and exit."),
    write_mode: str = typer.Option(
        "incremental",
        help="Use 'incremental' to process only unanalyzed rows or 'overwrite_all' to reprocess every row.",
    ),
    wipe_output_bucket: bool = typer.Option(
        False,
        help="Only with overwrite_all: delete every file in the analysis output bucket before processing.",
    ),
    artifacts_dir: Path = typer.Option(
        Path("artifacts/supabase_listener"),
        help="Local directory for downloaded and generated artifacts.",
    ),
    env_file: Path | None = typer.Option(
        None,
        exists=True,
        dir_okay=False,
        help="Optional .env file with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
    ),
) -> None:
    if write_mode not in {"incremental", "overwrite_all"}:
        raise typer.BadParameter("write_mode must be 'incremental' or 'overwrite_all'")
    if wipe_output_bucket and write_mode != "overwrite_all":
        raise typer.BadParameter("--wipe-output-bucket only applies with --write-mode overwrite_all")

    config = load_supabase_config(env_file)
    config = config.__class__(
        **{
            **config.__dict__,
            "write_mode": write_mode,
            "wipe_output_bucket_on_start": wipe_output_bucket,
        }
    )
    worker = SupabaseWorker(config, artifacts_dir=artifacts_dir)
    if once:
        processed = worker.run_once()
        console.print(f"processed_rows={processed}")
        return
    worker.run_forever()


@app.command("closed-loop")
def closed_loop_command(
    outdir: Path = typer.Option(..., help="Directory for closed-loop artifacts."),
    rounds: int = typer.Option(5, min=1, help="Maximum closed-loop rounds."),
    seed: int = typer.Option(42, help="Base seed for deterministic generation."),
    n: int = typer.Option(50, min=1, help="Samples per suite per round."),
    apply_updates: bool = typer.Option(False, help="Apply bounded config updates between rounds."),
) -> None:
    payload = run_closed_loop(outdir=outdir, rounds=rounds, seed=seed, n_per_suite=n, apply_updates=apply_updates)
    console.print_json(data=payload)


def _finalize_and_print(result: dict[str, object], outdir: Path, debug_masks: bool) -> None:
    outdir_path = ensure_dir(outdir)
    overlay_path = save_overlay(result, outdir_path)
    result_path = outdir_path / "result.json"
    expo_result_path = outdir_path / "expo_result.json"
    expo_payload = build_expo_payload(result)

    if debug_masks:
        save_debug_masks(result, outdir_path)

    serializable = {
        "image": result["image"],
        "summary": result["summary"],
        "expo": result["expo"],
        "instances": [_instance_payload(instance) for instance in result["instances"]],
        "artifacts": {
            "overlay": overlay_path.name,
            "result": result_path.name,
            "expo_result": expo_result_path.name,
        },
    }
    with result_path.open("w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2)
    with expo_result_path.open("w", encoding="utf-8") as handle:
        json.dump(expo_payload, handle, indent=2)
    console.print_json(data=serializable)


def _instance_payload(instance: dict[str, object]) -> dict[str, object]:
    return {
        "id": instance["id"],
        "bbox": instance["bbox"],
        "bbox_normalized": instance["bbox_normalized"],
        "contour": instance["contour"],
        "contour_normalized": instance["contour_normalized"],
        "area": instance["area"],
        "features": instance["features"],
        "label": instance["label"],
        "confidence": instance["confidence"],
        "explanation": instance["explanation"],
    }


if __name__ == "__main__":
    app()
