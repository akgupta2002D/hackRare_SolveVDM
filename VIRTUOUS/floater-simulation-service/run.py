"""
Starts the service with  python run.py  from this folder. Uses config for host/port.
"""
import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
