"""Serve the built frontend and FastAPI API from one local origin."""
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

from app.main import app


ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"


if not FRONTEND_DIST.exists():
    raise RuntimeError(f"Frontend build not found: {FRONTEND_DIST}")

app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5173, log_level="info")
