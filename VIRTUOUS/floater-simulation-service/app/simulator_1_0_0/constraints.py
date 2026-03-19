"""
Input validation rules (MVP).

Keep validation separate from the forward-model math.
This makes it easier to change rules without touching the core computation.
"""

from app.simulator_1_0_0.disturbance import Disturbance
from app.simulator_1_0_0.optical_context import OpticalContext


# Simple MVP bounds. Tune later if needed.
MIN_DEPTH_Z = 0.01
MAX_DEPTH_Z = 100.0

# size is a relative scale (MVP).
MIN_SIZE = 0.0
MAX_SIZE = 1000.0

MIN_OPACITY = 0.0
MAX_OPACITY = 1.0


def validate_inputs(disturbance: Disturbance, optical_context: OpticalContext) -> None:
    """Raise ValueError if values are outside the allowed MVP ranges."""
    if not (MIN_DEPTH_Z <= disturbance.depthZ <= MAX_DEPTH_Z):
        raise ValueError(f"depthZ must be in [{MIN_DEPTH_Z}, {MAX_DEPTH_Z}]")
    if not (MIN_SIZE <= disturbance.size <= MAX_SIZE):
        raise ValueError(f"size must be in [{MIN_SIZE}, {MAX_SIZE}]")
    if not (MIN_OPACITY <= disturbance.opacity <= MAX_OPACITY):
        raise ValueError(f"opacity must be in [{MIN_OPACITY}, {MAX_OPACITY}]")

    # Keep optical ranges intentionally loose for MVP.
    if optical_context.ambientBrightness < 0.0:
        raise ValueError("ambientBrightness must be >= 0")
    if optical_context.pupilSize < 0.0:
        raise ValueError("pupilSize must be >= 0")


# Future suggestions (not part of MVP):
# - Add invalid-combination checks if some parameter ranges conflict
#   (e.g., extremely large size with very large depth leading to unstable
#   artifacts in the chosen formulas).
# - Tie optical_context ranges to how we'll later compute visibility.

