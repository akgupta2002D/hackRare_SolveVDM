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
