"""
Database session management.
"""

from typing import Generator
from sqlalchemy.orm import Session
from app.database.base import SessionLocal
from app.core.logging import logger


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Database session instance
    """
    db = SessionLocal()
    try:
        logger.debug("Creating database session")
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        logger.debug("Closing database session")
        db.close()