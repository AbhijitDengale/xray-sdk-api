from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/xray_db")

# For development, use SQLite if PostgreSQL not available
if "postgresql" in DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        engine.connect()
    except Exception:
        print("PostgreSQL not available, falling back to SQLite")
        DATABASE_URL = "sqlite:///./xray_data.db"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    from .models import Base
    Base.metadata.create_all(bind=engine)