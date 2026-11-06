import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.app.core.config import settings
from backend.app.models.db_models import Base

# Ensure SQLite path directory exists if applicable
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    sqlite_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(sqlite_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# For SQLite, check_same_thread=False allows FastAPI multi-threaded requests
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    """Create all database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for API routes to obtain a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

