from __future__ import annotations

import numpy as np

from floater_demo.visualize import draw_instances_overlay, layout_instance_labels


def test_label_layout_avoids_heavy_overlap() -> None:
    image = np.full((220, 240, 3), 255, dtype=np.uint8)
    instances = [
        {"id": 1, "bbox": [20, 20, 50, 40], "label": "dots", "confidence": 0.91, "mask": None},
        {"id": 2, "bbox": [36, 32, 52, 42], "label": "strands", "confidence": 0.88, "mask": None},
        {"id": 3, "bbox": [52, 44, 54, 44], "label": "rings", "confidence": 0.95, "mask": None},
        {"id": 4, "bbox": [68, 56, 58, 46], "label": "membranes", "confidence": 0.73, "mask": None},
    ]

    placements = layout_instance_labels(image.shape[:2], instances, strategy="greedy")

    for idx, placement in enumerate(placements):
        for other in placements[idx + 1 :]:
            assert _intersection_area(placement.rect, other.rect) == 0

    overlay = draw_instances_overlay(image, instances, strategy="relax")
    assert overlay.shape == image.shape


def _intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0
    return int((x1 - x0) * (y1 - y0))
