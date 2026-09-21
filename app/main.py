from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.database import engine
from app.routers.jobs import router as jobs_router
from app.routers.auth import router as auth_router
from app.routers.telegram import router as telegram_router

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(title="PulseGrid")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(auth_router)
app.include_router(telegram_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/database")
def database_health_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"database": result.scalar()}


if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="frontend-assets",
        )

    @app.get("/")
    def spa_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        reserved = ("api/", "health", "docs", "redoc", "openapi.json")
        if full_path.startswith(reserved) or full_path in {
            "docs",
            "redoc",
            "openapi.json",
        }:
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

else:

    @app.get("/")
    def root():
        return {
            "message": "PulseGrid API",
            "dashboard": "Build frontend with: cd frontend && npm install && npm run build",
        }
