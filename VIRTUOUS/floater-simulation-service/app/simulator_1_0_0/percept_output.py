"""
Percept output container (MVP).

This module is intentionally only a structured data container.
No computation belongs here.
"""

from pydantic import BaseModel, Field


class PerceptOutput(BaseModel):
    """Forward model outputs at the retinal/percept level."""

    # Effective shadow size on retina (relative units).
    apparentSize: float = Field(..., ge=0.0)

    # Edge softness (relative units; larger => more blur).
    apparentBlur: float = Field(..., ge=0.0)

    # Shadow darkness reduction (0=none, 1=max darkness for MVP).
    apparentDarkness: float = Field(..., ge=0.0, le=1.0)

    # later: visibility, contrastDrop

