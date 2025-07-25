"""
FastAPI dependencies for dependency injection throughout the application.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.config import settings
from app.core.logging import logger
from typing import Generator


def get_current_user_id() -> str:
    """
    Placeholder for user authentication dependency.
    This would typically decode a JWT token and return the user ID.
    """
    # TODO: Implement proper JWT authentication
    return "placeholder-user-id"


def log_request_info():
    """
    Dependency to log request information.
    """
    def _log_request(request_id: str = None):
        logger.info(f"Processing request: {request_id or 'unknown'}")
        return request_id
    
    return _log_request


def validate_openai_config():
    """
    Dependency to validate OpenAI configuration is present.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key not configured"
        )
    return True


def get_database_session() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    """
    return get_db()