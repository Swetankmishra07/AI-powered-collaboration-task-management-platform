from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import models  # Ensures models are registered with Base metadata
from app.database.database import get_db
from app.core.config import settings
from app.core.redis import redis_cache
from app.routes import auth, comments, notifications, projects, tasks, teams, users
from app.exceptions.handlers import register_exception_handlers

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A production-style REST API demonstrating Authentication, JWT, and Ownership-based Authorization.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
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
