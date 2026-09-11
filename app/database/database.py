import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_engine():
    """
    Creates SQLAlchemy Engine with fallback to SQLite if MySQL is unavailable.
    """
    database_url = settings.DATABASE_URL
    if database_url.startswith("sqlite"):
        return create_engine(database_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
    
    try:
        # Test connecting to MySQL
        eng = create_engine(database_url, connect_args={}, pool_pre_ping=True)
        with eng.connect() as conn:
            pass
        return eng
    except Exception as e:
        logger.warning(f"MySQL unavailable ({e}). Falling back to SQLite for local execution.")
        fallback_url = "sqlite:///./task_db.sqlite3"
        return create_engine(fallback_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)

engine = _get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    FastAPI Dependency that provides a transactional database session per HTTP request.
    Closes session automatically when request lifecycle ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
