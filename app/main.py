from fastapi import FastAPI
from app.database.database import engine, Base
from app.database import models  # Ensures models are registered with Base metadata
from app.routes import auth, tasks
from app.exceptions.handlers import register_exception_handlers

# Auto-create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Task Management API",
    description="A production-style REST API demonstrating Authentication, JWT, and Ownership-based Authorization.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register Exception Handlers
register_exception_handlers(app)

# Register Routers
app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/", tags=["Health Check"])
def root():
    """
    Root Health Check Endpoint.
    Returns basic API metadata to confirm the service is online.
    """
    return {
        "message": "Welcome to Smart Task Management API",
        "status": "healthy",
        "version": "1.0.0"
    }
