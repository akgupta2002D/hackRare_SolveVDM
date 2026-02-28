from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi

import cv2
import numpy as np
from skimage.morphology import skeletonize

from .segment import InstanceComponent


EPS = 1e-6


@dataclass(frozen=True)
class InstanceFeatures:
    area: int
    perimeter: float
    circularity: float
    bbox_aspect_ratio: float
    solidity: float
    skeleton_length: float
    hole_count: int
    thickness_est: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def compute_features(
    grayscale: np.ndarray,
    instance: InstanceComponent,
) -> InstanceFeatures:
    del grayscale
    contours, _ = cv2.findContours(instance.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("Instance component does not contain contours")

    contour = max(contours, key=cv2.contourArea)
    area = int(instance.area)
    perimeter = float(cv2.arcLength(contour, True))
    circularity = float(4.0 * pi * area / (perimeter * perimeter + EPS))

    x, y, w, h = instance.bbox
    bbox_aspect_ratio = float(max(w, h) / (min(w, h) + EPS))

    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull))
    solidity = float(area / (hull_area + EPS))

    skeleton = skeletonize(instance.mask.astype(bool))
    skeleton_length = float(skeleton.sum())
    thickness_est = float(area / (skeleton_length + EPS))
    hole_count = _hole_count(instance.mask)

    return InstanceFeatures(
        area=area,
        perimeter=perimeter,
        circularity=circularity,
        bbox_aspect_ratio=bbox_aspect_ratio,
        solidity=solidity,
        skeleton_length=skeleton_length,
        hole_count=hole_count,
        thickness_est=thickness_est,
    )


def _hole_count(mask: np.ndarray) -> int:
    inverse = np.where(mask > 0, 0, 255).astype(np.uint8)
    flood = inverse.copy()
    flood_mask = np.zeros((inverse.shape[0] + 2, inverse.shape[1] + 2), dtype=np.uint8)
    cv2.floodFill(flood, flood_mask, (0, 0), 0)
    holes = (flood > 0).astype(np.uint8)
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(holes, connectivity=8)
    count = 0
    for idx in range(1, num_labels):
        if int(stats[idx, cv2.CC_STAT_AREA]) > 0:
            count += 1
    return count
