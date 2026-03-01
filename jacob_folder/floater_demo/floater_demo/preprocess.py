from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import PreprocessConfig


@dataclass(frozen=True)
class PreprocessResult:
    image_path: str
    original_bgr: np.ndarray
    grayscale: np.ndarray
    normalized: np.ndarray
    binary_mask: np.ndarray


def preprocess_image(path: str | Path, config: PreprocessConfig) -> PreprocessResult:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Unable to read PNG image: {path}")

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    normalized = _normalize_background(grayscale, config)
    binary_mask = _threshold_and_clean(grayscale, normalized, config)
    return PreprocessResult(
        image_path=str(path),
        original_bgr=image,
        grayscale=grayscale,
        normalized=normalized,
        binary_mask=binary_mask,
    )


def _normalize_background(grayscale: np.ndarray, config: PreprocessConfig) -> np.ndarray:
    clahe = cv2.createCLAHE(
        clipLimit=config.clahe_clip_limit,
        tileGridSize=(config.clahe_tile_grid_size, config.clahe_tile_grid_size),
    )
    return clahe.apply(grayscale)


def _threshold_and_clean(grayscale: np.ndarray, normalized: np.ndarray, config: PreprocessConfig) -> np.ndarray:
    mask = cv2.adaptiveThreshold(
        normalized,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        config.adaptive_block_size,
        config.adaptive_c,
    )
    raw_mask = cv2.threshold(grayscale, config.raw_dark_threshold, 255, cv2.THRESH_BINARY_INV)[1]
    support_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (config.raw_support_dilate_size, config.raw_support_dilate_size),
    )
    mask_support = cv2.dilate(mask, support_kernel)
    supported_raw = cv2.bitwise_and(raw_mask, mask_support)
    adaptive_coverage = float(np.count_nonzero(mask)) / max(mask.shape[0] * mask.shape[1], 1)
    if adaptive_coverage <= config.raw_mask_gate_coverage_max:
        binary = cv2.bitwise_or(mask, supported_raw)
    else:
        binary = mask

    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (config.morph_open_size, config.morph_open_size))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (config.morph_close_size, config.morph_close_size))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    filtered = np.zeros_like(binary)
    for label_idx in range(1, num_labels):
        if int(stats[label_idx, cv2.CC_STAT_AREA]) >= config.min_component_area:
            filtered[labels == label_idx] = 255
    return filtered
