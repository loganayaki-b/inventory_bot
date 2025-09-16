# database/connection.py
from sqlalchemy.orm import Session
from .models import SessionLocal

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()