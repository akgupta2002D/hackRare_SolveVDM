from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from floater_demo.config import load_config
from floater_demo.infer import infer_image


def test_smoke(tmp_path: Path) -> None:
    image = np.full((320, 320, 3), 255, dtype=np.uint8)
    cv2.circle(image, (60, 70), 16, (110, 110, 110), -1)
    cv2.line(image, (120, 220), (260, 220), (80, 80, 80), 6)
    cv2.circle(image, (240, 90), 24, (95, 95, 95), 5)
    cv2.ellipse(image, (170, 140), (46, 20), 15, 0, 360, (125, 125, 125), -1)

    png_path = tmp_path / "synthetic.png"
    cv2.imwrite(str(png_path), image)

    result = infer_image(png_path, load_config(), save_debug_masks=True)

    assert result["summary"]["instance_count"] >= 4
    labels = {instance["label"] for instance in result["instances"]}
    assert "dots" in labels
    assert "strands" in labels
    assert "rings" in labels
    assert "membranes" in labels
