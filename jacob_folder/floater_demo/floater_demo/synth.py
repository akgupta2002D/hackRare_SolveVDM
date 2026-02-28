from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import DemoConfig, load_config
from .infer import infer_image
from .utils import ensure_dir, mask_to_bbox, stable_color


LABELS = ("dots", "strands", "membranes", "rings")


@dataclass(frozen=True)
class SyntheticInstance:
    id: int
    label: str
    mask: np.ndarray
    bbox: tuple[int, int, int, int]
    contour: list[list[int]]
    layer: np.ndarray


def generate_synth_dataset(
    outdir: str | Path,
    n: int = 2000,
    seed: int = 42,
    width: int = 320,
    height: int = 320,
    config: DemoConfig | None = None,
) -> dict[str, object]:
    outdir_path = ensure_dir(outdir)
    rng = np.random.default_rng(seed)
    demo_config = config or load_config()

    label_counts = {label: 0 for label in LABELS}
    generated_ids: list[str] = []

    for index in range(n):
        image_id = f"{index:06d}"
        image, instances = _generate_image(rng, width, height)
        generated_ids.append(image_id)

        raw_path = outdir_path / f"{image_id}.png"
        overlay_path = outdir_path / f"{image_id}_overlay.png"
        json_path = outdir_path / f"{image_id}.json"

        cv2.imwrite(str(raw_path), image)
        _save_gt_overlay(image, instances, overlay_path)
        _save_annotation_json(image_id, width, height, instances, json_path)

        for instance in instances:
            label_counts[instance.label] += 1

    self_check = _run_self_check(outdir_path, generated_ids[: min(20, len(generated_ids))], demo_config)
    return {
        "outdir": str(outdir_path),
        "images": n,
        "label_counts": label_counts,
        "self_check": self_check,
    }


def _generate_image(rng: np.random.Generator, width: int, height: int) -> tuple[np.ndarray, list[SyntheticInstance]]:
    canvas = np.full((height, width), 255, dtype=np.float32)
    occupancy = np.zeros((height, width), dtype=np.uint8)
    instances: list[SyntheticInstance] = []

    instance_count = int(rng.integers(1, 5))
    for instance_id in range(1, instance_count + 1):
        label = str(rng.choice(LABELS, p=[0.34, 0.28, 0.2, 0.18]))
        instance = _place_instance(rng, label, width, height, occupancy, instance_id)
        instances.append(instance)
        canvas = np.minimum(canvas, instance.layer.astype(np.float32))
        occupancy = np.maximum(occupancy, instance.mask)

    sigma = float(rng.uniform(1.2, 2.0))
    final = cv2.GaussianBlur(canvas, (0, 0), sigmaX=sigma, sigmaY=sigma)
    final = np.clip(final, 0, 255).astype(np.uint8)
    return cv2.cvtColor(final, cv2.COLOR_GRAY2BGR), instances


