from __future__ import annotations

from dataclasses import dataclass

from .config import RuleConfig
from .features import InstanceFeatures


@dataclass(frozen=True)
class RulePrediction:
    label: str
    confidence: float
    explanation: str


def classify_instance(features: InstanceFeatures, config: RuleConfig) -> RulePrediction:
    if (
        features.hole_count >= 1
        and features.max_hole_area_ratio >= config.ring_big_hole_ratio
        and features.annularity_ratio >= config.ring_min_annularity_ratio
        and features.thickness_est <= config.ring_max_thickness
        and features.bbox_aspect_ratio <= config.ring_max_aspect_ratio_simple
        and features.circularity >= config.ring_min_circularity_simple
    ):
        return RulePrediction(
            label="rings",
            confidence=_clamp(
                0.7
                + 0.14 * min(features.max_hole_area_ratio / max(config.ring_big_hole_ratio, 1e-6), 2.0) / 2.0
                + 0.08 * min(features.annularity_ratio / max(config.ring_min_annularity_ratio, 1e-6), 2.0) / 2.0
                + 0.08 * min(features.hole_count, 2) / 2.0
            ),
            explanation="Detected a large obvious hole inside a thin annular structure.",
        )

    if (
        features.area >= config.membrane_area_min
        and features.elongation < config.membrane_elong_max
    ):
        return RulePrediction(
            label="membranes",
            confidence=_clamp(
                0.62
                + 0.16 * min(features.area / max(config.membrane_area_min, 1), 2.0) / 2.0
                + 0.1 * max(0.0, 1.0 - min(features.elongation / max(config.membrane_elong_max, 1e-6), 1.0))
            ),
            explanation="Large compact region matched membrane rule.",
        )

    if features.elongation >= config.strand_elong_min:
        return RulePrediction(
            label="strands",
            confidence=_clamp(
                0.62
                + 0.2 * min(features.elongation / max(config.strand_elong_min, 1e-6), 2.0) / 2.0
                + 0.08 * min(features.bbox_aspect_ratio / max(config.strand_elong_min * 0.6, 1e-6), 2.0) / 2.0
            ),
            explanation="Elongated component matched strand rule.",
        )

    if (
        features.elongation >= 1.8
        and features.area < config.membrane_area_min
    ):
        return RulePrediction(
            label="strands",
            confidence=_clamp(
                0.56
                + 0.16 * min(features.elongation / 1.8, 2.0) / 2.0
                + 0.1 * max(0.0, 1.0 - min(features.area / max(config.membrane_area_min, 1), 1.0))
            ),
            explanation="Moderately elongated small component matched relaxed strand rule.",
        )

    if features.area <= config.dot_area_max and features.circularity >= 0.35:
        return RulePrediction(
            label="dots",
            confidence=_clamp(
                0.58
                + 0.14 * max(0.0, 1.0 - min(features.area / max(config.dot_area_max, 1), 1.0))
                + 0.12 * min(features.circularity, 1.0)
            ),
            explanation="Small compact component matched dot rule.",
        )

    return RulePrediction(
        label="membranes",
        confidence=_membrane_confidence(features, config),
        explanation="Larger compact component fell back to membrane rule.",
    )


def _membrane_confidence(features: InstanceFeatures, config: RuleConfig) -> float:
    area_score = min(features.area / max(config.membrane_area_min, 1), 2.0) / 2.0
    return _clamp(0.58 + 0.2 * area_score + 0.08 * min(features.circularity, 1.0))


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)
