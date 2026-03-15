"""
Floater simulation logic. Kept out of routes so we can change the algorithm
without touching HTTP and test the logic without calling the API. This is were the code logic goes. Just a normal python file.
"""
import uuid
from app.schemas import SimulationParams, SimulationResult


def run_simulation_step(params: SimulationParams) -> SimulationResult:
    """One simulation step. Replace the placeholder with real floater logic later."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    # Placeholder: fake floater count from intensity
    count = max(1, int(params.intensity * 10))
    return SimulationResult(
        success=True,
        session_id=session_id,
        data={"frame": 1, "floaters_count": count, "intensity_used": params.intensity},
    )
