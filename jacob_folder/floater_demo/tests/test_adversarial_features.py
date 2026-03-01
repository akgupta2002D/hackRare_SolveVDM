from __future__ import annotations

from pathlib import Path

import cv2

from floater_demo.config import load_config
from floater_demo.features import compute_features
from floater_demo.infer import infer_image
from floater_demo.segment import InstanceComponent
from floater_demo.synth import ADVERSARIAL_SUITES, generate_adversarial_case, generate_adversarial_suite, generate_closed_loop_case


def test_adversarial_feature_assertions() -> None:
    config = load_config()

    image, instance, _ = generate_adversarial_case("membrane_with_tiny_hole", seed=42)
    features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instance))
    assert features.hole_count >= 1
    assert features.max_hole_area_ratio < config.rules.ring_min_hole_area_ratio

    image, instance, _ = generate_adversarial_case("membrane_with_pinhole_noise", seed=42)
    features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instance))
    assert features.hole_count == 0
    assert features.max_hole_area_ratio == 0.0

    image, instance, _ = generate_adversarial_case("membrane_with_big_hole", seed=42)
    features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instance))
    assert features.max_hole_area_ratio >= config.rules.ring_min_hole_area_ratio
    assert features.annularity_ratio < config.rules.ring_min_annularity_ratio

    image, instance, _ = generate_adversarial_case("thick_strand_long", seed=42)
    features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instance))
    assert features.skeleton_length >= config.rules.strand_skel_min
    assert features.thickness_est <= config.rules.strand_branch_thick_max

    image, instance, _ = generate_adversarial_case("broken_ring_gap_small", seed=42)
    features = compute_features(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), _component(instance))
    assert features.hole_area_total_ratio >= config.rules.ring_min_hole_area_total_ratio
    assert features.circularity >= config.rules.ring_min_circularity


def test_adversarial_suite_labels(tmp_path: Path) -> None:
    config = load_config()
    expectations = {
        "membrane_with_tiny_hole": "membranes",
        "membrane_with_big_hole": "membranes",
        "strand_with_loop_tail": "strands",
        "crossing_strands_pocket_hole": "strands",
        "thick_strand_long": "strands",
        "broken_ring_gap_small": "rings",
        "broken_ring_gap_large": "strands",
    }

    for suite_name, expected_label in expectations.items():
        suite_dir = tmp_path / suite_name
        summary = generate_adversarial_suite(suite_name, suite_dir, k=3, seed=42, config=config)
        assert summary["expected_label"] == expected_label
        assert summary["confusion"].get(expected_label, 0) >= 2

        for idx in range(3):
            raw_path = suite_dir / f"{suite_name}_{idx:03d}.png"
            result = infer_image(raw_path, config, save_debug_masks=False)
            assert result["summary"]["instance_count"] >= 1


def test_feature_debug_dump(tmp_path: Path) -> None:
    image, instance, _ = generate_adversarial_case("strand_with_loop_tail", seed=7)
    component = _component(instance)
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


def test_ring_false_positive_and_true_ring_rates(tmp_path: Path) -> None:
    config = load_config()

    pinhole_dir = tmp_path / "pinhole"
    pinhole_rings = 0
    pinhole_total = 20
    for idx in range(pinhole_total):
        image, _, _ = generate_adversarial_case("membrane_with_pinhole_noise", seed=100 + idx)
        raw_path = pinhole_dir / f"case_{idx:03d}.png"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(raw_path), image)
        result = infer_image(raw_path, config, save_debug_masks=False, debug_instance_dir=pinhole_dir / f"debug_{idx:03d}")
        if result["instances"]:
            pinhole_rings += sum(1 for item in result["instances"] if item["label"] == "rings")
    assert pinhole_rings / pinhole_total <= 0.05

    ring_dir = tmp_path / "true_ring"
    ring_hits = 0
    ring_total = 20
    for idx in range(ring_total):
        image, _, _ = generate_closed_loop_case("true_ring_clean", seed=200 + idx)
        raw_path = ring_dir / f"case_{idx:03d}.png"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(raw_path), image)
        result = infer_image(raw_path, config, save_debug_masks=False, debug_instance_dir=ring_dir / f"debug_{idx:03d}")
        if result["instances"] and result["instances"][0]["label"] == "rings":
            ring_hits += 1
    assert ring_hits / ring_total >= 0.9
    assert (ring_dir / "debug_000" / "instance_001_decision.json").exists()

    pocket_dir = tmp_path / "pocket"
    pocket_rings = 0
    pocket_total = 20
    for idx in range(pocket_total):
        image, _, _ = generate_adversarial_case("crossing_strands_pocket_hole", seed=300 + idx)
        raw_path = pocket_dir / f"case_{idx:03d}.png"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(raw_path), image)
        result = infer_image(raw_path, config, save_debug_masks=False, debug_instance_dir=pocket_dir / f"debug_{idx:03d}")
        if result["instances"] and any(item["label"] == "rings" for item in result["instances"]):
            pocket_rings += 1
    assert pocket_rings == 0


def _component(instance) -> InstanceComponent:
    return InstanceComponent(
        id=instance.id,
        mask=instance.mask,
        bbox=instance.bbox,
        area=int(instance.mask.sum() // 255),
    )
