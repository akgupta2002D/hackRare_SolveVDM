from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .utils import ensure_dir, stable_color


def save_overlay(result: dict[str, object], outdir: str | Path) -> Path:
    outdir_path = ensure_dir(outdir)
    image = np.asarray(result["_render"]["original_bgr"]).copy()

    for instance in result["instances"]:
        mask = instance.get("mask")
        if mask is None:
            continue
        color = stable_color(instance["id"])
        contours, _ = cv2.findContours(np.asarray(mask, dtype=np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(image, contours, -1, color, 2)
        x, y, w, h = instance["bbox"]
        cv2.rectangle(image, (x, y), (x + w, y + h), color, 1)
        text = f'{instance["id"]}:{instance["label"]}'
        _draw_text(image, text, (int(x), max(18, int(y) - 4)), color)

    overlay_path = outdir_path / "overlay.png"
    cv2.imwrite(str(overlay_path), image)
    return overlay_path


def save_debug_masks(result: dict[str, object], outdir: str | Path) -> None:
    outdir_path = ensure_dir(outdir)
    binary_mask = result["debug"].get("binary_mask")
    if binary_mask is not None:
        cv2.imwrite(str(outdir_path / "binary_mask.png"), np.asarray(binary_mask, dtype=np.uint8))

    for instance in result["instances"]:
        if instance.get("mask") is None:
            continue
        cv2.imwrite(
            str(outdir_path / f'instance_{instance["id"]:03d}.png'),
            np.asarray(instance["mask"], dtype=np.uint8) * 255,
        )


def _draw_text(image: np.ndarray, text: str, origin: tuple[int, int], color: tuple[int, int, int]) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (width, height), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = origin
    cv2.rectangle(image, (x - 3, y - height - baseline - 3), (x + width + 3, y + 3), (255, 255, 255), -1)
    cv2.putText(image, text, (x, y), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(image, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)
