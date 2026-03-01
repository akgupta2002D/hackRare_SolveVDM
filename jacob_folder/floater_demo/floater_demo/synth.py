from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import DemoConfig, load_config
from .infer import infer_image
from .utils import ensure_dir, mask_to_bbox, stable_color
from .visualize import draw_instances_overlay


LABELS = ("dots", "strands", "membranes", "rings")
ADVERSARIAL_SUITES = (
    "membrane_with_tiny_hole",
    "membrane_with_big_hole",
    "membrane_with_pinhole_noise",
    "strand_with_loop_tail",
    "crossing_strands_pocket_hole",
    "thick_strand_long",
    "broken_ring_gap_small",
    "broken_ring_gap_large",
)
CLOSED_LOOP_SUITES = (
    "true_dot_clean",
    "thick_strand_long",
    "dense_scribble_merge",
    "crossing_strands_pocket_hole",
    "true_ring_clean",
    "true_strand_thin",
    "small_ring_clean",
    "small_ring_overlap_strand",
    "membrane_cloud_faint",
    "strand_bundle_near_touch",
    "mixed_distinct_scene",
)


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
    overlay_instances = [
        {
            "id": instance.id,
            "bbox": list(instance.bbox),
            "label": instance.label,
            "confidence": 1.0,
            "mask": instance.mask,
        }
        for instance in instances
    ]
    overlay = draw_instances_overlay(image.copy(), overlay_instances, strategy="greedy", draw_leaders=False)
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


def generate_closed_loop_case(
    suite_name: str,
    seed: int = 42,
    width: int = 320,
    height: int = 320,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    if suite_name not in CLOSED_LOOP_SUITES:
        raise ValueError(f"Unknown closed-loop suite: {suite_name}")

    if suite_name in {"thick_strand_long", "crossing_strands_pocket_hole"}:
        image, instance, meta = generate_adversarial_case(suite_name, seed=seed, width=width, height=height)
        return image, [instance], meta

    rng = np.random.default_rng(seed)
    temp = np.full((height, width), 255, dtype=np.uint8)
    instances: list[SyntheticInstance] = []
    meta: dict[str, object] = {"suite_name": suite_name}

    if suite_name == "dense_scribble_merge":
        image, instances, meta = _generate_dense_scribble_merge(rng, width, height)
    elif suite_name == "true_dot_clean":
        image, instances, meta = _generate_true_dot_clean(rng, width, height)
    elif suite_name == "true_ring_clean":
        image, instances, meta = _generate_true_ring_clean(rng, width, height)
    elif suite_name == "true_strand_thin":
        image, instances, meta = _generate_true_strand_thin(rng, width, height)
    elif suite_name == "small_ring_clean":
        image, instances, meta = _generate_small_ring_clean(rng, width, height)
    elif suite_name == "small_ring_overlap_strand":
        image, instances, meta = _generate_small_ring_overlap_strand(rng, width, height)
    elif suite_name == "membrane_cloud_faint":
        image, instances, meta = _generate_membrane_cloud_faint(rng, width, height)
    elif suite_name == "strand_bundle_near_touch":
        image, instances, meta = _generate_strand_bundle_near_touch(rng, width, height)
    else:
        image, instances, meta = _generate_mixed_distinct_scene(rng, width, height)

    return image, instances, meta


def _generate_dense_scribble_merge(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    instances: list[SyntheticInstance] = []
    center = np.array([width // 2, height // 2], dtype=np.float32)
    count = int(rng.integers(6, 11))

    for instance_id in range(1, count + 1):
        mask = np.zeros((height, width), dtype=np.uint8)
        points = _scribble_points(rng, center, width, height)
        pts = points.reshape((-1, 1, 2))
        thickness = int(rng.integers(5, 8))
        intensity = int(rng.integers(102, 138))
        cv2.polylines(temp, [pts], False, intensity, thickness=thickness, lineType=cv2.LINE_AA)
        cv2.polylines(mask, [pts], False, 255, thickness=thickness, lineType=cv2.LINE_AA)
        mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=0.6, sigmaY=0.6)
        mask = np.where(mask > 80, 255, 0).astype(np.uint8)
        instances.append(
            SyntheticInstance(
                id=instance_id,
                label="strands",
                mask=mask,
                bbox=mask_to_bbox(mask),
                contour=_largest_contour(mask),
                layer=temp.copy(),
            )
        )

    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=1.45, sigmaY=1.45)
    meta = {"suite_name": "dense_scribble_merge", "expected_label": "strands", "gt_instances": count}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), instances, meta


def _generate_true_ring_clean(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (width // 2 + int(rng.integers(-10, 10)), height // 2 + int(rng.integers(-8, 8)))
    axes = (int(rng.integers(46, 62)), int(rng.integers(38, 54)))
    angle = float(rng.uniform(-18, 18))
    thickness = int(rng.integers(8, 11))
    intensity = int(rng.integers(104, 128))
    cv2.ellipse(temp, center, axes, angle, 0, 360, intensity, thickness=thickness, lineType=cv2.LINE_AA)
    cv2.ellipse(mask, center, axes, angle, 0, 360, 255, thickness=thickness, lineType=cv2.LINE_AA)
    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=1.2, sigmaY=1.2)
    instance = SyntheticInstance(
        id=1,
        label="rings",
        mask=mask,
        bbox=mask_to_bbox(mask),
        contour=_largest_contour(mask),
        layer=image_gray,
    )
    meta = {"suite_name": "true_ring_clean", "expected_label": "rings", "gt_instances": 1}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), [instance], meta


def _generate_true_dot_clean(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (width // 2 + int(rng.integers(-20, 20)), height // 2 + int(rng.integers(-20, 20)))
    radius = int(rng.integers(12, 19))
    intensity = int(rng.integers(104, 132))
    cv2.circle(temp, center, radius, intensity, -1, lineType=cv2.LINE_AA)
    cv2.circle(mask, center, radius, 255, -1, lineType=cv2.LINE_AA)
    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=1.05, sigmaY=1.05)
    instance = SyntheticInstance(
        id=1,
        label="dots",
        mask=mask,
        bbox=mask_to_bbox(mask),
        contour=_largest_contour(mask),
        layer=image_gray,
    )
    meta = {"suite_name": "true_dot_clean", "expected_label": "dots", "gt_instances": 1}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), [instance], meta


def _generate_true_strand_thin(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    points = _strand_points(rng, width, height, "long").reshape((-1, 1, 2))
    thickness = int(rng.integers(3, 5))
    intensity = int(rng.integers(96, 125))
    cv2.polylines(temp, [points], False, intensity, thickness=thickness, lineType=cv2.LINE_AA)
    cv2.polylines(mask, [points], False, 255, thickness=thickness, lineType=cv2.LINE_AA)
    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=0.95, sigmaY=0.95)
    instance = SyntheticInstance(
        id=1,
        label="strands",
        mask=mask,
        bbox=mask_to_bbox(mask),
        contour=_largest_contour(mask),
        layer=image_gray,
    )
    meta = {"suite_name": "true_strand_thin", "expected_label": "strands", "gt_instances": 1}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), [instance], meta


