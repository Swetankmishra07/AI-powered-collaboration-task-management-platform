from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import models  # Ensures models are registered with Base metadata
from app.database.database import get_db
from app.core.config import settings
from app.core.redis import redis_cache
from app.routes import ai, attachments, auth, comments, notifications, projects, tasks, teams, users, websocket
from app.exceptions.handlers import register_exception_handlers
from app.services.background_job_service import BackgroundJobRunner


background_job_runner = BackgroundJobRunner()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.BACKGROUND_JOBS_ENABLED:
        background_job_runner.start()
    try:
        yield
    finally:
        if settings.BACKGROUND_JOBS_ENABLED:
            background_job_runner.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A production-style REST API demonstrating Authentication, JWT, and Ownership-based Authorization.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register Exception Handlers
register_exception_handlers(app)

# Register Routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(projects.router)
app.include_router(comments.router)
app.include_router(notifications.router)
app.include_router(websocket.router)
app.include_router(ai.router)
app.include_router(attachments.router)

allowed_origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


@app.get("/", tags=["Health Check"])
def root():
    """
    Root Health Check Endpoint.
    Returns basic API metadata to confirm the service is online.
    """
    return {
        "message": "Welcome to Smart Task Management API",
        "status": "healthy",
        "version": settings.VERSION
    }


@app.get("/health/database", tags=["Health Check"])
def database_health(db: Session = Depends(get_db)):
    """Check connectivity to the explicitly configured database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configured database is unavailable.",
        ) from exc

    return {"status": "healthy", "database": "connected"}


@app.get("/health/redis", tags=["Health Check"])
def redis_health():
    """Report optional Redis cache connectivity without changing API behavior."""
    if not settings.REDIS_URL:
        return {"status": "disabled", "redis": "not_configured"}
    if not redis_cache.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configured Redis cache is unavailable.",
        )
    return {"status": "healthy", "redis": "connected"}
