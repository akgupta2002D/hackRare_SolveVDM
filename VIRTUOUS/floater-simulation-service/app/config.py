"""
Environment-based settings: port, host, CORS origins, app name. Change here
when you deploy or switch environments.
"""
import os

# Server
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# CORS: let Express (port 5050) and frontend (5173) call this service
CORS_ORIGINS = ["http://localhost:5050", "http://localhost:5173"]

APP_NAME = "floater-simulation-service"
