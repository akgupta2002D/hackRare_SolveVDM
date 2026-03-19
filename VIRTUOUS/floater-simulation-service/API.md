# Floater Simulation Service — API reference

This is the FastAPI service that the VIRTUOUS Express backend calls.  
Local base URL: `http://localhost:8000`

---

## Quick map

| Method | Path | Purpose |
|---:|---|---|
| GET | `/` | Just a quick “yep, it’s running” check |
| GET | `/health` | Express can ping this to see if we’re alive |
| GET | `/health/ready` | Readiness check (safe to send traffic) |
| POST | `/api/v1/simulation/run` | Run one simulation step (currently placeholder logic) |

---

## Endpoints

### GET `/`

- **Use**: Quick sanity check in a browser or with `curl`.
- **200 response**:

```json
{
  "service": "floater-simulation-service",
  "message": "Floater simulation service is running."
}
```

### GET `/health`

- **Use**: Express can ping this before calling simulation routes.
- **200 response**:

```json
{
  "message": "ok",
  "service": "floater-simulation-service"
}
```

### GET `/health/ready`

- **Use**: Readiness probe (we’ll extend later if we add DB/cache stuff).
- **200 response**:

```json
{
  "message": "ready",
  "service": "floater-simulation-service"
}
```

### POST `/api/v1/simulation/run`

- **Use**: Express calls this to run one simulation step.
- **Content-Type**: `application/json`

#### Request body

```json
{
  "intensity": 0.5,
  "duration_seconds": null
}
```

- **`intensity`**: float in \([0.0, 1.0]\)
- **`duration_seconds`**: optional float (0.1–3600.0) or `null`

#### 200 response

```json
{
  "success": true,
  "session_id": "sess_ab12cd34ef56",
  "data": {
    "frame": 1,
    "floaters_count": 5,
    "intensity_used": 0.5
  }
}
```

#### Validation errors (422)
FastAPI automatically returns a `422` with details if the input is invalid (like `intensity > 1.0`).

---

## Local usage

### Install + run

```bash
cd VIRTUOUS/floater-simulation-service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 run.py
```

### Docs UI

- Swagger UI: `http://localhost:8000/docs` (handy if you want to try requests)

### Tests

```bash
cd VIRTUOUS/floater-simulation-service
.venv/bin/pytest tests/ -v
```

