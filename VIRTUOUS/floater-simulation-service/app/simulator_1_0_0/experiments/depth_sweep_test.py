"""
Depth Sweep Test

Run:
  python depth_sweep_test.py

What it does:
1) Fix size/opacity/eye context constants
2) Sweep depthZ from far -> near
3) Call compute_forward_model for each depthZ
4) Assert the expected monotonic behavior:
   - apparentSize ↓ (far -> near)
   - apparentBlur ↓ (far -> near)
   - apparentDarkness ↑ (far -> near)
"""

from __future__ import annotations

import math
import os
import sys

# When running this file directly, Python's import path points to this folder
# (`.../app/simulator_1_0_0/experiments`). Add the service root so `import app...`
# works without needing an installed package.
SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from app.simulator_1_0_0.constraints import validate_inputs
from app.simulator_1_0_0.core_model import compute_forward_model
from app.simulator_1_0_0.disturbance import Disturbance
from app.simulator_1_0_0.optical_context import OpticalContext


def _is_finite_number(x: object) -> bool:
    """True if x is a float/int and not NaN/Inf."""
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _assert_monotonic_decreasing(values: list[float], label: str) -> None:
    """Assert values go down as the sweep progresses (index 0 -> end)."""
    for i in range(len(values) - 1):
        if values[i] < values[i + 1]:
            raise AssertionError(f"{label} expected to decrease: {values}")


def _assert_monotonic_increasing(values: list[float], label: str) -> None:
    """Assert values go up as the sweep progresses (index 0 -> end)."""
    for i in range(len(values) - 1):
        if values[i] > values[i + 1]:
            raise AssertionError(f"{label} expected to increase: {values}")


def main() -> None:
    # Fix these values (same as the guide)
    size = 0.2
    opacity = 0.6
    ambientBrightness = 100.0
    pupilSize = 4.0

    # Sweep depthZ (far -> near)
    depth_values = [15.0, 10.0, 5.0, 2.0, 0.5]

    optical_context = OpticalContext(
        ambientBrightness=ambientBrightness, pupilSize=pupilSize
    )

    # Build disturbance, validate, compute, store outputs
    results: list[dict] = []
    for depthZ in depth_values:
        disturbance = Disturbance(depthZ=depthZ, size=size, opacity=opacity)

        # Extra explicit validation step (core_model also validates)
        validate_inputs(disturbance, optical_context)

        percept = compute_forward_model(disturbance, optical_context)

        results.append(
            {
                "depthZ": depthZ,
                "apparentSize": float(percept.apparentSize),
                "apparentBlur": float(percept.apparentBlur),
                "apparentDarkness": float(percept.apparentDarkness),
            }
        )

    # Print a tiny table for quick human checking
    print("\nDepth Sweep Results (far -> near):")
    print("depthZ\tapparentSize\tapparentBlur\tapparentDarkness")
    for r in results:
        print(
            f"{r['depthZ']:.3f}\t{r['apparentSize']:.6f}\t{r['apparentBlur']:.6f}\t{r['apparentDarkness']:.6f}"
        )

    apparent_size_vals = [r["apparentSize"] for r in results]
    apparent_blur_vals = [r["apparentBlur"] for r in results]
    apparent_darkness_vals = [r["apparentDarkness"] for r in results]

    # Assertions: numeric + monotonic
    for r in results:
        if not _is_finite_number(r["apparentSize"]):
            raise AssertionError("apparentSize is not a finite number")
        if not _is_finite_number(r["apparentBlur"]):
            raise AssertionError("apparentBlur is not a finite number")
        if not _is_finite_number(r["apparentDarkness"]):
            raise AssertionError("apparentDarkness is not a finite number")

    # Expected monotonic behavior from your guide
    _assert_monotonic_decreasing(apparent_size_vals, "apparentSize")
    _assert_monotonic_decreasing(apparent_blur_vals, "apparentBlur")
    _assert_monotonic_increasing(apparent_darkness_vals, "apparentDarkness")

    print("\nSuccess: outputs are numeric and behave smoothly/monotonically (per guide).")


if __name__ == "__main__":
    main()

