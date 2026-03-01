from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi
from pathlib import Path
import json

import cv2
import numpy as np
from skimage.morphology import skeletonize

from .segment import InstanceComponent


EPS = 1e-6
DEFAULT_MIN_HOLE_AREA_PX = 25


@dataclass(frozen=True)
class InstanceFeatures:
    area: int
    perimeter: float
    circularity: float
    bbox_aspect_ratio: float
    elongation: float
    solidity: float
    skeleton_length: float
    hole_count: int
    max_hole_area_ratio: float
    hole_area_total_ratio: float
    annularity_ratio: float
    thickness_est: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def compute_features(
    grayscale: np.ndarray,
    instance: InstanceComponent,
    debug_dir: str | Path | None = None,
    debug_prefix: str | None = None,
    min_hole_area_px: int = DEFAULT_MIN_HOLE_AREA_PX,
) -> InstanceFeatures:
    contours, hierarchy = cv2.findContours(instance.mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("Instance component does not contain contours")

    contour_index, contour = max(
        ((idx, contour) for idx, contour in enumerate(contours) if _is_external_contour(hierarchy, idx)),
        key=lambda item: cv2.contourArea(item[1]),
    )
    area = int(instance.area)
    perimeter = float(cv2.arcLength(contour, True))
    circularity = float(4.0 * pi * area / (perimeter * perimeter + EPS))

    x, y, w, h = instance.bbox
    bbox_aspect_ratio = float(max(w, h) / (min(w, h) + EPS))

    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull))
    solidity = float(area / (hull_area + EPS))
    elongation = _pca_elongation(instance.mask)

    feature_mask = _smooth_mask(instance.mask)
    skeleton = skeletonize(feature_mask.astype(bool))
    skeleton = _prune_skeleton_spurs(skeleton, iterations=3)
    skeleton_length = float(skeleton.sum())
    thickness_est = _distance_thickness_estimate(feature_mask)
    hole_stats = _hole_stats(
        instance.mask,
        contours,
        hierarchy,
        contour_index,
        area,
        min_hole_area_px=min_hole_area_px,
    )

    features = InstanceFeatures(
        area=area,
        perimeter=perimeter,
        circularity=circularity,
        bbox_aspect_ratio=bbox_aspect_ratio,
        elongation=elongation,
        solidity=solidity,
        skeleton_length=skeleton_length,
        hole_count=hole_stats["hole_count"],
        max_hole_area_ratio=hole_stats["max_hole_area_ratio"],
        hole_area_total_ratio=hole_stats["hole_area_total_ratio"],
        annularity_ratio=hole_stats["annularity_ratio"],
        thickness_est=thickness_est,
    )
    if debug_dir is not None:
        save_feature_debug(
            grayscale=grayscale,
            instance=instance,
            features=features,
            skeleton=skeleton,
            holes_mask=hole_stats["holes_mask"],
            outer_contour=contour,
            hull=hull,
            output_dir=debug_dir,
            prefix=debug_prefix or f"instance_{instance.id:03d}",
        )
    return features


def _hole_stats(
    mask: np.ndarray,
    contours: list[np.ndarray],
    hierarchy: np.ndarray | None,
    contour_index: int,
    mask_area: int,
    min_hole_area_px: int = DEFAULT_MIN_HOLE_AREA_PX,
) -> dict[str, object]:
    holes_mask = np.zeros_like(mask, dtype=np.uint8)
    if hierarchy is None:
        return {
            "hole_count": 0,
            "max_hole_area_ratio": 0.0,
            "hole_area_total_ratio": 0.0,
            "annularity_ratio": 0.0,
            "holes_mask": holes_mask,
        }

    hole_areas: list[float] = []
    for idx, contour in enumerate(contours):
        if int(hierarchy[0][idx][3]) != contour_index:
            continue
        hole_area = float(abs(cv2.contourArea(contour)))
        if hole_area < float(min_hole_area_px):
            continue
        hole_areas.append(hole_area)
        cv2.drawContours(holes_mask, contours, idx, 255, thickness=-1)

    if not hole_areas:
        return {
            "hole_count": 0,
            "max_hole_area_ratio": 0.0,
            "hole_area_total_ratio": 0.0,
            "annularity_ratio": 0.0,
            "holes_mask": holes_mask,
        }

    total_hole_area = float(sum(hole_areas))
    max_hole_area = float(max(hole_areas))
    mask_area = max(mask_area, 1)
    filled_area = float(mask_area + total_hole_area)
    return {
        "hole_count": len(hole_areas),
        "max_hole_area_ratio": max_hole_area / mask_area,
        "hole_area_total_ratio": total_hole_area / mask_area,
        "annularity_ratio": total_hole_area / max(filled_area, 1.0),
        "holes_mask": holes_mask,
    }


