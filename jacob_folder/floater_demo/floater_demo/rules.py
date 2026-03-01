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
        and features.hole_count <= config.ring_max_hole_count
        and features.max_hole_area_ratio >= config.ring_min_hole_area_ratio
        and features.hole_area_total_ratio >= config.ring_min_hole_area_total_ratio
        and features.annularity_ratio >= config.ring_min_annularity_ratio
        and features.circularity >= config.ring_min_circularity
        and features.thickness_est <= config.ring_max_thickness
        and features.skeleton_length <= config.ring_skel_max
        and features.solidity >= config.ring_min_solidity
        and features.solidity <= config.ring_max_solidity
        and features.bbox_aspect_ratio <= config.ring_max_aspect_ratio
    ):
        return RulePrediction(
            label="rings",
            confidence=_clamp(
                0.72
                + 0.12 * min(features.hole_count, 2) / 2.0
                + 0.1 * min(features.max_hole_area_ratio / max(config.ring_min_hole_area_ratio, 1e-6), 2.0) / 2.0
                + 0.06 * min(features.annularity_ratio / max(config.ring_min_hole_area_total_ratio, 1e-6), 2.0) / 2.0
            ),
            explanation="Detected a substantial enclosed hole with ring-like geometry.",
        )

    if (
        features.area >= config.membrane_force_area_min
        and features.thickness_est >= config.membrane_force_thickness_min
    ):
        return RulePrediction(
            label="membranes",
            confidence=_clamp(
                0.62
                + 0.14 * min(features.area / max(config.membrane_force_area_min, 1), 2.0) / 2.0
                + 0.14 * min(features.thickness_est / max(config.membrane_force_thickness_min, 1e-6), 2.0) / 2.0
            ),
            explanation="Large thick region matched explicit membrane rule before strand fallback.",
        )

    if (
        features.area >= config.membrane_holey_area_min
        and features.bbox_aspect_ratio >= config.membrane_holey_aspect_min
        and features.hole_count >= config.membrane_holey_hole_count_min
    ):
        return RulePrediction(
            label="membranes",
            confidence=_clamp(
                0.58
                + 0.14 * min(features.area / max(config.membrane_holey_area_min, 1), 2.0) / 2.0
                + 0.12 * min(features.bbox_aspect_ratio / max(config.membrane_holey_aspect_min, 1e-6), 2.0) / 2.0
            ),
            explanation="Large elongated holey region matched membrane sheet heuristic.",
        )

    if (
        features.circularity >= config.dot_circ_min
        and features.area <= config.dot_area_max
        and features.skeleton_length <= config.dot_skel_max
        and features.solidity >= config.dot_min_solidity
        and features.bbox_aspect_ratio <= config.dot_max_aspect_ratio
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
        features.hole_count == 0
        and features.area <= config.dot_cluster_area_max
        and features.circularity >= config.dot_cluster_circ_min
        and features.skeleton_length <= config.dot_cluster_skel_max
        and features.solidity >= config.dot_cluster_min_solidity
        and features.bbox_aspect_ratio <= config.dot_max_aspect_ratio
    ):
        return RulePrediction(
            label="dots",
            confidence=_clamp(
                0.56
                + 0.14 * min(features.circularity / max(config.dot_cluster_circ_min, 1e-6), 2.0) / 2.0
                + 0.12 * min(features.solidity / max(config.dot_cluster_min_solidity, 1e-6), 1.5) / 1.5
            ),
            explanation="Compact no-hole cluster matched relaxed dot rule.",
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

    if (
        features.skeleton_length >= config.strand_skel_min * 1.6
        and features.thickness_est <= config.strand_branch_thick_max
        and features.solidity <= config.strand_sparse_solidity_max
    ):
        return RulePrediction(
            label="strands",
            confidence=_clamp(
                0.56
                + 0.16 * min(features.skeleton_length / max(config.strand_skel_min * 1.6, 1.0), 2.0) / 2.0
                + 0.12 * max(0.0, 1.0 - features.solidity / max(config.strand_sparse_solidity_max, 1e-6))
            ),
            explanation="Long sparse branched component matched relaxed strand rule.",
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
