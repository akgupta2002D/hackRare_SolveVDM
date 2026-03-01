from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, replace
from pathlib import Path

import cv2
import numpy as np

from .config import DemoConfig, load_config
from .infer import infer_image
from .synth import CLOSED_LOOP_SUITES, SyntheticInstance, generate_closed_loop_case
from .utils import ensure_dir, mask_to_contour
from .visualize import draw_instances_overlay


DEFAULT_SUITE_ORDER = (
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
CORE_LABELS = ("dots", "strands", "membranes", "rings")
PRESENTATION_BUCKETS = {
    "clean": {"true_ring_clean", "true_strand_thin", "membrane_cloud_faint", "mixed_distinct_scene"},
    "small_ring": {"small_ring_clean", "small_ring_overlap_strand"},
    "overlap": {"dense_scribble_merge", "crossing_strands_pocket_hole", "strand_bundle_near_touch", "small_ring_overlap_strand"},
}


def match_predictions_to_gt(
    gt_instances: list[dict[str, object]],
    pred_instances: list[dict[str, object]],
    iou_threshold: float = 0.3,
) -> list[dict[str, object]]:
    candidates: list[tuple[float, float, int, int]] = []
    for gt_idx, gt in enumerate(gt_instances):
        for pred_idx, pred in enumerate(pred_instances):
            bbox_iou_value = bbox_iou(gt["bbox"], pred["bbox"])
            if bbox_iou_value < iou_threshold:
                continue
            mask_iou_value = mask_iou(gt.get("mask"), pred.get("mask"))
            score = mask_iou_value if mask_iou_value > 0 else bbox_iou_value
            candidates.append((score, bbox_iou_value, gt_idx, pred_idx))

    matches: list[dict[str, object]] = []
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    for score, bbox_score, gt_idx, pred_idx in sorted(candidates, reverse=True):
        if gt_idx in used_gt or pred_idx in used_pred:
            continue
        used_gt.add(gt_idx)
        used_pred.add(pred_idx)
        matches.append(
            {
                "gt_index": gt_idx,
                "pred_index": pred_idx,
                "score": round(float(score), 4),
                "bbox_iou": round(float(bbox_score), 4),
            }
        )

    return matches


def run_closed_loop(
    outdir: str | Path,
    rounds: int = 5,
    seed: int = 42,
    n_per_suite: int = 50,
    apply_updates: bool = True,
    base_config: DemoConfig | None = None,
) -> dict[str, object]:
    outdir_path = ensure_dir(outdir)
    current_config = base_config or load_config()
    step_scale = 0.10
    no_improvement_rounds = 0
    best_score: float | None = None
    history: list[dict[str, object]] = []

    for round_index in range(rounds):
        round_dir = ensure_dir(outdir_path / f"round_{round_index:02d}")
        round_seed = seed + round_index * 1000
        evaluation = evaluate_closed_loop_round(
            outdir=round_dir,
            config=current_config,
            seed=round_seed,
            n_per_suite=n_per_suite,
        )

        round_result: dict[str, object] = {
            "round": round_index,
            "seed": round_seed,
            "score_before": evaluation["score"],
            "report_path": str(round_dir / "report.json"),
            "confusion_path": str(round_dir / "confusion.csv"),
            "confusion_matrix_path": str(round_dir / "confusion_matrix.png"),
            "presentation_metrics_path": str(round_dir / "presentation_metrics.json"),
            "config": serialize_config(current_config),
            "proposed_updates": [],
            "applied_updates": [],
            "accepted": False,
        }

        score_before = float(evaluation["score"])
        if best_score is None or score_before > best_score + 1e-9:
            best_score = score_before

        if not apply_updates:
            history.append(round_result)
            continue

        updates = propose_updates(evaluation["report"], current_config, step_scale=step_scale)
        round_result["proposed_updates"] = updates
        if not updates:
            history.append(round_result)
            no_improvement_rounds += 1
            if no_improvement_rounds >= 2:
                break
            continue

        candidate_config = apply_config_updates(current_config, updates)
        candidate_evaluation = evaluate_closed_loop_round(
            outdir=ensure_dir(round_dir / "candidate"),
            config=candidate_config,
            seed=round_seed,
            n_per_suite=n_per_suite,
        )
        score_after = float(candidate_evaluation["score"])
        round_result["score_after"] = score_after

        if score_after >= score_before:
            current_config = candidate_config
            round_result["applied_updates"] = updates
            round_result["accepted"] = True
            improvement = score_after - score_before
            no_improvement_rounds = no_improvement_rounds + 1 if improvement < 1e-3 else 0
            best_score = max(best_score or score_after, score_after)
        else:
            step_scale = max(0.05, step_scale * 0.5)
            no_improvement_rounds += 1

        history.append(round_result)
        with (round_dir / "round_summary.json").open("w", encoding="utf-8") as handle:
            json.dump(round_result, handle, indent=2)
        if no_improvement_rounds >= 2:
            break

    payload = {
        "outdir": str(outdir_path),
        "rounds_completed": len(history),
        "final_config": serialize_config(current_config),
        "history": history,
    }
    with (outdir_path / "closed_loop_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload


def evaluate_closed_loop_round(
    outdir: str | Path,
    config: DemoConfig,
    seed: int,
    n_per_suite: int,
) -> dict[str, object]:
    outdir_path = ensure_dir(outdir)
    records: list[dict[str, object]] = []
    confusion: dict[tuple[str, str], int] = {}

    for suite_index, suite_name in enumerate(DEFAULT_SUITE_ORDER):
        suite_dir = ensure_dir(outdir_path / suite_name)
        for sample_index in range(n_per_suite):
            case_seed = seed + suite_index * 100 + sample_index
            image, gt_instances, meta = generate_closed_loop_case(suite_name, seed=case_seed)
            image_id = f"{suite_name}_{sample_index:03d}"
            raw_path = suite_dir / f"{image_id}.png"
            gt_json_path = suite_dir / f"{image_id}.json"
            gt_overlay_path = suite_dir / f"{image_id}_overlay.png"
            cv2.imwrite(str(raw_path), image)
            save_ground_truth_case(image_id, image, gt_instances, gt_json_path, gt_overlay_path)

            result = infer_image(raw_path, config, save_debug_masks=True)
            pred_overlay = draw_instances_overlay(image.copy(), result["instances"], strategy="greedy", draw_leaders=False)
            cv2.imwrite(str(suite_dir / f"{image_id}_pred_overlay.png"), pred_overlay)

            gt_payload = [instance_to_payload(instance) for instance in gt_instances]
            pred_payload = [prediction_to_payload(instance) for instance in result["instances"]]
            matches = match_predictions_to_gt(gt_payload, pred_payload)
            used_gt = {match["gt_index"] for match in matches}
            used_pred = {match["pred_index"] for match in matches}

            for match in matches:
                gt_item = gt_payload[match["gt_index"]]
                pred_item = pred_payload[match["pred_index"]]
                confusion[(gt_item["label"], pred_item["label"])] = confusion.get((gt_item["label"], pred_item["label"]), 0) + 1

            for gt_idx, gt_item in enumerate(gt_payload):
                if gt_idx not in used_gt:
                    confusion[(gt_item["label"], "missed")] = confusion.get((gt_item["label"], "missed"), 0) + 1
            for pred_idx, pred_item in enumerate(pred_payload):
                if pred_idx not in used_pred:
                    confusion[("spurious", pred_item["label"])] = confusion.get(("spurious", pred_item["label"]), 0) + 1

            records.append(
                {
                    "suite_name": suite_name,
                    "image_id": image_id,
                    "meta": meta,
                    "ground_truth": gt_payload,
                    "predictions": pred_payload,
                    "matches": matches,
                }
            )

    report = analyze_records(records, config)
    report["seed"] = seed
    score = score_report(report)
    report["score"] = round(score, 4)
    confusion_summary = build_confusion_summary(confusion)
    presentation_metrics = build_presentation_metrics(records, confusion_summary)

    with (outdir_path / "report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    write_confusion_csv(confusion, outdir_path / "confusion.csv")
    with (outdir_path / "confusion_matrix.json").open("w", encoding="utf-8") as handle:
        json.dump(confusion_summary, handle, indent=2)
    with (outdir_path / "presentation_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(presentation_metrics, handle, indent=2)
    render_confusion_matrix_image(confusion_summary, outdir_path / "confusion_matrix.png")
    return {"report": report, "score": score}


def analyze_records(records: list[dict[str, object]], config: DemoConfig) -> dict[str, object]:
    strand_to_membrane_features: list[dict[str, float]] = []
    false_ring_features: list[dict[str, float]] = []
    merge_stats: list[dict[str, float]] = []
    counts = {
        "strand_targets": 0,
        "strand_to_membrane": 0,
        "ring_negative_targets": 0,
        "ring_false_positives": 0,
    }

    for record in records:
        suite_name = str(record["suite_name"])
        gt_items = record["ground_truth"]
        pred_items = record["predictions"]
        matches = record["matches"]
        matched_gt = {match["gt_index"] for match in matches}
        matched_pred = {match["pred_index"] for match in matches}

        if suite_name == "dense_scribble_merge":
            gt_count = len(gt_items)
            pred_count = len(pred_items)
            merge_stats.append(
                {
                    "gt_count": gt_count,
                    "pred_count": pred_count,
                    "merge_fraction": max(gt_count - pred_count, 0) / max(gt_count, 1),
                    "max_pred_area_ratio": max((float(item["features"]["area"]) / max(gt_count, 1) for item in pred_items), default=0.0),
                    "pred_hole_count_max": max((int(item["features"]["hole_count"]) for item in pred_items), default=0),
                }
            )

        for match in matches:
            gt_item = gt_items[match["gt_index"]]
            pred_item = pred_items[match["pred_index"]]
            gt_label = str(gt_item["label"])
            pred_label = str(pred_item["label"])
            if gt_label == "strands":
                counts["strand_targets"] += 1
                if pred_label == "membranes":
                    counts["strand_to_membrane"] += 1
                    strand_to_membrane_features.append(pred_item["features"])

            if suite_name in {"dense_scribble_merge", "crossing_strands_pocket_hole"} and gt_label != "rings":
                counts["ring_negative_targets"] += 1
                if pred_label == "rings":
                    counts["ring_false_positives"] += 1
                    false_ring_features.append(pred_item["features"])

        for pred_idx, pred_item in enumerate(pred_items):
            if pred_idx in matched_pred:
                continue
            if suite_name in {"dense_scribble_merge", "crossing_strands_pocket_hole"}:
                counts["ring_negative_targets"] += 1
                if str(pred_item["label"]) == "rings":
                    counts["ring_false_positives"] += 1
                    false_ring_features.append(pred_item["features"])

        for gt_idx, gt_item in enumerate(gt_items):
            if gt_idx in matched_gt:
                continue
            if gt_item["label"] == "strands":
                counts["strand_targets"] += 1

    strand_rate = counts["strand_to_membrane"] / max(counts["strand_targets"], 1)
    rings_fp_rate = counts["ring_false_positives"] / max(counts["ring_negative_targets"], 1)
    merge_rate = float(np.mean([item["merge_fraction"] for item in merge_stats])) if merge_stats else 0.0

    return {
        "metrics": {
            "strand_to_membrane_rate": round(strand_rate, 4),
            "rings_false_positive_rate": round(rings_fp_rate, 4),
            "merge_rate": round(merge_rate, 4),
        },
        "counts": counts,
        "analysis": {
            "strand_to_membrane_features": summarize_feature_group(strand_to_membrane_features),
            "false_ring_features": summarize_feature_group(false_ring_features),
            "merge_stats": summarize_numeric_group(merge_stats),
        },
        "config_snapshot": serialize_config(config),
    }


def build_confusion_summary(confusion: dict[tuple[str, str], int]) -> dict[str, object]:
    matrix_counts = {
        gt_label: {pred_label: int(confusion.get((gt_label, pred_label), 0)) for pred_label in CORE_LABELS}
        for gt_label in CORE_LABELS
    }
    row_totals = {
        gt_label: sum(matrix_counts[gt_label].values()) + int(confusion.get((gt_label, "missed"), 0))
        for gt_label in CORE_LABELS
    }
    normalized = {}
    precision_recall = {}
    for gt_label in CORE_LABELS:
        total = max(row_totals[gt_label], 1)
        normalized[gt_label] = {
            pred_label: round(matrix_counts[gt_label][pred_label] / total, 4) for pred_label in CORE_LABELS
        }
        tp = matrix_counts[gt_label][gt_label]
        fp = sum(matrix_counts[other][gt_label] for other in CORE_LABELS if other != gt_label) + int(confusion.get(("spurious", gt_label), 0))
        fn = sum(matrix_counts[gt_label][other] for other in CORE_LABELS if other != gt_label) + int(confusion.get((gt_label, "missed"), 0))
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        precision_recall[gt_label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "support": row_totals[gt_label],
        }

    overall_correct = sum(matrix_counts[label][label] for label in CORE_LABELS)
    overall_total = sum(row_totals.values())
    return {
        "labels": list(CORE_LABELS),
        "counts": matrix_counts,
        "normalized": normalized,
        "missed": {gt_label: int(confusion.get((gt_label, "missed"), 0)) for gt_label in CORE_LABELS},
        "spurious": {pred_label: int(confusion.get(("spurious", pred_label), 0)) for pred_label in CORE_LABELS},
        "precision_recall": precision_recall,
        "overall_accuracy": round(overall_correct / max(overall_total, 1), 4),
        "overall_support": overall_total,
    }


def build_presentation_metrics(records: list[dict[str, object]], confusion_summary: dict[str, object]) -> dict[str, object]:
    bucket_stats: dict[str, dict[str, int]] = {
        bucket: {"matched_correct": 0, "matched_total": 0, "gt_total": 0, "pred_total": 0, "ring_gt": 0, "ring_tp": 0}
        for bucket in PRESENTATION_BUCKETS
    }
    for record in records:
        suite_name = str(record["suite_name"])
        active_buckets = [bucket for bucket, suites in PRESENTATION_BUCKETS.items() if suite_name in suites]
        gt_items = record["ground_truth"]
        pred_items = record["predictions"]
        for bucket in active_buckets:
            bucket_stats[bucket]["gt_total"] += len(gt_items)
            bucket_stats[bucket]["pred_total"] += len(pred_items)
            bucket_stats[bucket]["ring_gt"] += sum(1 for item in gt_items if item["label"] == "rings")
        for match in record["matches"]:
            gt_item = gt_items[match["gt_index"]]
            pred_item = pred_items[match["pred_index"]]
            for bucket in active_buckets:
                bucket_stats[bucket]["matched_total"] += 1
                if gt_item["label"] == pred_item["label"]:
                    bucket_stats[bucket]["matched_correct"] += 1
                if gt_item["label"] == "rings" and pred_item["label"] == "rings":
                    bucket_stats[bucket]["ring_tp"] += 1

    output = {
        "overall_accuracy": confusion_summary["overall_accuracy"],
        "per_class": confusion_summary["precision_recall"],
        "buckets": {},
    }
    for bucket, stats in bucket_stats.items():
        output["buckets"][bucket] = {
            "matched_accuracy": round(stats["matched_correct"] / max(stats["matched_total"], 1), 4),
            "detection_ratio": round(stats["pred_total"] / max(stats["gt_total"], 1), 4),
            "ring_recall": round(stats["ring_tp"] / max(stats["ring_gt"], 1), 4) if stats["ring_gt"] else None,
        }
    return output


def propose_updates(report: dict[str, object], current_config: DemoConfig, step_scale: float = 0.10) -> list[dict[str, object]]:
    metrics = report["metrics"]
    analysis = report["analysis"]
    updates: list[dict[str, object]] = []

    strand_rate = float(metrics["strand_to_membrane_rate"])
    if strand_rate >= 0.12:
        strand_summary = analysis["strand_to_membrane_features"]
        if (
            strand_summary.get("bbox_aspect_ratio_mean", 0.0) >= 2.5
            and strand_summary.get("skeleton_length_mean", 0.0) >= current_config.rules.strand_skel_min
            and strand_summary.get("thickness_est_mean", 0.0) > current_config.rules.strand_thick_max * 0.95
        ):
            new_value = bounded_scale(current_config.rules.strand_thick_max, 1.0 + step_scale, increase=True)
            updates.append(
                make_update(
                    scope="rules",
                    field="strand_thick_max",
                    old=current_config.rules.strand_thick_max,
                    new=new_value,
                    reason="thick strands are falling into membrane fallback despite long skeletons and high aspect ratio",
                )
            )
        elif strand_summary.get("skeleton_length_mean", current_config.rules.strand_skel_min) < current_config.rules.strand_skel_min:
            new_value = bounded_scale(current_config.rules.strand_skel_min, 1.0 - step_scale, increase=False)
            updates.append(
                make_update(
                    scope="rules",
                    field="strand_skel_min",
                    old=current_config.rules.strand_skel_min,
                    new=new_value,
                    reason="strand misses have skeleton lengths slightly below the current strand minimum",
                )
            )

    merge_rate = float(metrics["merge_rate"])
    if merge_rate >= 0.18 and len(updates) < 2:
        if current_config.preprocess.morph_close_size > 1:
            updates.append(
                make_update(
                    scope="preprocess",
                    field="morph_close_size",
                    old=current_config.preprocess.morph_close_size,
                    new=current_config.preprocess.morph_close_size - 1,
                    reason="dense scribbles are merging into mega-components after close morphology",
                )
            )
        elif current_config.preprocess.raw_mask_gate_coverage_max > 0.002:
            new_value = max(0.002, round(current_config.preprocess.raw_mask_gate_coverage_max * 0.5, 6))
            updates.append(
                make_update(
                    scope="preprocess",
                    field="raw_mask_gate_coverage_max",
                    old=current_config.preprocess.raw_mask_gate_coverage_max,
                    new=new_value,
                    reason="raw mask support is still bridging dense scribbles; gate it to sparse adaptive detections only",
                )
            )

    ring_fp_rate = float(metrics["rings_false_positive_rate"])
    if ring_fp_rate >= 0.08 and len(updates) < 2:
        ring_summary = analysis["false_ring_features"]
        if ring_summary.get("skeleton_length_mean", 0.0) >= current_config.rules.ring_skel_max * 0.7:
            new_value = bounded_scale(current_config.rules.ring_skel_max, 1.0 - step_scale, increase=False)
            updates.append(
                make_update(
                    scope="rules",
                    field="ring_skel_max",
                    old=current_config.rules.ring_skel_max,
                    new=new_value,
                    reason="false rings are long scribbly components; tighten the ring skeleton-length guard",
                )
            )
        else:
            new_value = bounded_scale(current_config.rules.ring_min_hole_area_ratio, 1.0 + step_scale, increase=True)
            updates.append(
                make_update(
                    scope="rules",
                    field="ring_min_hole_area_ratio",
                    old=current_config.rules.ring_min_hole_area_ratio,
                    new=new_value,
                    reason="false rings have small pocket holes; require a larger dominant hole",
                )
            )

    return updates[:2]


def apply_config_updates(config: DemoConfig, updates: list[dict[str, object]]) -> DemoConfig:
    preprocess = config.preprocess
    rules = config.rules
    for update in updates:
        if update["scope"] == "preprocess":
            preprocess = replace(preprocess, **{update["field"]: update["new"]})
        elif update["scope"] == "rules":
            rules = replace(rules, **{update["field"]: update["new"]})
    return replace(config, preprocess=preprocess, rules=rules)


def score_report(report: dict[str, object]) -> float:
    metrics = report["metrics"]
    return (
        0.6 * (1.0 - float(metrics["strand_to_membrane_rate"]))
        + 0.4 * (1.0 - float(metrics["rings_false_positive_rate"]))
        - 0.3 * float(metrics["merge_rate"])
    )


def save_ground_truth_case(
    image_id: str,
    image: np.ndarray,
    instances: list[SyntheticInstance],
    json_path: Path,
    overlay_path: Path,
) -> None:
    payload_instances = [instance_to_payload(instance) for instance in instances]
    overlay = draw_instances_overlay(image.copy(), payload_instances, strategy="greedy", draw_leaders=False)
    cv2.imwrite(str(overlay_path), overlay)
    payload = {
        "image_id": image_id,
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "instances": [
            {
                "id": instance["id"],
                "label": instance["label"],
                "bbox": instance["bbox"],
                "contour": instance["contour"],
            }
            for instance in payload_instances
        ],
    }
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def instance_to_payload(instance: SyntheticInstance) -> dict[str, object]:
    return {
        "id": instance.id,
        "label": instance.label,
        "bbox": list(instance.bbox),
        "mask": instance.mask,
        "contour": instance.contour or mask_to_contour(instance.mask),
        "features": {"area": int(np.count_nonzero(instance.mask))},
    }


def prediction_to_payload(instance: dict[str, object]) -> dict[str, object]:
    return {
        "id": int(instance["id"]),
        "label": str(instance["label"]),
        "bbox": [int(v) for v in instance["bbox"]],
        "mask": instance.get("mask"),
        "contour": instance.get("contour", []),
        "features": dict(instance.get("features", {})),
    }


def bbox_iou(box_a: list[int] | tuple[int, int, int, int], box_b: list[int] | tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    inter_w = max(0, min(ax2, bx2) - max(ax, bx))
    inter_h = max(0, min(ay2, by2) - max(ay, by))
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    return float(inter / union) if union > 0 else 0.0


def mask_iou(mask_a: object, mask_b: object) -> float:
    if mask_a is None or mask_b is None:
        return 0.0
    mask_a_u8 = np.asarray(mask_a, dtype=bool)
    mask_b_u8 = np.asarray(mask_b, dtype=bool)
    inter = np.logical_and(mask_a_u8, mask_b_u8).sum()
    union = np.logical_or(mask_a_u8, mask_b_u8).sum()
    return float(inter / union) if union > 0 else 0.0


def summarize_feature_group(items: list[dict[str, object]]) -> dict[str, float]:
    if not items:
        return {}
    keys = ("thickness_est", "skeleton_length", "circularity", "bbox_aspect_ratio", "solidity", "hole_count", "max_hole_area_ratio")
    summary: dict[str, float] = {}
    for key in keys:
        values = [float(item[key]) for item in items if key in item]
        if values:
            summary[f"{key}_mean"] = round(float(np.mean(values)), 4)
            summary[f"{key}_median"] = round(float(np.median(values)), 4)
    summary["count"] = len(items)
    return summary


def summarize_numeric_group(items: list[dict[str, float]]) -> dict[str, float]:
    if not items:
        return {}
    keys = items[0].keys()
    summary: dict[str, float] = {"count": len(items)}
    for key in keys:
        values = [float(item[key]) for item in items]
        summary[f"{key}_mean"] = round(float(np.mean(values)), 4)
        summary[f"{key}_median"] = round(float(np.median(values)), 4)
    return summary


def write_confusion_csv(confusion: dict[tuple[str, str], int], path: Path) -> None:
    labels = sorted({key[0] for key in confusion} | {key[1] for key in confusion})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["gt_or_status", *labels])
        for row_label in labels:
            row = [row_label]
            for col_label in labels:
                row.append(confusion.get((row_label, col_label), 0))
            writer.writerow(row)


def render_confusion_matrix_image(confusion_summary: dict[str, object], path: Path) -> None:
    labels = list(confusion_summary["labels"])
    counts = confusion_summary["counts"]
    normalized = confusion_summary["normalized"]
    cell_w = 124
    cell_h = 58
    left_w = 160
    top_h = 100
    width = left_w + cell_w * len(labels)
    height = top_h + cell_h * len(labels)
    image = np.full((height, width, 3), 255, dtype=np.uint8)

    cv2.putText(image, "Confusion Matrix", (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(image, "GT rows vs Pred columns", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1, cv2.LINE_AA)

    for col_idx, label in enumerate(labels):
        x0 = left_w + col_idx * cell_w
        cv2.putText(image, label, (x0 + 12, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)

    for row_idx, row_label in enumerate(labels):
        y0 = top_h + row_idx * cell_h
        cv2.putText(image, row_label, (18, y0 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
        for col_idx, col_label in enumerate(labels):
            x0 = left_w + col_idx * cell_w
            value = float(normalized[row_label][col_label])
            count = int(counts[row_label][col_label])
            color = _matrix_cell_color(value)
            cv2.rectangle(image, (x0, y0), (x0 + cell_w - 2, y0 + cell_h - 2), color, -1)
            cv2.rectangle(image, (x0, y0), (x0 + cell_w - 2, y0 + cell_h - 2), (200, 200, 200), 1)
            cv2.putText(image, str(count), (x0 + 12, y0 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (20, 20, 20), 2, cv2.LINE_AA)
            cv2.putText(image, f"{value:.2f}", (x0 + 12, y0 + 46), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (45, 45, 45), 1, cv2.LINE_AA)

    cv2.imwrite(str(path), image)


def _matrix_cell_color(value: float) -> tuple[int, int, int]:
    low = np.array([235, 245, 255], dtype=np.float32)
    high = np.array([80, 170, 110], dtype=np.float32)
    color = low + (high - low) * float(np.clip(value, 0.0, 1.0))
    return int(color[0]), int(color[1]), int(color[2])


def serialize_config(config: DemoConfig) -> dict[str, object]:
    return {
        "preprocess": asdict(config.preprocess),
        "segment": asdict(config.segment),
        "rules": asdict(config.rules),
    }


def make_update(scope: str, field: str, old: float | int, new: float | int, reason: str) -> dict[str, object]:
    return {
        "scope": scope,
        "field": field,
        "old": old,
        "new": new,
        "reason": reason,
    }


def bounded_scale(value: float, factor: float, increase: bool) -> float:
    lower_factor = 0.8 if increase else factor
    upper_factor = factor if increase else 1.2
    scaled = value * factor
    scaled = max(value * lower_factor, min(value * upper_factor, scaled))
    return round(float(scaled), 4)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic closed-loop tuning for the floater demo.")
    parser.add_argument("--outdir", required=True, help="Directory for round artifacts.")
    parser.add_argument("--rounds", type=int, default=5, help="Maximum number of tuning rounds.")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed.")
    parser.add_argument("--n", type=int, default=50, help="Samples per suite per round.")
    parser.add_argument("--apply-updates", action="store_true", help="Apply bounded config updates between rounds.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run_closed_loop(
        outdir=args.outdir,
        rounds=args.rounds,
        seed=args.seed,
        n_per_suite=args.n,
        apply_updates=args.apply_updates,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
