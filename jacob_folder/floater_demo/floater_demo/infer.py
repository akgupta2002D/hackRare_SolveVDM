from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from .config import DemoConfig
from .features import compute_features
from .preprocess import preprocess_image
from .rules import classify_instance
from .segment import segment_instances
from .utils import mask_to_contour, normalize_bbox, normalize_contour


def infer_image(
    png_path: str | Path,
    config: DemoConfig,
    save_debug_masks: bool = False,
    debug_instance_dir: str | Path | None = None,
) -> dict[str, object]:
    pre = preprocess_image(png_path, config.preprocess)
    components = segment_instances(pre.binary_mask, config.segment)
    image_width = int(pre.original_bgr.shape[1])
    image_height = int(pre.original_bgr.shape[0])

    instances: list[dict[str, object]] = []
    for component in components:
        features = compute_features(
            pre.grayscale,
            component,
            debug_dir=debug_instance_dir,
            debug_prefix=f"instance_{component.id:03d}" if debug_instance_dir is not None else None,
        )
        prediction = classify_instance(features, config.rules)
        if debug_instance_dir is not None:
            _save_rule_debug(
                output_dir=debug_instance_dir,
                prefix=f"instance_{component.id:03d}",
                prediction=prediction,
                features=features.to_dict(),
            )
        bbox = list(component.bbox)
        contour = mask_to_contour(component.mask)
        instances.append(
            {
                "id": component.id,
                "bbox": bbox,
                "bbox_normalized": normalize_bbox(bbox, image_width, image_height),
                "contour": contour,
                "contour_normalized": normalize_contour(contour, image_width, image_height),
                "area": component.area,
                "features": _serialize_features(asdict(features)),
                "label": prediction.label,
                "confidence": prediction.confidence,
                "explanation": prediction.explanation,
                "mask": component.mask if save_debug_masks else None,
            }
        )

    return {
        "image": {
            "path": str(png_path),
            "width": image_width,
            "height": image_height,
        },
        "summary": {
            "instance_count": len(instances),
            "counts": _count_labels(instances),
        },
        "expo": {
            "canvas": {
                "width": image_width,
                "height": image_height,
            },
            "instances": [
                {
                    "id": instance["id"],
                    "label": instance["label"],
                    "confidence": instance["confidence"],
                    "bbox": instance["bbox"],
                    "bbox_normalized": instance["bbox_normalized"],
                    "contour": instance["contour"],
                    "contour_normalized": instance["contour_normalized"],
                }
                for instance in instances
            ],
        },
        "instances": instances,
        "debug": {
            "binary_mask": pre.binary_mask if save_debug_masks else None,
        },
        "_render": {
            "original_bgr": pre.original_bgr,
            "binary_mask": pre.binary_mask,
        },
    }


def build_expo_payload(result: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "image": {
            "width": result["image"]["width"],
            "height": result["image"]["height"],
        },
        "summary": result["summary"],
        "instances": [
            {
                "id": instance["id"],
                "label": instance["label"],
                "confidence": instance["confidence"],
                "bbox": instance["bbox"],
                "bbox_normalized": instance["bbox_normalized"],
                "contour": instance["contour"],
                "contour_normalized": instance["contour_normalized"],
            }
            for instance in result["instances"]
        ],
    }


def _serialize_features(features: dict[str, object]) -> dict[str, object]:
    serialized: dict[str, object] = {}
    for key, value in features.items():
        if isinstance(value, float):
            serialized[key] = round(value, 4)
        else:
            serialized[key] = value
    return serialized


def _count_labels(instances: list[dict[str, object]]) -> dict[str, int]:
    counts = {"dots": 0, "strands": 0, "membranes": 0, "rings": 0}
    for instance in instances:
        counts[str(instance["label"])] += 1
    return counts


def _save_rule_debug(
    output_dir: str | Path,
    prefix: str,
    prediction: object,
    features: dict[str, object],
) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": prediction.label,
        "confidence": prediction.confidence,
        "explanation": prediction.explanation,
        "features": features,
    }
    with (path / f"{prefix}_decision.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