def _generate_small_ring_clean(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (width // 2 + int(rng.integers(-16, 16)), height // 2 + int(rng.integers(-16, 16)))
    axes = (int(rng.integers(18, 28)), int(rng.integers(15, 24)))
    angle = float(rng.uniform(-24, 24))
    thickness = int(rng.integers(5, 8))
    intensity = int(rng.integers(102, 132))
    cv2.ellipse(temp, center, axes, angle, 0, 360, intensity, thickness=thickness, lineType=cv2.LINE_AA)
    cv2.ellipse(mask, center, axes, angle, 0, 360, 255, thickness=thickness, lineType=cv2.LINE_AA)
    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=1.0, sigmaY=1.0)
    instance = SyntheticInstance(
        id=1,
        label="rings",
        mask=mask,
        bbox=mask_to_bbox(mask),
        contour=_largest_contour(mask),
        layer=image_gray,
    )
    meta = {"suite_name": "small_ring_clean", "expected_label": "rings", "gt_instances": 1, "bucket": "small_ring"}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), [instance], meta


def _generate_small_ring_overlap_strand(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    ring_mask = np.zeros((height, width), dtype=np.uint8)
    strand_mask = np.zeros((height, width), dtype=np.uint8)

    ring_center = (width // 2 - 18 + int(rng.integers(-8, 8)), height // 2 + int(rng.integers(-10, 10)))
    ring_axes = (int(rng.integers(18, 26)), int(rng.integers(16, 24)))
    ring_angle = float(rng.uniform(-15, 15))
    ring_thickness = int(rng.integers(5, 8))
    cv2.ellipse(temp, ring_center, ring_axes, ring_angle, 0, 360, 110, thickness=ring_thickness, lineType=cv2.LINE_AA)
    cv2.ellipse(ring_mask, ring_center, ring_axes, ring_angle, 0, 360, 255, thickness=ring_thickness, lineType=cv2.LINE_AA)

    strand_points = np.array(
        [
            [ring_center[0] - 36, ring_center[1] + 18],
            [ring_center[0] - 8, ring_center[1] + 4],
            [ring_center[0] + 26, ring_center[1] - 8],
            [ring_center[0] + 60, ring_center[1] - 12],
        ],
        dtype=np.int32,
    ).reshape((-1, 1, 2))
    cv2.polylines(temp, [strand_points], False, 118, thickness=6, lineType=cv2.LINE_AA)
    cv2.polylines(strand_mask, [strand_points], False, 255, thickness=6, lineType=cv2.LINE_AA)

    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=1.25, sigmaY=1.25)
    instances = [
        SyntheticInstance(
            id=1,
            label="rings",
            mask=ring_mask,
            bbox=mask_to_bbox(ring_mask),
            contour=_largest_contour(ring_mask),
            layer=image_gray,
        ),
        SyntheticInstance(
            id=2,
            label="strands",
            mask=strand_mask,
            bbox=mask_to_bbox(strand_mask),
            contour=_largest_contour(strand_mask),
            layer=image_gray,
        ),
    ]
    meta = {"suite_name": "small_ring_overlap_strand", "expected_label": "mixed", "gt_instances": 2, "bucket": "small_ring_overlap"}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), instances, meta


