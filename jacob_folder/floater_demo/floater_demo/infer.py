from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .config import DemoConfig
from .features import compute_features
from .preprocess import preprocess_image
from .rules import classify_instance
from .segment import segment_instances


def infer_image(
    png_path: str | Path,
    config: DemoConfig,
    save_debug_masks: bool = False,
) -> dict[str, object]:
    pre = preprocess_image(png_path, config.preprocess)
    components = segment_instances(pre.binary_mask, config.segment)

    instances: list[dict[str, object]] = []
    for component in components:
        features = compute_features(pre.grayscale, component)
        prediction = classify_instance(features, config.rules)
        instances.append(
            {
                "id": component.id,
                "bbox": list(component.bbox),
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
            "width": int(pre.original_bgr.shape[1]),
            "height": int(pre.original_bgr.shape[0]),
        },
        "summary": {
            "instance_count": len(instances),
            "counts": _count_labels(instances),
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
