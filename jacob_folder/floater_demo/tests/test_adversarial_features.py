from __future__ import annotations

from pathlib import Path

import cv2

from floater_demo.config import load_config
from floater_demo.features import compute_features
from floater_demo.infer import infer_image
from floater_demo.segment import InstanceComponent
from floater_demo.synth import generate_closed_loop_case


def test_controlled_feature_assertions() -> None:
    config = load_config()

    image, instances, _ = generate_closed_loop_case("true_dot_clean", seed=42)
    dot_features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instances[0]))
    assert dot_features.area <= config.rules.dot_area_max

    image, instances, _ = generate_closed_loop_case("true_ring_clean", seed=42)
    ring_features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instances[0]))
    assert ring_features.hole_count >= 1
    assert ring_features.max_hole_area_ratio >= config.rules.ring_big_hole_ratio

    image, instances, _ = generate_closed_loop_case("true_strand_thin", seed=42)
    strand_features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instances[0]))
    assert strand_features.elongation >= config.rules.strand_elong_min

    image, instances, _ = generate_closed_loop_case("membrane_cloud_faint", seed=42)
    membrane_features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instances[0]))
    assert membrane_features.area > config.rules.dot_area_max
    assert membrane_features.elongation < config.rules.strand_elong_min

    image, instances, _ = generate_closed_loop_case("small_ring_clean", seed=42)
    small_ring_features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instances[0]))
    assert small_ring_features.max_hole_area_ratio >= config.rules.ring_big_hole_ratio


def test_controlled_suite_labels(tmp_path: Path) -> None:
    config = load_config()
    expectations = {
        "true_dot_clean": {"dots"},
        "true_ring_clean": {"rings"},
        "true_strand_thin": {"strands"},
        "thick_strand_long": {"strands"},
        "membrane_cloud_faint": {"membranes"},
    }

    for suite_name, expected_labels in expectations.items():
        for idx in range(5):
            image, _, _ = generate_closed_loop_case(suite_name, seed=42 + idx)
            raw_path = tmp_path / suite_name / f"{suite_name}_{idx:03d}.png"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(raw_path), image)
            result = infer_image(raw_path, config, save_debug_masks=False)
            labels = {instance["label"] for instance in result["instances"]}
            assert labels & expected_labels


def test_mixed_scene_contains_all_demo_classes(tmp_path: Path) -> None:
    image, _, _ = generate_closed_loop_case("mixed_distinct_scene", seed=42)
    raw_path = tmp_path / "mixed.png"
    cv2.imwrite(str(raw_path), image)
    result = infer_image(raw_path, load_config(), save_debug_masks=False)
    labels = {instance["label"] for instance in result["instances"]}
    assert "dots" in labels
    assert "strands" in labels
    assert "membranes" in labels or "rings" in labels


def test_feature_debug_dump(tmp_path: Path) -> None:
    image, instances, _ = generate_closed_loop_case("true_strand_thin", seed=7)
    component = _component(instances[0])
    debug_dir = tmp_path / "debug"
    features = compute_features(
        cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
        component,
        debug_dir=debug_dir,
        debug_prefix="case",
    )
    assert features.skeleton_length > 0
    assert (debug_dir / "case_mask.png").exists()
    assert (debug_dir / "case_skeleton.png").exists()
    assert (debug_dir / "case_holes.png").exists()
    assert (debug_dir / "case_contour_hull.png").exists()
    assert (debug_dir / "case_features.json").exists()


def _component(instance) -> InstanceComponent:
    return InstanceComponent(
        id=instance.id,
        mask=instance.mask,
        bbox=instance.bbox,
        area=int(instance.mask.sum() // 255),
    )