def _generate_membrane_cloud_faint(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (width // 2 + int(rng.integers(-16, 16)), height // 2 + int(rng.integers(-12, 12)))
    axes = (int(rng.integers(42, 58)), int(rng.integers(20, 30)))
    angle = float(rng.uniform(-24, 24))
    cv2.ellipse(temp, center, axes, angle, 0, 360, int(rng.integers(108, 128)), -1, lineType=cv2.LINE_AA)
    cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1, lineType=cv2.LINE_AA)
    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=1.0, sigmaY=1.0)
    instance = SyntheticInstance(
        id=1,
        label="membranes",
        mask=mask,
        bbox=mask_to_bbox(mask),
        contour=_largest_contour(mask),
        layer=image_gray,
    )
    meta = {"suite_name": "membrane_cloud_faint", "expected_label": "membranes", "gt_instances": 1, "bucket": "clean"}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), [instance], meta


def _generate_strand_bundle_near_touch(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    temp = np.full((height, width), 255, dtype=np.uint8)
    instances: list[SyntheticInstance] = []
    base_center = np.array([width // 2, height // 2], dtype=np.float32)
    offsets = [(-22, -10), (0, 0), (22, 10)]
    for instance_id, (ox, oy) in enumerate(offsets, start=1):
        mask = np.zeros((height, width), dtype=np.uint8)
        points = _strand_points(rng, width, height, "short").astype(np.float32)
        points += np.array([ox, oy], dtype=np.float32)
        points[:, 0] = np.clip(points[:, 0], 8, width - 8)
        points[:, 1] = np.clip(points[:, 1], 8, height - 8)
        pts = points.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(temp, [pts], False, int(rng.integers(104, 132)), thickness=5, lineType=cv2.LINE_AA)
        cv2.polylines(mask, [pts], False, 255, thickness=5, lineType=cv2.LINE_AA)
        instances.append(
            SyntheticInstance(
                id=instance_id,
                label="strands",
                mask=mask,
                bbox=mask_to_bbox(mask),
                contour=_largest_contour(mask),
                layer=temp.copy(),
            )
        )
    image_gray = cv2.GaussianBlur(temp, (0, 0), sigmaX=1.1, sigmaY=1.1)
    for idx, instance in enumerate(instances):
        instances[idx] = SyntheticInstance(
            id=instance.id,
            label=instance.label,
            mask=instance.mask,
            bbox=instance.bbox,
            contour=instance.contour,
            layer=image_gray,
        )
    meta = {"suite_name": "strand_bundle_near_touch", "expected_label": "strands", "gt_instances": len(instances), "bucket": "overlap"}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), instances, meta


def _generate_mixed_distinct_scene(
    rng: np.random.Generator,
    width: int,
    height: int,
) -> tuple[np.ndarray, list[SyntheticInstance], dict[str, object]]:
    canvas = np.full((height, width), 255, dtype=np.float32)
    occupancy = np.zeros((height, width), dtype=np.uint8)
    instances: list[SyntheticInstance] = []
    ordered_labels = ["dots", "strands", "membranes", "rings"]
    for instance_id, label in enumerate(ordered_labels, start=1):
        instance = _place_instance(rng, label, width, height, occupancy, instance_id)
        canvas = np.minimum(canvas, instance.layer.astype(np.float32))
        occupancy = np.maximum(occupancy, instance.mask)
        instances.append(instance)
    image_gray = cv2.GaussianBlur(canvas.astype(np.uint8), (0, 0), sigmaX=1.4, sigmaY=1.4)
    refreshed = [
        SyntheticInstance(
            id=instance.id,
            label=instance.label,
            mask=instance.mask,
            bbox=instance.bbox,
            contour=instance.contour,
            layer=image_gray,
        )
        for instance in instances
    ]
    meta = {"suite_name": "mixed_distinct_scene", "expected_label": "mixed", "gt_instances": len(refreshed), "bucket": "clean"}
    return cv2.cvtColor(image_gray, cv2.COLOR_GRAY2BGR), refreshed, meta


def _scribble_points(
    rng: np.random.Generator,
    center: np.ndarray,
    width: int,
    height: int,
) -> np.ndarray:
    points: list[list[int]] = []
    point = center + rng.normal(0, 18, size=2)
    steps = int(rng.integers(10, 18))
    for _ in range(steps):
        delta = rng.normal(0, 18, size=2)
        pull = (center - point) * 0.18
        point = point + delta + pull
        x = int(np.clip(point[0], 10, width - 10))
        y = int(np.clip(point[1], 10, height - 10))
        points.append([x, y])
    return np.asarray(points, dtype=np.int32)


def generate_adversarial_case(
    suite_name: str,
    seed: int = 42,
    width: int = 320,
    height: int = 320,
) -> tuple[np.ndarray, SyntheticInstance, dict[str, object]]:
    if suite_name not in ADVERSARIAL_SUITES:
        raise ValueError(f"Unknown adversarial suite: {suite_name}")

    rng = np.random.default_rng(seed)
    temp = np.full((height, width), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)

    expected_label = "membranes"
    blur_sigma = 1.6

    if suite_name == "membrane_with_tiny_hole":
        expected_label = "membranes"
        for center, axes, angle in [
            ((145, 160), (62, 34), 20),
            ((185, 165), (58, 30), -10),
            ((165, 142), (46, 24), 35),
        ]:
            cv2.ellipse(temp, center, axes, angle, 0, 360, 160, -1, lineType=cv2.LINE_AA)
            cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1, lineType=cv2.LINE_AA)
        cv2.circle(temp, (176, 158), 5, 255, -1, lineType=cv2.LINE_AA)
        cv2.circle(mask, (176, 158), 5, 0, -1, lineType=cv2.LINE_AA)
        blur_sigma = 3.0
    elif suite_name == "membrane_with_big_hole":
        expected_label = "membranes"
        for center, axes, angle in [
            ((130, 162), (72, 34), 18),
            ((195, 160), (78, 32), -6),
            ((168, 140), (54, 22), 28),
        ]:
            cv2.ellipse(temp, center, axes, angle, 0, 360, 154, -1, lineType=cv2.LINE_AA)
            cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(temp, (192, 160), (26, 20), 5, 0, 360, 255, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(mask, (192, 160), (26, 20), 5, 0, 360, 0, -1, lineType=cv2.LINE_AA)
        blur_sigma = 2.7
    elif suite_name == "membrane_with_pinhole_noise":
        expected_label = "membranes"
        for center, axes, angle in [
            ((144, 162), (68, 36), 18),
            ((196, 162), (70, 34), -8),
            ((170, 140), (56, 26), 24),
        ]:
            cv2.ellipse(temp, center, axes, angle, 0, 360, 158, -1, lineType=cv2.LINE_AA)
            cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1, lineType=cv2.LINE_AA)
        for _ in range(int(rng.integers(4, 11))):
            px = int(rng.integers(132, 208))
            py = int(rng.integers(132, 188))
            radius = int(rng.integers(1, 3))
            cv2.circle(temp, (px, py), radius, 255, -1, lineType=cv2.LINE_AA)
            cv2.circle(mask, (px, py), radius, 0, -1, lineType=cv2.LINE_AA)
        blur_sigma = 2.8
    elif suite_name == "strand_with_loop_tail":
        expected_label = "strands"
        points = np.array([[40, 230], [85, 205], [130, 180], [170, 158], [205, 138]], dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(temp, [points], False, 118, thickness=7, lineType=cv2.LINE_AA)
        cv2.polylines(mask, [points], False, 255, thickness=7, lineType=cv2.LINE_AA)
        cv2.circle(temp, (230, 120), 22, 118, thickness=7, lineType=cv2.LINE_AA)
        cv2.circle(mask, (230, 120), 22, 255, thickness=7, lineType=cv2.LINE_AA)
        cv2.line(temp, (205, 138), (214, 133), 118, thickness=7, lineType=cv2.LINE_AA)
        cv2.line(mask, (205, 138), (214, 133), 255, thickness=7, lineType=cv2.LINE_AA)
        blur_sigma = 1.2
    elif suite_name == "crossing_strands_pocket_hole":
        expected_label = "strands"
        pts1 = np.array([[45, 110], [110, 150], [165, 180], [240, 230]], dtype=np.int32).reshape((-1, 1, 2))
        pts2 = np.array([[50, 235], [120, 185], [180, 145], [255, 90]], dtype=np.int32).reshape((-1, 1, 2))
        pts3 = np.array([[110, 150], [145, 132], [180, 145]], dtype=np.int32).reshape((-1, 1, 2))
        for pts in (pts1, pts2, pts3):
            cv2.polylines(temp, [pts], False, 112, thickness=8, lineType=cv2.LINE_AA)
            cv2.polylines(mask, [pts], False, 255, thickness=8, lineType=cv2.LINE_AA)
        blur_sigma = 1.25
    elif suite_name == "thick_strand_long":
        expected_label = "strands"
        points = _strand_points(rng, width, height, "long").reshape((-1, 1, 2))
        cv2.polylines(temp, [points], False, 110, thickness=12, lineType=cv2.LINE_AA)
        cv2.polylines(mask, [points], False, 255, thickness=12, lineType=cv2.LINE_AA)
        blur_sigma = 1.1
    elif suite_name == "broken_ring_gap_small":
        expected_label = "rings"
        cv2.ellipse(temp, (160, 160), (58, 46), 8, 0, 360, 108, thickness=10, lineType=cv2.LINE_AA)
        cv2.ellipse(mask, (160, 160), (58, 46), 8, 0, 360, 255, thickness=10, lineType=cv2.LINE_AA)
        cv2.line(temp, (211, 128), (220, 122), 255, thickness=8, lineType=cv2.LINE_AA)
        cv2.line(mask, (211, 128), (220, 122), 0, thickness=8, lineType=cv2.LINE_AA)
        blur_sigma = 1.4
    elif suite_name == "broken_ring_gap_large":
        expected_label = "strands"
        cv2.ellipse(temp, (160, 160), (60, 50), 0, 40, 320, 110, thickness=10, lineType=cv2.LINE_AA)
        cv2.ellipse(mask, (160, 160), (60, 50), 0, 40, 320, 255, thickness=10, lineType=cv2.LINE_AA)
        blur_sigma = 1.1

    layer = cv2.GaussianBlur(temp, (0, 0), sigmaX=blur_sigma, sigmaY=blur_sigma)
    image = cv2.cvtColor(layer, cv2.COLOR_GRAY2BGR)
    instance = SyntheticInstance(
        id=1,
        label=expected_label,
        mask=mask,
        bbox=mask_to_bbox(mask),
        contour=_largest_contour(mask),
        layer=layer,
    )
    return image, instance, {"suite_name": suite_name, "expected_label": expected_label}


def generate_adversarial_suite(
    suite_name: str,
    outdir: str | Path,
    k: int = 5,
    seed: int = 42,
    width: int = 320,
    height: int = 320,
    config: DemoConfig | None = None,
) -> dict[str, object]:
    outdir_path = ensure_dir(outdir)
    demo_config = config or load_config()
    confusion: dict[str, int] = {}
    expected_label = ""

    for idx in range(k):
        image_id = f"{suite_name}_{idx:03d}"
        image, instance, meta = generate_adversarial_case(suite_name, seed=seed + idx, width=width, height=height)
        expected_label = str(meta["expected_label"])
        raw_path = outdir_path / f"{image_id}.png"
        overlay_path = outdir_path / f"{image_id}_overlay.png"
        json_path = outdir_path / f"{image_id}.json"
        cv2.imwrite(str(raw_path), image)
        _save_gt_overlay(image, [instance], overlay_path)
        _save_annotation_json(image_id, width, height, [instance], json_path)

        prediction = infer_image(raw_path, demo_config, save_debug_masks=False)
        predicted_label = str(prediction["instances"][0]["label"]) if prediction["instances"] else "none"
        confusion[predicted_label] = confusion.get(predicted_label, 0) + 1

    return {
        "suite_name": suite_name,
        "expected_label": expected_label,
        "count": k,
        "confusion": confusion,
    }
