from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.database.indexes import create_indexes
from app.auth.router import router as auth_router
from app.admin.router import router as admin_router
from app.verify.router import router as verify_router
from app.notifications.router import router as notifications_router
from app.access.router import router as access_router
from app.audit.router import router as audit_router
from app.users.router import router as users_router
from app.patients.router import router as patients_router
from app.doctors.router import router as doctors_router
from app.reports.router import router as reports_router
from app.reports.trends_router import router as trends_router
from app.prescriptions.router import router as prescriptions_router
from app.history.router import router as history_router
from app.core.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

logger = logging.getLogger("healthcare_system")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Healthcare System API")
    await connect_to_mongo()
    await create_indexes()
    stop_reminders = None
    try:
        from app.notifications.scheduler import start_reminder_scheduler

        stop_reminders = start_reminder_scheduler()
    except Exception as exc:
        logger.warning(f"Reminder scheduler not started: {exc}")
    yield
    logger.info("Shutting down Healthcare System API")
    if stop_reminders is not None:
        try:
            stop_reminders()
        except Exception:
            pass
    await close_mongo_connection()


app = FastAPI(
    title="Intelligent Medical Report Interpretation and Digital Healthcare System",
    description="AI-powered medical report interpretation and digital prescription management system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health", tags=["Health"])
async def health_check():
    # Additive AI fields let the dashboard show the real engine state
    # (model name is public config; the API key itself is never exposed).
    return {
        "status": "healthy",
        "version": "1.0.0",
        "ai_configured": bool(settings.omni_route_api_key),
        "ai_model": settings.omni_route_model,
    }


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Healthcare System API", "docs": "/docs", "redoc": "/redoc"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(verify_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(access_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(doctors_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(prescriptions_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
