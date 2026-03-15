"""
Request and response models for the API. Defines what we accept (e.g. intensity)
and return (e.g. success, data) so Express gets a consistent JSON shape and
we get automatic validation.
"""
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Simple message, e.g. for health checks."""
    message: str
    service: str


class SimulationParams(BaseModel):
    """What the client (Express) sends for a simulation run."""
    intensity: float = Field(0.5, ge=0.0, le=1.0)
    duration_seconds: float | None = Field(None, ge=0.1, le=3600.0)


class SimulationResult(BaseModel):
    """What we send back to Express."""
    success: bool
    session_id: str | None = None
    data: dict | None = None
