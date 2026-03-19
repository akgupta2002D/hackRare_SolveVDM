"""
Optical context input model (MVP).

This stores the eye + environment conditions:
- ambientBrightness
- pupilSize

The goal: create a clean context object that the core model can use.
"""

from pydantic import BaseModel, Field


class OpticalContext(BaseModel):
    """Eye/environment settings used during forward computation."""

    # Ambient brightness. MVP: use a simple normalized range.
    ambientBrightness: float = Field(..., ge=0.0)

    # Pupil size (MVP units, e.g., mm-ish).
    pupilSize: float = Field(..., ge=0.0)

    # later: backgroundType, focusState

