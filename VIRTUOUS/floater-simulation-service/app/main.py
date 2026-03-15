"""
FastAPI app entry: wires CORS for Express, mounts all routes. This is what
uvicorn runs (app.main:app).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routes import router

app = FastAPI(
    title="floater-simulation-service",
    description="Microservice for VIRTUOUS; Express backend calls this.",
)

# Let Express and frontend call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
