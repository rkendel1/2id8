"""
LLM logs routes for accessing AI interaction history and debugging.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.dependencies import get_database_session, get_current_user_id
from app.schemas.llm_log import LLMLogResponse, LLMLogListResponse
from app.services.llm_service import LLMService
from app.models.llm_log import LLMOperation, LLMStatus
from app.core.logging import logger

router = APIRouter(prefix="/llm-logs", tags=["llm-logs"])


@router.get("/", response_model=List[LLMLogListResponse])
async def get_llm_logs(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    operation_type: Optional[LLMOperation] = None,
    status: Optional[LLMStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get LLM logs for the current user with filtering options.
    
    Args:
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        operation_type: Filter by operation type
        status: Filter by status
        start_date: Filter by start date
        end_date: Filter by end date
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        List of LLM logs
        
    Raises:
        HTTPException: If retrieval fails
    """
    logger.info(f"Getting LLM logs for user {user_id}")
    
    llm_service = LLMService(db)
    
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)  # Default to last 30 days
        
        # Get logs
        logs = llm_service.get_user_llm_logs(
            user_id=int(user_id),
            limit=limit,
            offset=offset,
            operation_type=operation_type,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Retrieved {len(logs)} LLM logs for user {user_id}")
        return [LLMLogListResponse.from_orm(log) for log in logs]
        
    except Exception as e:
        logger.error(f"Error getting LLM logs for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve LLM logs"
        )


@router.get("/{log_id}", response_model=LLMLogResponse)
async def get_llm_log_detail(
    log_id: int,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get detailed information for a specific LLM log.
    
    Args:
        log_id: ID of the LLM log
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Detailed LLM log information
        
    Raises:
        HTTPException: If log not found or access denied
    """
    logger.info(f"Getting LLM log {log_id} for user {user_id}")
    
    llm_service = LLMService(db)
    
    try:
        # Get log
        log = llm_service.get_llm_log_by_id(log_id)
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LLM log not found"
            )
        
        # Check ownership
        if log.user_id != int(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this log"
            )
        
        logger.info(f"Retrieved LLM log {log_id}")
        return LLMLogResponse.from_orm(log)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LLM log {log_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve LLM log"
        )


@router.get("/idea/{idea_id}", response_model=List[LLMLogListResponse])
async def get_idea_llm_logs(
    idea_id: int,
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get LLM logs associated with a specific idea.
    
    Args:
        idea_id: ID of the idea
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        List of LLM logs for the idea
        
    Raises:
        HTTPException: If idea not found or access denied
    """
    logger.info(f"Getting LLM logs for idea {idea_id}")
    
    llm_service = LLMService(db)
    
    try:
        # Get logs for idea
        logs = llm_service.get_idea_llm_logs(
            idea_id=idea_id,
            user_id=int(user_id),
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Retrieved {len(logs)} LLM logs for idea {idea_id}")
        return [LLMLogListResponse.from_orm(log) for log in logs]
        
    except Exception as e:
        logger.error(f"Error getting LLM logs for idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve idea LLM logs"
        )


@router.get("/analytics/usage")
async def get_usage_analytics(
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get LLM usage analytics for the current user.
    
    Args:
        days: Number of days to analyze
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Usage analytics data
        
    Raises:
        HTTPException: If analytics generation fails
    """
    logger.info(f"Generating LLM usage analytics for user {user_id}")
    
    llm_service = LLMService(db)
    
    try:
        # Generate analytics
        analytics = llm_service.get_user_usage_analytics(
            user_id=int(user_id),
            days=days
        )
        
        logger.info(f"Generated usage analytics for user {user_id}")
        return analytics
        
    except Exception as e:
        logger.error(f"Error generating usage analytics for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate usage analytics"
        )


@router.get("/analytics/costs")
async def get_cost_analytics(
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get LLM cost analytics for the current user.
    
    Args:
        days: Number of days to analyze
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Cost analytics data
        
    Raises:
        HTTPException: If cost analytics generation fails
    """
    logger.info(f"Generating LLM cost analytics for user {user_id}")
    
    llm_service = LLMService(db)
    
    try:
        # Generate cost analytics
        cost_analytics = llm_service.get_user_cost_analytics(
            user_id=int(user_id),
            days=days
        )
        
        logger.info(f"Generated cost analytics for user {user_id}")
        return cost_analytics
        
    except Exception as e:
        logger.error(f"Error generating cost analytics for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cost analytics"
        )


@router.delete("/{log_id}")
async def delete_llm_log(
    log_id: int,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete a specific LLM log (for privacy/cleanup).
    
    Args:
        log_id: ID of the LLM log to delete
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If log not found or access denied
    """
    logger.info(f"Deleting LLM log {log_id} for user {user_id}")
    
    llm_service = LLMService(db)
    
    try:
        # Delete log
        success = llm_service.delete_llm_log(log_id, int(user_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LLM log not found or unauthorized"
            )
        
        logger.info(f"Successfully deleted LLM log {log_id}")
        return {"message": "LLM log deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting LLM log {log_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete LLM log"
        )