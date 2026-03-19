"""
Forward model math (MVP).

This is the only place that computes:
disturbance + optical_context -> percept outputs.
"""

from app.simulator_1_0_0.constraints import validate_inputs
from app.simulator_1_0_0.disturbance import Disturbance
from app.simulator_1_0_0.optical_context import OpticalContext
from app.simulator_1_0_0.percept_output import PerceptOutput


def compute_forward_model(
    disturbance: Disturbance,
    optical_context: OpticalContext,
) -> PerceptOutput:
    """Compute percept outputs from disturbance + optical context."""
    validate_inputs(disturbance, optical_context)

    # MVP relationships:
    # - closer disturbance => bigger shadow
    # - closer disturbance => sharper edges
    # - opacity directly controls how dark the artifact feels
    #
    # For MVP, we don't apply ambientBrightness/pupilSize yet. We still take
    # optical_context as an input so it can be used later without changing
    # the public function signature.
    depth = disturbance.depthZ
    apparent_size = disturbance.size / depth
    apparent_blur = 1.0 / depth
    apparent_darkness = disturbance.opacity

    return PerceptOutput(
        apparentSize=apparent_size,
        apparentBlur=apparent_blur,
        apparentDarkness=apparent_darkness,
    )


# Future suggestions (not part of MVP):
# - Use `optical_context.ambientBrightness` to modulate contrast/visibility.
# - Use `optical_context.pupilSize` to adjust blur/clarity (differing aperture).
# - Add non-linear mappings or tuned curves once we have real data.

