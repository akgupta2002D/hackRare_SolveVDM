from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .utils import ensure_dir, stable_color


@dataclass(frozen=True)
class LabelPlacement:
    instance_id: int
    text: str
    anchor_point: tuple[int, int]
    text_origin: tuple[int, int]
    rect: tuple[int, int, int, int]
    color: tuple[int, int, int]
    requires_leader: bool


def save_overlay(result: dict[str, object], outdir: str | Path) -> Path:
    outdir_path = ensure_dir(outdir)
    image = draw_instances_overlay(np.asarray(result["_render"]["original_bgr"]).copy(), result["instances"], strategy="greedy")

    overlay_path = outdir_path / "overlay.png"
    cv2.imwrite(str(overlay_path), image)
    return overlay_path


def draw_instances_overlay(
    image: np.ndarray,
    instances: list[dict[str, object]],
    predictions: list[dict[str, object]] | None = None,
    strategy: str = "greedy",
    draw_leaders: bool = False,
) -> np.ndarray:
    overlay = image.copy()
    placements = layout_instance_labels(overlay.shape[:2], instances, predictions=predictions, strategy=strategy)

    for instance in instances:
        mask = instance.get("mask")
        color = stable_color(instance["id"])
        if mask is not None:
            contours, _ = cv2.findContours(np.asarray(mask, dtype=np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, color, 2)
        x, y, w, h = [int(v) for v in instance["bbox"]]
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 1)

    for placement in placements:
        if draw_leaders and placement.requires_leader:
            leader_end = _leader_end_point(placement.rect, placement.anchor_point)
            cv2.line(overlay, placement.anchor_point, leader_end, placement.color, 1, cv2.LINE_AA)
        _draw_text_box(overlay, placement.text, placement.text_origin, placement.color)

    return overlay