def _is_external_contour(hierarchy: np.ndarray | None, contour_index: int) -> bool:
    return hierarchy is None or int(hierarchy[0][contour_index][3]) < 0


def _smooth_mask(mask: np.ndarray) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    smoothed = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_CLOSE, kernel)
    return smoothed


def _prune_skeleton_spurs(skeleton: np.ndarray, iterations: int = 2) -> np.ndarray:
    pruned = skeleton.astype(bool).copy()
    for _ in range(iterations):
        endpoints = _skeleton_endpoints(pruned)
        if not np.any(endpoints):
            break
        pruned = np.logical_and(pruned, np.logical_not(endpoints))
    return pruned


def _skeleton_endpoints(skeleton: np.ndarray) -> np.ndarray:
    padded = np.pad(skeleton.astype(np.uint8), 1, mode="constant")
    endpoints = np.zeros_like(skeleton, dtype=bool)
    ys, xs = np.where(skeleton)
    for y, x in zip(ys, xs):
        neighborhood = padded[y : y + 3, x : x + 3]
        neighbors = int(neighborhood.sum()) - 1
        if neighbors <= 1:
            endpoints[y, x] = True
    return endpoints


def _distance_thickness_estimate(mask: np.ndarray) -> float:
    distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    positive = distance[distance > 0]
    if positive.size == 0:
        return 0.0
    return float(2.0 * np.median(positive))


def _pca_elongation(mask: np.ndarray) -> float:
    ys, xs = np.where(mask > 0)
    if xs.size < 3:
        return 1.0
    coords = np.column_stack((xs.astype(np.float32), ys.astype(np.float32)))
    centered = coords - coords.mean(axis=0, keepdims=True)
    covariance = np.cov(centered, rowvar=False)
    eigenvalues = np.linalg.eigvalsh(covariance)
    if eigenvalues.size != 2:
        return 1.0
    lambda1 = float(max(eigenvalues))
    lambda2 = float(min(eigenvalues))
    return float(np.sqrt(lambda1 / (lambda2 + EPS)))


def save_feature_debug(
    grayscale: np.ndarray,
    instance: InstanceComponent,
    features: InstanceFeatures,
    skeleton: np.ndarray,
    holes_mask: np.ndarray,
    outer_contour: np.ndarray,
    hull: np.ndarray,
    output_dir: str | Path,
    prefix: str,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    mask = instance.mask.astype(np.uint8) * 255
    cv2.imwrite(str(output / f"{prefix}_mask.png"), mask)
    cv2.imwrite(str(output / f"{prefix}_skeleton.png"), skeleton.astype(np.uint8) * 255)
    cv2.imwrite(str(output / f"{prefix}_holes.png"), holes_mask)

    overlay = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2BGR)
    cv2.drawContours(overlay, [outer_contour], -1, (0, 255, 0), 2)
    cv2.drawContours(overlay, [hull], -1, (0, 0, 255), 1)
    cv2.imwrite(str(output / f"{prefix}_contour_hull.png"), overlay)

    with (output / f"{prefix}_features.json").open("w", encoding="utf-8") as handle:
        json.dump(features.to_dict(), handle, indent=2)