def _place_instance(
    rng: np.random.Generator,
    label: str,
    width: int,
    height: int,
    occupancy: np.ndarray,
    instance_id: int,
) -> SyntheticInstance:
    last_candidate: SyntheticInstance | None = None
    for _ in range(20):
        candidate = _make_instance(rng, label, width, height, instance_id)
        last_candidate = candidate
        overlap = np.logical_and(candidate.mask > 0, occupancy > 0).sum()
        candidate_area = max(int(candidate.mask.sum() // 255), 1)
        if overlap / candidate_area <= 0.03:
            return candidate
    assert last_candidate is not None
    return last_candidate


def _make_instance(
    rng: np.random.Generator,
    label: str,
    width: int,
    height: int,
    instance_id: int,
) -> SyntheticInstance:
    if label == "dots":
        mask, layer = _draw_dots(rng, width, height)
    elif label == "strands":
        mask, layer = _draw_strands(rng, width, height)
    elif label == "membranes":
        mask, layer = _draw_membranes(rng, width, height)
    else:
        mask, layer = _draw_rings(rng, width, height)

    bbox = mask_to_bbox(mask)
    contour = _largest_contour(mask)
    return SyntheticInstance(
        id=instance_id,
        label=label,
        mask=mask,
        bbox=bbox,
        contour=contour,
        layer=layer,
    )


def _draw_dots(rng: np.random.Generator, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    variant = str(rng.choice(["single", "cluster", "cloud"], p=[0.35, 0.4, 0.25]))
    cx = int(rng.integers(40, width - 40))
    cy = int(rng.integers(40, height - 40))
    count = {"single": 1, "cluster": int(rng.integers(3, 7)), "cloud": int(rng.integers(12, 28))}[variant]
    spread = {"single": 0, "cluster": 14, "cloud": 20}[variant]

    for _ in range(count):
        radius = int(rng.integers(3, 11 if variant != "cloud" else 7))
        offset_x = int(rng.normal(0, spread))
        offset_y = int(rng.normal(0, spread))
        px = int(np.clip(cx + offset_x, radius + 4, width - radius - 4))
        py = int(np.clip(cy + offset_y, radius + 4, height - radius - 4))
        intensity = int(rng.integers(95, 190))
        cv2.circle(temp, (px, py), radius, intensity, -1, lineType=cv2.LINE_AA)
        cv2.circle(mask, (px, py), radius, 255, -1, lineType=cv2.LINE_AA)

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    sigma = float(rng.uniform(1.0, 1.8))
    layer = cv2.GaussianBlur(temp, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return mask, layer


def _draw_strands(rng: np.random.Generator, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    variant = str(rng.choice(["long", "short", "worm", "multi"], p=[0.3, 0.25, 0.3, 0.15]))
    strands = 1 if variant != "multi" else int(rng.integers(2, 4))

    for _ in range(strands):
        points = _strand_points(rng, width, height, variant)
        thickness = int(rng.integers(2, 8))
        intensity = int(rng.integers(95, 170))
        pts = points.reshape((-1, 1, 2))
        cv2.polylines(temp, [pts], False, intensity, thickness=thickness, lineType=cv2.LINE_AA)
        cv2.polylines(mask, [pts], False, 255, thickness=thickness, lineType=cv2.LINE_AA)
        if thickness >= 4:
            cv2.polylines(temp, [pts], False, min(intensity + 20, 220), thickness=max(1, thickness - 2), lineType=cv2.LINE_AA)

    sigma = float(rng.uniform(0.9, 1.5))
    layer = cv2.GaussianBlur(temp, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return mask, layer


def _draw_membranes(rng: np.random.Generator, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    variant = str(rng.choice(["sheet", "cloud", "smudges"], p=[0.4, 0.35, 0.25]))
    cx = int(rng.integers(55, width - 55))
    cy = int(rng.integers(55, height - 55))
    intensity = int(rng.integers(135, 205))

    if variant == "sheet":
        pts = _blob_points(rng, cx, cy, int(rng.integers(36, 60)), int(rng.integers(7, 12)))
        cv2.fillPoly(temp, [pts], intensity, lineType=cv2.LINE_AA)
        cv2.fillPoly(mask, [pts], 255, lineType=cv2.LINE_AA)
    elif variant == "cloud":
        for _ in range(int(rng.integers(4, 8))):
            axes = (int(rng.integers(18, 42)), int(rng.integers(12, 28)))
            offset = (int(rng.normal(0, 18)), int(rng.normal(0, 14)))
            center = (
                int(np.clip(cx + offset[0], axes[0] + 5, width - axes[0] - 5)),
                int(np.clip(cy + offset[1], axes[1] + 5, height - axes[1] - 5)),
            )
            angle = float(rng.uniform(0, 180))
            cv2.ellipse(temp, center, axes, angle, 0, 360, intensity, -1, lineType=cv2.LINE_AA)
            cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1, lineType=cv2.LINE_AA)
    else:
        for _ in range(int(rng.integers(2, 5))):
            radius = int(rng.integers(16, 30))
            offset = (int(rng.normal(0, 24)), int(rng.normal(0, 20)))
            center = (
                int(np.clip(cx + offset[0], radius + 5, width - radius - 5)),
                int(np.clip(cy + offset[1], radius + 5, height - radius - 5)),
            )
            cv2.circle(temp, center, radius, intensity, -1, lineType=cv2.LINE_AA)
            cv2.circle(mask, center, radius, 255, -1, lineType=cv2.LINE_AA)

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    sigma = float(rng.uniform(2.2, 3.8))
    layer = cv2.GaussianBlur(temp, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return mask, layer


def _draw_rings(rng: np.random.Generator, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    cx = int(rng.integers(50, width - 50))
    cy = int(rng.integers(50, height - 50))
    radius = float(rng.integers(18, 42))
    thickness = int(rng.integers(4, 12))
    intensity = int(rng.integers(95, 175))

    pts = _ring_points(rng, cx, cy, radius)
    pts_poly = pts.reshape((-1, 1, 2))
    cv2.polylines(temp, [pts_poly], True, intensity, thickness=thickness, lineType=cv2.LINE_AA)
    cv2.polylines(mask, [pts_poly], True, 255, thickness=thickness, lineType=cv2.LINE_AA)

    if rng.random() < 0.35:
        gap_angle = float(rng.uniform(0, 2 * np.pi))
        gap_radius = int(radius)
        p1 = (int(cx + np.cos(gap_angle) * gap_radius), int(cy + np.sin(gap_angle) * gap_radius))
        p2 = (
            int(cx + np.cos(gap_angle + 0.22) * gap_radius),
            int(cy + np.sin(gap_angle + 0.22) * gap_radius),
        )
        cv2.line(temp, p1, p2, 255, thickness=max(1, thickness // 2), lineType=cv2.LINE_AA)

    sigma = float(rng.uniform(1.0, 1.7))
    layer = cv2.GaussianBlur(temp, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return mask, layer


def _strand_points(rng: np.random.Generator, width: int, height: int, variant: str) -> np.ndarray:
    if variant == "long":
        length = float(rng.uniform(120, 210))
        amplitude = float(rng.uniform(12, 32))
        points_n = int(rng.integers(10, 18))
    elif variant == "short":
        length = float(rng.uniform(55, 110))
        amplitude = float(rng.uniform(8, 22))
        points_n = int(rng.integers(8, 14))
    else:
        length = float(rng.uniform(80, 150))
        amplitude = float(rng.uniform(18, 38))
        points_n = int(rng.integers(12, 22))

    theta = float(rng.uniform(0, np.pi))
    center = np.array([rng.integers(40, width - 40), rng.integers(40, height - 40)], dtype=np.float32)
    direction = np.array([np.cos(theta), np.sin(theta)], dtype=np.float32)
    normal = np.array([-direction[1], direction[0]], dtype=np.float32)

    ts = np.linspace(-0.5, 0.5, points_n)
    points: list[list[int]] = []
    for t in ts:
        wave = np.sin((t + 0.5) * np.pi * rng.uniform(1.2, 2.8))
        jitter = rng.normal(0, amplitude * 0.18)
        pos = center + direction * (t * length) + normal * (wave * amplitude + jitter)
        x = int(np.clip(pos[0], 8, width - 8))
        y = int(np.clip(pos[1], 8, height - 8))
        points.append([x, y])
    return np.asarray(points, dtype=np.int32)


def _blob_points(rng: np.random.Generator, cx: int, cy: int, radius: int, points_n: int) -> np.ndarray:
    points: list[list[int]] = []
    for angle in np.linspace(0, 2 * np.pi, points_n, endpoint=False):
        local_radius = radius * rng.uniform(0.6, 1.15)
        x = int(cx + np.cos(angle) * local_radius * rng.uniform(0.8, 1.1))
        y = int(cy + np.sin(angle) * local_radius * rng.uniform(0.6, 1.0))
        points.append([x, y])
    return cv2.convexHull(np.asarray(points, dtype=np.int32))


def _ring_points(rng: np.random.Generator, cx: int, cy: int, radius: float) -> np.ndarray:
    points: list[list[int]] = []
    count = int(rng.integers(18, 28))
    for angle in np.linspace(0, 2 * np.pi, count, endpoint=False):
        noisy_radius = radius * rng.uniform(0.82, 1.18)
        x = int(cx + np.cos(angle) * noisy_radius)
        y = int(cy + np.sin(angle) * noisy_radius * rng.uniform(0.82, 1.12))
        points.append([x, y])
    return np.asarray(points, dtype=np.int32)


def _largest_contour(mask: np.ndarray) -> list[list[int]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea)
    return [[int(point[0][0]), int(point[0][1])] for point in contour]


def _save_gt_overlay(image: np.ndarray, instances: list[SyntheticInstance], path: Path) -> None:
    overlay = image.copy()
    for instance in instances:
        color = stable_color(instance.id)
        contours, _ = cv2.findContours(instance.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, color, 2)
        x, y, w, h = instance.bbox
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 1)
        _draw_text(overlay, f"{instance.id}:{instance.label}", (x, max(18, y - 4)), color)
    cv2.imwrite(str(path), overlay)


def _save_annotation_json(
    image_id: str,
    width: int,
    height: int,
    instances: list[SyntheticInstance],
    path: Path,
) -> None:
    payload = {
        "image_id": image_id,
        "width": width,
        "height": height,
        "instances": [
            {
                "id": instance.id,
                "label": instance.label,
                "bbox": list(instance.bbox),
                "contour": instance.contour,
            }
            for instance in instances
        ],
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _run_self_check(outdir: Path, image_ids: list[str], config: DemoConfig) -> dict[str, int]:
    gt_total = 0
    detected_total = 0
    for image_id in image_ids:
        raw_path = outdir / f"{image_id}.png"
        annotation_path = outdir / f"{image_id}.json"
        with annotation_path.open("r", encoding="utf-8") as handle:
            annotation = json.load(handle)
        gt_total += len(annotation["instances"])
        result = infer_image(raw_path, config, save_debug_masks=False)
        detected_total += int(result["summary"]["instance_count"])

    report = {
        "checked_images": len(image_ids),
        "ground_truth_instances": gt_total,
        "detected_instances": detected_total,
    }
    print(
        "Synthetic self-check:",
        f'images={report["checked_images"]}',
        f'gt_instances={report["ground_truth_instances"]}',
        f'detected_instances={report["detected_instances"]}',
    )
    return report


def _draw_text(image: np.ndarray, text: str, origin: tuple[int, int], color: tuple[int, int, int]) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (width, height), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = origin
    cv2.rectangle(image, (x - 3, y - height - baseline - 3), (x + width + 3, y + 3), (255, 255, 255), -1)
    cv2.putText(image, text, (x, y), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(image, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)
