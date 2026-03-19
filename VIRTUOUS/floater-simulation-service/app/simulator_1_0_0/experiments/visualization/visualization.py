"""
Basic Visualization for depth sweep test experiment (Matplotlib)

Purpose:
  Inspect how the forward model behaves (depthZ -> percept outputs).
  This is *visual intuition only*; it does not render realistic images.

What it does:
  - Uses a fixed disturbance + fixed optical context
  - Sweeps 5 depthZ values (far -> near)
  - Calls compute_forward_model(disturbance, optical_context)
  - Maps outputs to simple visual parameters:
      circle radius     <- apparentSize
      circle blur (approx) <- apparentBlur
      circle intensity  <- apparentDarkness

Output:
  A single figure with 5 panels in a horizontal row.
"""

from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np

# Make `import app...` work when running as:
#   python visualization.py
SERVICE_ROOT = os.path.abspath(
    # Current file: .../app/simulator_1_0_0/experiments/visualization/visualization.py
    # We want .../ (service root) so `import app...` works.
    os.path.join(os.path.dirname(__file__), "../../../../")
)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from app.simulator_1_0_0.constraints import validate_inputs
from app.simulator_1_0_0.core_model import compute_forward_model
from app.simulator_1_0_0.disturbance import Disturbance
from app.simulator_1_0_0.optical_context import OpticalContext


def _gaussian_kernel1d(sigma: float, radius: int | None = None) -> np.ndarray:
    """Create a simple 1D Gaussian kernel for blur visualization."""
    if sigma <= 0:
        return np.array([1.0], dtype=float)

    if radius is None:
        # 3 sigma on each side keeps most of the energy.
        radius = int(math.ceil(3.0 * sigma))
    radius = max(1, radius)

    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-(x**2) / (2.0 * sigma**2))
    kernel /= kernel.sum()
    return kernel


def _blur_mask(mask: np.ndarray, sigma: float) -> np.ndarray:
    """Blur a 2D mask by convolving with separable Gaussian kernels."""
    if sigma <= 0:
        return mask

    kernel = _gaussian_kernel1d(sigma)

    # Separable convolution: blur in x then in y.
    blurred = np.apply_along_axis(
        lambda row: np.convolve(row, kernel, mode="same"), axis=1, arr=mask
    )
    blurred = np.apply_along_axis(
        lambda col: np.convolve(col, kernel, mode="same"), axis=0, arr=blurred
    )
    return blurred


def _draw_panel(
    ax,
    percept,
    title: str,
    grid_size: int = 200,
    center: tuple[float, float] = (100, 100),
) -> None:
    """Draw one panel using only percept outputs (no extra model logic)."""
    # We build a simple grayscale mask where intensity is darkest at the center.
    h = w = grid_size
    cx, cy = center

    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

    # Map apparentSize -> radius
    radius_px = max(1.0, float(percept.apparentSize) * 30.0)

    # Map apparentDarkness -> overall intensity (0..1)
    intensity = float(percept.apparentDarkness)
    intensity = max(0.0, min(1.0, intensity))

    # Build a hard circle mask in [0..1], then blur it by apparentBlur.
    mask = (rr <= radius_px).astype(float)

    # Map apparentBlur -> blur sigma (visual approximation)
    blur_sigma = max(0.0, float(percept.apparentBlur) * 2.0)
    blurred = _blur_mask(mask, blur_sigma)

    # Convert to display image: intensity controls darkness.
    # Higher darkness => darker circle.
    img = 1.0 - intensity * blurred / (blurred.max() + 1e-9)

    ax.imshow(img, cmap="gray", interpolation="nearest")
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])


def run(
    size: float = 0.2,
    opacity: float = 0.6,
    ambient_brightness: float = 100.0,
    pupil_size: float = 4.0,
    depth_values: list[float] | None = None,
    save_path: str | None = None,
) -> None:
    """Render the 1x5 depth sweep visualization."""
    if depth_values is None:
        depth_values = [15.0, 10.0, 5.0, 2.0, 0.5]

    optical_context = OpticalContext(
        ambientBrightness=ambient_brightness, pupilSize=pupil_size
    )

    # Fixed disturbance parts
    results = []
    for depthZ in depth_values:
        disturbance = Disturbance(depthZ=depthZ, size=size, opacity=opacity)
        # Explicit validation keeps errors obvious during debugging.
        validate_inputs(disturbance, optical_context)
        percept = compute_forward_model(disturbance, optical_context)
        results.append(percept)

    # Matplotlib writes a cache/config dir on first import. Some sandboxed
    # environments can’t write to `~/.matplotlib`, so force a writable folder.
    mpl_cache_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), ".mpl_cache")
    )
    os.makedirs(mpl_cache_dir, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", mpl_cache_dir)

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(depth_values), figsize=(3.5 * len(depth_values), 3.5))

    # Ensure `axes` is always iterable.
    if len(depth_values) == 1:
        axes = [axes]

    # Far -> near mapping (left -> right)
    for ax, depthZ, percept in zip(axes, depth_values, results):
        title = f"depthZ={depthZ:g}"
        _draw_panel(ax, percept, title=title)

    fig.suptitle("Phase 1.5: Depth sweep -> percept outputs", fontsize=11)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=200)
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Depth sweep visualization (MVP).")
    parser.add_argument("--save", type=str, default=None, help="Optional output image path (png).")
    args = parser.parse_args()

    run(save_path=args.save)


if __name__ == "__main__":
    main()

