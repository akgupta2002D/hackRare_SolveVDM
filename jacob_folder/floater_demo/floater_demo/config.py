from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreprocessConfig:
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: int = 8
    adaptive_block_size: int = 35
    adaptive_c: int = 7
    raw_dark_threshold: int = 245
    raw_support_dilate_size: int = 3
    raw_mask_gate_coverage_max: float = 1.0
    morph_open_size: int = 3
    morph_close_size: int = 3
    min_component_area: int = 16


@dataclass(frozen=True)
class SegmentConfig:
    min_instance_area: int = 20


@dataclass(frozen=True)
class RuleConfig:
    ring_min_hole_area_ratio: float = 0.06
    ring_min_hole_area_total_ratio: float = 0.08
    ring_min_annularity_ratio: float = 0.18
    ring_min_circularity: float = 0.24
    ring_max_thickness: float = 16.0
    ring_skel_max: float = 320.0
    ring_min_solidity: float = 0.22
    ring_max_solidity: float = 0.72
    ring_max_hole_count: int = 2
    ring_max_aspect_ratio: float = 1.45
    dot_circ_min: float = 0.58
    dot_area_max: int = 2400
    dot_skel_max: float = 70.0
    dot_min_solidity: float = 0.72
    dot_max_aspect_ratio: float = 1.85
    dot_cluster_area_max: int = 1800
    dot_cluster_circ_min: float = 0.42
    dot_cluster_skel_max: float = 28.0
    dot_cluster_min_solidity: float = 0.72
    strand_skel_min: float = 28.0
    strand_thick_max: float = 8.5
    strand_circ_max: float = 0.32
    strand_branch_thick_max: float = 14.0
    strand_sparse_solidity_max: float = 0.34
    membrane_area_min: int = 1800
    membrane_thickness_min: float = 4.5
    membrane_force_area_min: int = 2800
    membrane_force_thickness_min: float = 12.0
    membrane_holey_area_min: int = 5500
    membrane_holey_aspect_min: float = 1.7
    membrane_holey_hole_count_min: int = 2


@dataclass(frozen=True)
class DemoConfig:
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    segment: SegmentConfig = field(default_factory=SegmentConfig)
    rules: RuleConfig = field(default_factory=RuleConfig)


def load_config() -> DemoConfig:
    return DemoConfig()
