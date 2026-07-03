import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import SessionLocal,engine,Base
from app.services.auth_service import seed_admin
from app.tasks.scheduler import start_scheduler,stop_scheduler

import app.models  # noqa:F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger=logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app:FastAPI):
    logger.info("Starting up...")
    Base.metadata.create_all(bind=engine)

    db=SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()

    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shut down complete")


app=FastAPI(
    title="Healthcare Appointment Manager",
    description="Appointment booking system with AI summaries,email notifications,and calendar sync.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import auth,admin,patients,doctors,appointments

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(appointments.router)


@app.get("/health",tags=["Health"])
def health_check():
    return {
"status":"healthy",
"service":"Healthcare Appointment Manager",
    }

app.mount("/",StaticFiles(directory="frontend",html=True),name="frontend")
