"""
Disturbance input model (MVP).

This stores and validates the core disturbance parameters:
- depthZ
- size
- opacity

The goal: create a clean disturbance object for the core model.
"""

from pydantic import BaseModel, Field


class Disturbance(BaseModel):
    """Physical disturbance parameters used by the forward model."""

    # Distance from retina along optical axis. Must be > 0.
    depthZ: float = Field(..., gt=0.0)

    # We need to add a shape type too. Like a dot 

    # Physical scale (relative units for MVP).
    size: float = Field(..., ge=0.0)

    # Light blocking strength (0=none, 1=full).
    opacity: float = Field(..., ge=0.0, le=1.0)

    # later: shape, position, texture

