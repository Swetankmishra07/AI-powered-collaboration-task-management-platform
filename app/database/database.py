from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings

def _create_engine():
    """
    Creates the configured SQLAlchemy engine without changing databases.
    """
    database_url = settings.DATABASE_URL
    if database_url.startswith("sqlite"):
        engine_options = {
            "connect_args": {"check_same_thread": False},
            "pool_pre_ping": True,
        }
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_options["poolclass"] = StaticPool
        return create_engine(database_url, **engine_options)

    return create_engine(database_url, pool_pre_ping=True)

engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Register post-commit realtime delivery without retaining any Session objects.
from app.services import realtime_service  # noqa: F401, E402


def get_db():
    """
    FastAPI Dependency that provides a transactional database session per HTTP request.
    Closes session automatically when request lifecycle ends.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
