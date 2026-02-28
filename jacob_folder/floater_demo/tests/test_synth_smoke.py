from __future__ import annotations

import json
from pathlib import Path

from floater_demo.config import load_config
from floater_demo.infer import infer_image
from floater_demo.synth import generate_synth_dataset


def test_synth_smoke(tmp_path: Path) -> None:
    outdir = tmp_path / "synth"
    payload = generate_synth_dataset(outdir=outdir, n=20, seed=42, config=load_config())

    assert payload["images"] == 20

    raw_files = sorted(outdir.glob("*.png"))
    json_files = sorted(outdir.glob("*.json"))
    overlay_files = sorted(outdir.glob("*_overlay.png"))

    assert len(json_files) == 20
    assert len(overlay_files) == 20
    assert len(raw_files) == 40

    for json_path in json_files:
        image_id = json_path.stem
        raw_path = outdir / f"{image_id}.png"
        overlay_path = outdir / f"{image_id}_overlay.png"

        assert raw_path.exists()
        assert overlay_path.exists()

        with json_path.open("r", encoding="utf-8") as handle:
            annotation = json.load(handle)
        assert len(annotation["instances"]) >= 1

    for json_path in json_files[:5]:
        image_id = json_path.stem
        result = infer_image(outdir / f"{image_id}.png", load_config(), save_debug_masks=False)
        assert result["summary"]["instance_count"] >= 1
