import pytest
from backend.app.core.database import engine, init_db, SessionLocal
from backend.app.models.db_models import Base

@pytest.fixture(autouse=True)
def clean_database():
    """Ensure clean tables exist before each test and clear rows cleanly."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Delete rows in reverse dependency order
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()
    yield
    # Keep schema ready for next test