def layout_instance_labels(
    image_shape: tuple[int, int],
    instances: list[dict[str, object]],
    predictions: list[dict[str, object]] | None = None,
    strategy: str = "greedy",
) -> list[LabelPlacement]:
    height, width = image_shape
    entries = []
    for idx, instance in enumerate(instances):
        label = str(instance.get("label", "unknown"))
        confidence = float(instance.get("confidence", 0.0))
        if predictions is not None and idx < len(predictions):
            label = str(predictions[idx].get("label", label))
            confidence = float(predictions[idx].get("confidence", confidence))
        text = f'{instance["id"]}:{label} {confidence:.2f}'
        x, y, w, h = [int(v) for v in instance["bbox"]]
        entries.append(
            {
                "id": int(instance["id"]),
                "bbox": (x, y, w, h),
                "anchor": (x + w // 2, y + h // 2),
                "text": text,
                "color": stable_color(instance["id"]),
            }
        )

    greedy = _layout_labels_greedy(width, height, entries)
    if strategy == "greedy":
        return greedy
    if strategy == "relax":
        return _layout_labels_relax(width, height, entries, greedy)
    raise ValueError(f"Unknown overlay strategy: {strategy}")


def _layout_labels_greedy(width: int, height: int, entries: list[dict[str, object]]) -> list[LabelPlacement]:
    occupied: list[tuple[int, int, int, int]] = []
    placements: list[LabelPlacement] = []
    sorted_entries = sorted(entries, key=lambda item: (item["bbox"][1], item["bbox"][0], item["id"]))

    for entry in sorted_entries:
        text_rects = _candidate_label_rects(width, height, entry["bbox"], entry["text"])
        best = None
        best_penalty = float("inf")

        for candidate in text_rects:
            rect = candidate["rect"]
            penalty = _rect_overlap_area(rect, occupied) * 5.0
            penalty += _rect_overlap_area(rect, [_expand_rect(entry["bbox"], 4)]) * 2.5
            penalty += float(candidate["distance"]) * 0.02

            if penalty == 0:
                best = candidate
                break
            if penalty < best_penalty:
                best = candidate
                best_penalty = penalty

        assert best is not None
        placement = LabelPlacement(
            instance_id=entry["id"],
            text=entry["text"],
            anchor_point=entry["anchor"],
            text_origin=best["origin"],
            rect=best["rect"],
            color=entry["color"],
            requires_leader=best["requires_leader"],
        )
        placements.append(placement)
        occupied.append(placement.rect)

    return placements


def _layout_labels_relax(
    width: int,
    height: int,
    entries: list[dict[str, object]],
    initial: list[LabelPlacement],
) -> list[LabelPlacement]:
    states: list[dict[str, object]] = []
    for placement, entry in zip(initial, sorted(entries, key=lambda item: (item["bbox"][1], item["bbox"][0], item["id"]))):
        x0, y0, x1, y1 = placement.rect
        states.append(
            {
                "entry": entry,
                "center": np.array([(x0 + x1) / 2.0, (y0 + y1) / 2.0], dtype=np.float32),
                "size": np.array([x1 - x0, y1 - y0], dtype=np.float32),
                "target": np.array([(x0 + x1) / 2.0, (y0 + y1) / 2.0], dtype=np.float32),
            }
        )

    for _ in range(80):
        for idx, state in enumerate(states):
            force = np.zeros(2, dtype=np.float32)
            rect = _center_size_to_rect(state["center"], state["size"])
            bbox_rect = _expand_rect(state["entry"]["bbox"], 6)

            if _rect_intersection_area(rect, bbox_rect) > 0:
                force += _repel_from_rect(rect, bbox_rect) * 1.1

            for other_idx, other_state in enumerate(states):
                if idx == other_idx:
                    continue
                other_rect = _center_size_to_rect(other_state["center"], other_state["size"])
                if _rect_intersection_area(rect, other_rect) > 0:
                    force += _repel_from_rect(rect, other_rect) * 1.25

            force += (state["target"] - state["center"]) * 0.08

            next_center = state["center"] + force
            next_center[0] = np.clip(next_center[0], state["size"][0] / 2 + 2, width - state["size"][0] / 2 - 2)
            next_center[1] = np.clip(next_center[1], state["size"][1] / 2 + 2, height - state["size"][1] / 2 - 2)
            state["center"] = next_center

    placements: list[LabelPlacement] = []
    greedy_score = _layout_score(initial, entries)
    relaxed_score = 0.0
    relaxed_candidates: list[LabelPlacement] = []
    for state in states:
        rect = _center_size_to_rect(state["center"], state["size"])
        origin = (rect[0] + 3, rect[3] - 3)
        relaxed_candidates.append(
            LabelPlacement(
                instance_id=state["entry"]["id"],
                text=state["entry"]["text"],
                anchor_point=state["entry"]["anchor"],
                text_origin=origin,
                rect=rect,
                color=state["entry"]["color"],
                requires_leader=True,
            )
        )
    relaxed_score = _layout_score(relaxed_candidates, entries)
    placements = relaxed_candidates if relaxed_score <= greedy_score else initial
    return placements


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


def _draw_text_box(image: np.ndarray, text: str, origin: tuple[int, int], color: tuple[int, int, int]) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (width, height), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = origin
    cv2.rectangle(image, (x - 3, y - height - baseline - 3), (x + width + 3, y + 3), (255, 255, 255), -1)
    cv2.putText(image, text, (x, y), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(image, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def _candidate_label_rects(width: int, height: int, bbox: tuple[int, int, int, int], text: str) -> list[dict[str, object]]:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
    box_width = text_width + 6
    box_height = text_height + baseline + 6
    x, y, w, h = bbox
    candidates = [
        (x, y - 6, False),
        (x + w - box_width, y - 6, False),
        (x, y + h + box_height, False),
        (x + w - box_width, y + h + box_height, False),
        (x + w + 8, y + text_height + 4, True),
        (x - box_width - 8, y + text_height + 4, True),
        (x + (w - box_width) // 2, y - 10, False),
        (x + (w - box_width) // 2, y + h + box_height + 4, False),
    ]
    output = []
    for candidate_x, baseline_y, leader in candidates:
        origin_x = int(np.clip(candidate_x + 3, 3, max(width - text_width - 3, 3)))
        origin_y = int(np.clip(baseline_y, text_height + baseline + 3, max(height - 3, text_height + baseline + 3)))
        rect = (
            origin_x - 3,
            origin_y - text_height - baseline - 3,
            origin_x + text_width + 3,
            origin_y + 3,
        )
        distance = abs((origin_x + text_width // 2) - (x + w // 2)) + abs(origin_y - (y + h // 2))
        output.append(
            {
                "origin": (origin_x, origin_y),
                "rect": rect,
                "distance": distance,
                "requires_leader": leader or not _rects_adjacent(rect, bbox, tolerance=6),
            }
        )
    return output


def _layout_score(placements: list[LabelPlacement], entries: list[dict[str, object]]) -> float:
    score = 0.0
    rects = [placement.rect for placement in placements]
    bbox_map = {entry["id"]: entry["bbox"] for entry in entries}
    for idx, placement in enumerate(placements):
        score += _rect_overlap_area(placement.rect, rects[:idx]) * 5.0
        score += _rect_overlap_area(placement.rect, [_expand_rect(bbox_map[placement.instance_id], 4)]) * 2.5
        score += 0.02 * (
            abs(placement.text_origin[0] - placement.anchor_point[0])
            + abs(placement.text_origin[1] - placement.anchor_point[1])
        )
    return score


def _expand_rect(rect: tuple[int, int, int, int], margin: int) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    return (x - margin, y - margin, x + w + margin, y + h + margin)


def _rect_overlap_area(rect: tuple[int, int, int, int], others: list[tuple[int, int, int, int]]) -> int:
    return sum(_rect_intersection_area(rect, other) for other in others)


def _rect_intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    ax0, ay0, ax1, ay1 = _rect_to_corners(a)
    bx0, by0, bx1, by1 = _rect_to_corners(b)
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0
    return int((ix1 - ix0) * (iy1 - iy0))


def _rect_to_corners(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if rect[2] >= rect[0] and rect[3] >= rect[1] and (rect[2] - rect[0] > 0 or rect[3] - rect[1] > 0):
        return rect
    x, y, w, h = rect
    return (x, y, x + w, y + h)


def _rects_adjacent(label_rect: tuple[int, int, int, int], bbox: tuple[int, int, int, int], tolerance: int) -> bool:
    bx0, by0, bx1, by1 = _expand_rect(bbox, tolerance)
    return _rect_intersection_area(label_rect, (bx0, by0, bx1, by1)) > 0


def _leader_end_point(rect: tuple[int, int, int, int], anchor: tuple[int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = rect
    cx = int(np.clip(anchor[0], x0, x1))
    cy = int(np.clip(anchor[1], y0, y1))
    distances = {
        (cx, y0): abs(anchor[1] - y0),
        (cx, y1): abs(anchor[1] - y1),
        (x0, cy): abs(anchor[0] - x0),
        (x1, cy): abs(anchor[0] - x1),
    }
    return min(distances, key=distances.get)


def _center_size_to_rect(center: np.ndarray, size: np.ndarray) -> tuple[int, int, int, int]:
    half_w = size[0] / 2.0
    half_h = size[1] / 2.0
    x0 = int(round(center[0] - half_w))
    y0 = int(round(center[1] - half_h))
    x1 = int(round(center[0] + half_w))
    y1 = int(round(center[1] + half_h))
    return (x0, y0, x1, y1)


def _repel_from_rect(rect: tuple[int, int, int, int], other: tuple[int, int, int, int]) -> np.ndarray:
    rx0, ry0, rx1, ry1 = rect
    ox0, oy0, ox1, oy1 = _rect_to_corners(other)
    rcx = (rx0 + rx1) / 2.0
    rcy = (ry0 + ry1) / 2.0
    ocx = (ox0 + ox1) / 2.0
    ocy = (oy0 + oy1) / 2.0
    delta = np.array([rcx - ocx, rcy - ocy], dtype=np.float32)
    if np.allclose(delta, 0):
        delta = np.array([1.0, -1.0], dtype=np.float32)
    norm = float(np.linalg.norm(delta))
    overlap_x = max(0, min(rx1, ox1) - max(rx0, ox0))
    overlap_y = max(0, min(ry1, oy1) - max(ry0, oy0))
    magnitude = max(overlap_x, overlap_y, 1) * 0.35
    return delta / max(norm, 1e-6) * magnitude
