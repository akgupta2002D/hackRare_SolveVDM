from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from .config import DemoConfig, load_config
from .infer import infer_image
from .synth import SyntheticInstance, generate_closed_loop_case
from .utils import ensure_dir, mask_to_contour
from .visualize import draw_instances_overlay


CORE_LABELS = ("dots", "strands", "membranes", "rings")
BALANCED_BENCHMARK_SUITES = {
    "dots": "true_dot_clean",
    "strands": "thick_strand_long",
    "membranes": "membrane_cloud_faint",
    "rings": "small_ring_clean",
}
STRESS_SUITES = {
    "overlap_strands": "strand_bundle_near_touch",
    "small_ring_overlap": "small_ring_overlap_strand",
}


def run_closed_loop(
    outdir: str | Path,
    rounds: int = 1,
    seed: int = 42,
    n_per_suite: int = 100,
    base_config: DemoConfig | None = None,
) -> dict[str, object]:
    outdir_path = ensure_dir(outdir)
    config = base_config or load_config()
    history: list[dict[str, object]] = []

    for round_index in range(rounds):
        round_dir = ensure_dir(outdir_path / f"round_{round_index:02d}")
        round_seed = seed + round_index * 1000
        evaluation = evaluate_benchmark_round(
            outdir=round_dir,
            config=config,
            seed=round_seed,
            n_per_suite=n_per_suite,
        )
        history.append(
            {
                "round": round_index,
                "seed": round_seed,
                "report_path": str(round_dir / "report.json"),
                "confusion_path": str(round_dir / "confusion.csv"),
                "confusion_row_normalized_path": str(round_dir / "confusion_row_normalized.csv"),
                "confusion_matrix_path": str(round_dir / "confusion_matrix.png"),
                "presentation_metrics_path": str(round_dir / "presentation_metrics.json"),
                "stress_metrics_path": str(round_dir / "stress_metrics.json"),
                "overall_accuracy": evaluation["presentation_metrics"]["overall_accuracy"],
                "balanced_support_per_class": n_per_suite,
            }
        )

    payload = {
        "outdir": str(outdir_path),
        "rounds_completed": len(history),
        "benchmark_type": "balanced_realistic_demo",
        "balanced_support_per_class": n_per_suite,
        "note": "Legacy auto-tuning was removed. This benchmark is a harder balanced synthetic evaluation with separate overlap stress metrics.",
        "config": serialize_config(config),
        "history": history,
    }

    with (outdir_path / "closed_loop_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload


def evaluate_benchmark_round(
    outdir: str | Path,
    config: DemoConfig,
    seed: int,
    n_per_suite: int,
) -> dict[str, object]:
    outdir_path = ensure_dir(outdir)
    records: list[dict[str, object]] = []
    confusion: dict[tuple[str, str], int] = {}

    for label_index, (label, suite_name) in enumerate(BALANCED_BENCHMARK_SUITES.items()):
        suite_dir = ensure_dir(outdir_path / suite_name)
        for sample_index in range(n_per_suite):
            case_seed = seed + label_index * 1000 + sample_index
            image, gt_instances, meta = generate_closed_loop_case(suite_name, seed=case_seed)
            image_id = f"{suite_name}_{sample_index:03d}"
            raw_path = suite_dir / f"{image_id}.png"
            gt_json_path = suite_dir / f"{image_id}.json"
            gt_overlay_path = suite_dir / f"{image_id}_overlay.png"
            pred_overlay_path = suite_dir / f"{image_id}_pred_overlay.png"

            cv2.imwrite(str(raw_path), image)
            save_ground_truth_case(image_id, image, gt_instances, gt_json_path, gt_overlay_path)

            result = infer_image(raw_path, config, save_debug_masks=True)
            pred_overlay = draw_instances_overlay(image.copy(), result["instances"], strategy="greedy", draw_leaders=False)
            cv2.imwrite(str(pred_overlay_path), pred_overlay)

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
                    "target_label": label,
                    "image_id": image_id,
                    "meta": meta,
                    "ground_truth": gt_payload,
                    "predictions": pred_payload,
                    "matches": matches,
                }
            )

    confusion_summary = build_confusion_summary(confusion)
    stress_metrics = evaluate_stress_suites(outdir_path, config, seed, n_per_suite)
    presentation_metrics = build_presentation_metrics(records, confusion_summary, stress_metrics, n_per_suite)
    report = {
        "seed": seed,
        "benchmark_type": "balanced_realistic_demo",
        "suite_map": BALANCED_BENCHMARK_SUITES,
        "stress_suite_map": STRESS_SUITES,
        "balanced_support_per_class": n_per_suite,
        "total_images": len(records),
        "total_gt_instances": int(sum(confusion_summary["row_support"].values())),
        "overall_accuracy": confusion_summary["overall_accuracy"],
        "config": serialize_config(config),
    }

    with (outdir_path / "report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    with (outdir_path / "confusion_matrix.json").open("w", encoding="utf-8") as handle:
        json.dump(confusion_summary, handle, indent=2)
    with (outdir_path / "presentation_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(presentation_metrics, handle, indent=2)
    with (outdir_path / "stress_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(stress_metrics, handle, indent=2)

    write_confusion_csv(confusion_summary, outdir_path / "confusion.csv")
    write_confusion_row_normalized_csv(confusion_summary, outdir_path / "confusion_row_normalized.csv")
    render_confusion_matrix_image(confusion_summary, outdir_path / "confusion_matrix.png")
    return {
        "report": report,
        "confusion_summary": confusion_summary,
        "presentation_metrics": presentation_metrics,
        "stress_metrics": stress_metrics,
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


def build_confusion_summary(confusion: dict[tuple[str, str], int]) -> dict[str, object]:
    counts = {
        gt_label: {pred_label: int(confusion.get((gt_label, pred_label), 0)) for pred_label in CORE_LABELS}
        for gt_label in CORE_LABELS
    }
    missed = {gt_label: int(confusion.get((gt_label, "missed"), 0)) for gt_label in CORE_LABELS}
    spurious = {pred_label: int(confusion.get(("spurious", pred_label), 0)) for pred_label in CORE_LABELS}
    row_support = {gt_label: sum(counts[gt_label].values()) + missed[gt_label] for gt_label in CORE_LABELS}

    normalized = {}
    precision_recall = {}
    for gt_label in CORE_LABELS:
        support = max(row_support[gt_label], 1)
        normalized[gt_label] = {
            pred_label: round(counts[gt_label][pred_label] / support, 4) for pred_label in CORE_LABELS
        }
        tp = counts[gt_label][gt_label]
        fp = sum(counts[other][gt_label] for other in CORE_LABELS if other != gt_label) + spurious[gt_label]
        fn = sum(counts[gt_label][other] for other in CORE_LABELS if other != gt_label) + missed[gt_label]
        precision_recall[gt_label] = {
            "precision": round(tp / max(tp + fp, 1), 4),
            "recall": round(tp / max(tp + fn, 1), 4),
            "support": row_support[gt_label],
        }

    overall_correct = sum(counts[label][label] for label in CORE_LABELS)
    overall_support = sum(row_support.values())
    return {
        "labels": list(CORE_LABELS),
        "counts": counts,
        "normalized": normalized,
        "missed": missed,
        "spurious": spurious,
        "row_support": row_support,
        "overall_accuracy": round(overall_correct / max(overall_support, 1), 4),
        "overall_support": overall_support,
        "precision_recall": precision_recall,
    }


def build_presentation_metrics(
    records: list[dict[str, object]],
    confusion_summary: dict[str, object],
    stress_metrics: dict[str, object],
    balanced_support_per_class: int,
) -> dict[str, object]:
    return {
        "benchmark_type": "balanced_realistic_demo",
        "overall_accuracy": confusion_summary["overall_accuracy"],
        "total_images": len(records),
        "total_gt_instances": confusion_summary["overall_support"],
        "balanced_support_per_class": balanced_support_per_class,
        "per_class": confusion_summary["precision_recall"],
        "row_support": confusion_summary["row_support"],
        "stress_metrics": stress_metrics,
        "note": "Confusion matrix is row-normalized. It reflects a harder synthetic benchmark, not real-world clinical accuracy.",
    }


def evaluate_stress_suites(
    outdir: Path,
    config: DemoConfig,
    seed: int,
    n_per_suite: int,
) -> dict[str, object]:
    metrics: dict[str, object] = {}
    suite_base = ensure_dir(outdir / "_stress")

    overlap_correct = 0
    overlap_matches = 0
    overlap_gt = 0
    overlap_pred = 0
    for sample_index in range(n_per_suite):
        image, gt_instances, _ = generate_closed_loop_case(STRESS_SUITES["overlap_strands"], seed=seed + 4000 + sample_index)
        raw_path = suite_base / f"overlap_strands_{sample_index:03d}.png"
        cv2.imwrite(str(raw_path), image)
        result = infer_image(raw_path, config, save_debug_masks=True)
        gt_payload = [instance_to_payload(instance) for instance in gt_instances]
        pred_payload = [prediction_to_payload(instance) for instance in result["instances"]]
        matches = match_predictions_to_gt(gt_payload, pred_payload)
        overlap_gt += len(gt_payload)
        overlap_pred += len(pred_payload)
        overlap_matches += len(matches)
        for match in matches:
            if gt_payload[match["gt_index"]]["label"] == pred_payload[match["pred_index"]]["label"]:
                overlap_correct += 1

    ring_correct = 0
    ring_total = 0
    for sample_index in range(n_per_suite):
        image, gt_instances, _ = generate_closed_loop_case(STRESS_SUITES["small_ring_overlap"], seed=seed + 5000 + sample_index)
        raw_path = suite_base / f"small_ring_overlap_{sample_index:03d}.png"
        cv2.imwrite(str(raw_path), image)
        result = infer_image(raw_path, config, save_debug_masks=True)
        gt_payload = [instance_to_payload(instance) for instance in gt_instances]
        pred_payload = [prediction_to_payload(instance) for instance in result["instances"]]
        matches = match_predictions_to_gt(gt_payload, pred_payload)
        for match in matches:
            gt_item = gt_payload[match["gt_index"]]
            if gt_item["label"] != "rings":
                continue
            ring_total += 1
            if pred_payload[match["pred_index"]]["label"] == "rings":
                ring_correct += 1
        matched_ring_indices = {
            match["gt_index"] for match in matches if gt_payload[match["gt_index"]]["label"] == "rings"
        }
        for gt_idx, gt_item in enumerate(gt_payload):
            if gt_item["label"] == "rings" and gt_idx not in matched_ring_indices:
                ring_total += 1

    metrics["overlap_strands"] = {
        "matched_accuracy": round(overlap_correct / max(overlap_matches, 1), 4),
        "detection_ratio": round(overlap_pred / max(overlap_gt, 1), 4),
        "gt_instances": overlap_gt,
        "pred_instances": overlap_pred,
    }
    metrics["small_ring_overlap"] = {
        "ring_recall": round(ring_correct / max(ring_total, 1), 4),
        "ring_gt_instances": ring_total,
    }
    return metrics


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
    a = np.asarray(mask_a, dtype=bool)
    b = np.asarray(mask_b, dtype=bool)
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / union) if union > 0 else 0.0


def write_confusion_csv(confusion_summary: dict[str, object], path: Path) -> None:
    labels = list(confusion_summary["labels"])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["gt_label", *labels, "missed", "support"])
        for row_label in labels:
            writer.writerow(
                [
                    row_label,
                    *[confusion_summary["counts"][row_label][col_label] for col_label in labels],
                    confusion_summary["missed"][row_label],
                    confusion_summary["row_support"][row_label],
                ]
            )
        writer.writerow(["spurious", *[confusion_summary["spurious"][col_label] for col_label in labels], "", ""])


def write_confusion_row_normalized_csv(confusion_summary: dict[str, object], path: Path) -> None:
    labels = list(confusion_summary["labels"])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["gt_label", *labels, "missed", "row_sum"])
        for row_label in labels:
            row_values = [float(confusion_summary["normalized"][row_label][col_label]) for col_label in labels]
            missed_ratio = round(
                float(confusion_summary["missed"][row_label] / max(confusion_summary["row_support"][row_label], 1)),
                4,
            )
            writer.writerow([row_label, *row_values, missed_ratio, round(sum(row_values) + missed_ratio, 4)])


def render_confusion_matrix_image(confusion_summary: dict[str, object], path: Path) -> None:
    labels = list(confusion_summary["labels"])
    counts = confusion_summary["counts"]
    normalized = confusion_summary["normalized"]
    row_support = confusion_summary["row_support"]
    overall_accuracy = float(confusion_summary["overall_accuracy"])

    cell_w = 164
    cell_h = 84
    left_w = 180
    top_h = 118
    right_w = 120
    width = left_w + cell_w * len(labels) + right_w
    height = top_h + cell_h * len(labels) + 36
    image = np.full((height, width, 3), 255, dtype=np.uint8)

    cv2.putText(image, "Balanced Synthetic Confusion Matrix", (22, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (24, 24, 24), 2, cv2.LINE_AA)
    cv2.putText(
        image,
        "Rows are ground truth. Each row sums to 100%, including missed detections.",
        (22, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (90, 90, 90),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        f"Overall accuracy {overall_accuracy * 100:.1f}%  |  Balanced support {row_support[labels[0]]} per class",
        (22, 94),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (60, 60, 60),
        1,
        cv2.LINE_AA,
    )

    for col_idx, label in enumerate(labels):
        x0 = left_w + col_idx * cell_w
        cv2.putText(image, label.title(), (x0 + 28, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (35, 35, 35), 1, cv2.LINE_AA)

    for row_idx, row_label in enumerate(labels):
        y0 = top_h + row_idx * cell_h
        cv2.putText(image, row_label.title(), (22, y0 + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 1, cv2.LINE_AA)
        cv2.putText(
            image,
            f"n={row_support[row_label]}",
            (22, y0 + 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (115, 115, 115),
            1,
            cv2.LINE_AA,
        )
        for col_idx, col_label in enumerate(labels):
            x0 = left_w + col_idx * cell_w
            value = float(normalized[row_label][col_label])
            count = int(counts[row_label][col_label])
            cv2.rectangle(image, (x0, y0), (x0 + cell_w - 6, y0 + cell_h - 6), _matrix_cell_color(value), -1)
            cv2.rectangle(image, (x0, y0), (x0 + cell_w - 6, y0 + cell_h - 6), (220, 220, 220), 1)
            cv2.putText(
                image,
                f"{value * 100:.0f}%",
                (x0 + 18, y0 + 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.78,
                (20, 20, 20),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                image,
                f"{count} / {row_support[row_label]}",
                (x0 + 18, y0 + 64),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (52, 52, 52),
                1,
                cv2.LINE_AA,
            )

    cv2.imwrite(str(path), image)


def _matrix_cell_color(value: float) -> tuple[int, int, int]:
    low = np.array([245, 245, 245], dtype=np.float32)
    high = np.array([91, 168, 122], dtype=np.float32)
    color = low + (high - low) * float(np.clip(value, 0.0, 1.0))
    return int(color[0]), int(color[1]), int(color[2])


def serialize_config(config: DemoConfig) -> dict[str, object]:
    return {
        "preprocess": asdict(config.preprocess),
        "segment": asdict(config.segment),
        "rules": asdict(config.rules),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a balanced synthetic benchmark for the floater demo.")
    parser.add_argument("--outdir", required=True, help="Directory for benchmark artifacts.")
    parser.add_argument("--rounds", type=int, default=1, help="Number of benchmark rounds to run.")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed.")
    parser.add_argument("--n", type=int, default=100, help="Samples per class per round.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run_closed_loop(
        outdir=args.outdir,
        rounds=args.rounds,
        seed=args.seed,
        n_per_suite=args.n,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
