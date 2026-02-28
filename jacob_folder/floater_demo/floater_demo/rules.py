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
    if features.hole_count >= 1:
        return RulePrediction(
            label="rings",
            confidence=_clamp(0.85 + 0.05 * min(features.hole_count, 2)),
            explanation="Detected enclosed hole, matching ring shape.",
        )

    if (
        features.circularity >= config.dot_circ_min
        and features.area <= config.dot_area_max
        and features.skeleton_length <= config.dot_skel_max
    ):
        return RulePrediction(
            label="dots",
            confidence=_clamp(
                0.62
                + 0.18 * min(features.circularity, 1.0)
                + 0.1 * max(0.0, 1.0 - features.skeleton_length / max(config.dot_skel_max, 1.0))
            ),
            explanation="Small compact high-circularity component matched dot rule.",
        )

    if (
        features.skeleton_length >= config.strand_skel_min
        and features.thickness_est <= config.strand_thick_max
        and features.circularity <= config.strand_circ_max
    ):
        return RulePrediction(
            label="strands",
            confidence=_clamp(
                0.58
                + 0.16 * min(features.skeleton_length / max(config.strand_skel_min, 1.0), 2.0) / 2.0
                + 0.12 * max(0.0, 1.0 - features.thickness_est / max(config.strand_thick_max, 1.0))
            ),
            explanation="Long thin low-circularity component matched strand rule.",
        )

    return RulePrediction(
        label="membranes",
        confidence=_membrane_confidence(features, config),
        explanation="Fallback selected membrane for a thicker or broader region.",
    )


def _membrane_confidence(features: InstanceFeatures, config: RuleConfig) -> float:
    area_score = min(features.area / max(config.membrane_area_min, 1), 2.0) / 2.0
    thickness_score = min(features.thickness_est / max(config.membrane_thickness_min, 1e-6), 2.0) / 2.0
    return _clamp(0.5 + 0.22 * area_score + 0.18 * thickness_score)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)
