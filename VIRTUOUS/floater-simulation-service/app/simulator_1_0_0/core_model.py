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

    # MVP relationships (aligned with the experiment guide):
    # - far -> near (depthZ decreases): apparentSize ↓ and apparentBlur ↓
    # - far -> near: apparentDarkness ↑
    #
    # For MVP, we don't use ambientBrightness/pupilSize yet. We keep optical_context
    # in the signature so we can expand later without changing the API.
    depth = disturbance.depthZ

    # Bigger depth => bigger shadow on the retina (so near => smaller).
    apparent_size = disturbance.size * depth

    # Bigger depth => more blur (so near => sharper edges).
    apparent_blur = depth

    # Darkness increases as the disturbance gets closer to the retina.
    apparent_darkness = disturbance.opacity / depth
    if apparent_darkness > 1.0:
        apparent_darkness = 1.0

    return PerceptOutput(
        apparentSize=apparent_size,
        apparentBlur=apparent_blur,
        apparentDarkness=apparent_darkness,
    )


# Future suggestions (not part of MVP):
# - Use `optical_context.ambientBrightness` to modulate contrast/visibility.
# - Use `optical_context.pupilSize` to adjust blur/clarity (differing aperture).
# - Add non-linear mappings or tuned curves once we have real data.

