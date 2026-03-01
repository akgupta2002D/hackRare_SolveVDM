from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from .config import load_config
from .infer import build_expo_payload, infer_image
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
