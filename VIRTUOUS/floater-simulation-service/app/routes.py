"""
HTTP endpoints: root, health, ready, and simulation run. Express calls /health
to check we're up and POST /api/v1/simulation/run to run a simulation.
"""
from fastapi import APIRouter

from app.config import APP_NAME
from app.schemas import MessageResponse, SimulationParams, SimulationResult
from app.simulation import run_simulation_step

router = APIRouter()


@router.get("/")
def root():
    """Root so we know the service is up."""
    return {"service": APP_NAME, "message": "Floater simulation service is running."}


# ---- Health (Express can ping these) ----
@router.get("/health", response_model=MessageResponse)
def health():
    """Is the service up? Express can call this."""
    return MessageResponse(message="ok", service=APP_NAME)


@router.get("/health/ready", response_model=MessageResponse)
def ready():
    """Ready for traffic."""
    return MessageResponse(message="ready", service=APP_NAME)


# ---- Simulation (what Express will call) ----
@router.post("/api/v1/simulation/run", response_model=SimulationResult)
def run_simulation(params: SimulationParams):
    """Run one simulation step. POST from Express with JSON body { intensity, duration_seconds }."""
    return run_simulation_step(params)
