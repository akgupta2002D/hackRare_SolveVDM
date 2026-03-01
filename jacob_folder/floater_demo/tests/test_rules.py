from floater_demo.config import load_config
from floater_demo.features import InstanceFeatures
from floater_demo.rules import classify_instance


def test_branched_sparse_component_prefers_strands_over_membranes() -> None:
    config = load_config().rules
    features = InstanceFeatures(
        area=3200,
        perimeter=620.0,
        circularity=0.10,
        bbox_aspect_ratio=1.35,
        elongation=3.4,
        solidity=0.22,
        skeleton_length=140.0,
        hole_count=0,
        max_hole_area_ratio=0.0,
        hole_area_total_ratio=0.0,
        annularity_ratio=0.0,
        thickness_est=10.5,
    )
    prediction = classify_instance(features, config)
    assert prediction.label == "strands"


def test_thick_holey_blob_does_not_trigger_ring_rule() -> None:
    config = load_config().rules
    features = InstanceFeatures(
        area=4100,
        perimeter=360.0,
        circularity=0.4,
        bbox_aspect_ratio=1.15,
        elongation=1.2,
        solidity=0.78,
        skeleton_length=180.0,
        hole_count=1,
        max_hole_area_ratio=0.92,
        hole_area_total_ratio=0.92,
        annularity_ratio=0.16,
        thickness_est=18.0,
    )
    prediction = classify_instance(features, config)
    assert prediction.label == "membranes"


def test_true_thin_annular_shape_still_triggers_ring_rule() -> None:
    config = load_config().rules
    features = InstanceFeatures(
        area=1350,
        perimeter=210.0,
        circularity=0.38,
        bbox_aspect_ratio=1.1,
        elongation=1.15,
        solidity=0.86,
        skeleton_length=115.0,
        hole_count=1,
        max_hole_area_ratio=1.05,
        hole_area_total_ratio=1.05,
        annularity_ratio=0.41,
        thickness_est=8.4,
    )
    prediction = classify_instance(features, config)
    assert prediction.label == "rings"
