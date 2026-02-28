from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreprocessConfig:
    adaptive_block_size: int = 35
    adaptive_c: int = 7
    raw_dark_threshold: int = 245
    morph_open_size: int = 3
    morph_close_size: int = 3
    min_component_area: int = 16


@dataclass(frozen=True)
class SegmentConfig:
    min_instance_area: int = 20


@dataclass(frozen=True)
class RuleConfig:
    dot_circ_min: float = 0.58
    dot_area_max: int = 2400
    dot_skel_max: float = 70.0
    strand_skel_min: float = 28.0
    strand_thick_max: float = 8.5
    strand_circ_max: float = 0.32
    membrane_area_min: int = 1800
    membrane_thickness_min: float = 4.5


@dataclass(frozen=True)
class DemoConfig:
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    segment: SegmentConfig = field(default_factory=SegmentConfig)
    rules: RuleConfig = field(default_factory=RuleConfig)


def load_config() -> DemoConfig:
    return DemoConfig()
