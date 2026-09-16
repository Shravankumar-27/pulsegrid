from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine
from app.routers.jobs import router as jobs_router
from app.routers.auth import router as auth_router
from app.routers.telegram import router as telegram_router

from app.models.user import User
from app.models.tracking_job import TrackingJob

app = FastAPI(title="PulseGrid")

app.include_router(jobs_router)
app.include_router(auth_router)
app.include_router(telegram_router)

@app.get("/")
def root():
    return {"message": "Welcome to PulseGrid! and its runnninggggg"}
    
@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/health/database")
def database_health_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"database": result.scalar()}