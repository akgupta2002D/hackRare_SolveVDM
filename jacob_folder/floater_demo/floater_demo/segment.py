from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .config import SegmentConfig
from .utils import mask_to_bbox


@dataclass(frozen=True)
class InstanceComponent:
    id: int
    mask: np.ndarray
    bbox: tuple[int, int, int, int]
    area: int


def segment_instances(binary_mask: np.ndarray, config: SegmentConfig) -> list[InstanceComponent]:
    binary = (binary_mask > 0).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    instances: list[InstanceComponent] = []
    next_id = 1
    for label_idx in range(1, num_labels):
        area = int(stats[label_idx, cv2.CC_STAT_AREA])
        if area < config.min_instance_area:
            continue
        mask = (labels == label_idx).astype(np.uint8)
        bbox = mask_to_bbox(mask)
        instances.append(
            InstanceComponent(
                id=next_id,
                mask=mask,
                bbox=bbox,
                area=area,
            )
        )
        next_id += 1
    return instances
