"""
Feedback routes for collecting and managing feedback on ideas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_database_session, get_current_user_id
from app.services.feedback_service import FeedbackService
from app.services.idea_service import IdeaService
from app.core.logging import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    idea_id: int
    content: str = Field(..., min_length=10, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=10)
    feedback_type: str = Field(default="general", regex="^(general|suggestion|critique|praise)$")
    is_anonymous: bool = False


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: int
    idea_id: int
    content: str
    rating: Optional[int]
    feedback_type: str
    is_anonymous: bool
    author_id: Optional[int]
    author_name: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class FeedbackSummary(BaseModel):
    """Schema for feedback summary."""
    idea_id: int
    total_feedback_count: int
    average_rating: Optional[float]
    sentiment_score: Optional[float]
    key_themes: List[str]
    improvement_suggestions: List[str]


@router.post("/create", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Create feedback for an idea.
    
    Args:
        feedback_data: Feedback creation data
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Created feedback
        
    Raises:
        HTTPException: If idea not found or feedback creation fails
    """
    logger.info(f"Creating feedback for idea {feedback_data.idea_id} by user {user_id}")
    
    idea_service = IdeaService(db)
    feedback_service = FeedbackService(db)
    
    try:
        # Check if idea exists and user can access it
        if not idea_service.can_user_access_idea(feedback_data.idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found or access denied"
            )
        
        # Create feedback
        feedback = feedback_service.create_feedback(
            idea_id=feedback_data.idea_id,
            content=feedback_data.content,
            author_id=int(user_id) if not feedback_data.is_anonymous else None,
            rating=feedback_data.rating,
            feedback_type=feedback_data.feedback_type,
            is_anonymous=feedback_data.is_anonymous
        )
        
        logger.info(f"Successfully created feedback {feedback.id}")
        return FeedbackResponse.from_orm(feedback)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feedback"
        )


@router.get("/idea/{idea_id}", response_model=List[FeedbackResponse])
async def get_idea_feedback(
    idea_id: int,
    limit: int = 20,
    offset: int = 0,
    feedback_type: Optional[str] = None,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get feedback for a specific idea.
    
    Args:
        idea_id: ID of the idea
        limit: Maximum number of feedback items to return
        offset: Number of feedback items to skip
        feedback_type: Optional filter by feedback type
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        List of feedback for the idea
        
    Raises:
        HTTPException: If idea not found or access denied
    """
    logger.info(f"Getting feedback for idea {idea_id}")
    
    idea_service = IdeaService(db)
    feedback_service = FeedbackService(db)
    
    try:
        # Check permissions
        if not idea_service.can_user_access_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found or access denied"
            )
        
        # Get feedback
        feedback_list = feedback_service.get_idea_feedback(
            idea_id, limit, offset, feedback_type
        )
        
        logger.info(f"Retrieved {len(feedback_list)} feedback items for idea {idea_id}")
        return [FeedbackResponse.from_orm(feedback) for feedback in feedback_list]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback for idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feedback"
        )


@router.get("/summary/{idea_id}", response_model=FeedbackSummary)
async def get_feedback_summary(
    idea_id: int,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get AI-generated feedback summary for an idea.
    
    Args:
        idea_id: ID of the idea
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Feedback summary with insights
        
    Raises:
        HTTPException: If idea not found or summary generation fails
    """
    logger.info(f"Generating feedback summary for idea {idea_id}")
    
    idea_service = IdeaService(db)
    feedback_service = FeedbackService(db)
    
    try:
        # Check permissions
        if not idea_service.can_user_access_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found or access denied"
            )
        
        # Generate summary
        summary = await feedback_service.generate_feedback_summary(idea_id, user_id)
        
        logger.info(f"Generated feedback summary for idea {idea_id}")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating feedback summary for idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate feedback summary"
        )


@router.put("/update/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: int,
    content: Optional[str] = None,
    rating: Optional[int] = Field(None, ge=1, le=10),
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Update feedback (only by the author).
    
    Args:
        feedback_id: ID of the feedback to update
        content: New content
        rating: New rating
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Updated feedback
        
    Raises:
        HTTPException: If feedback not found or unauthorized
    """
    logger.info(f"Updating feedback {feedback_id} by user {user_id}")
    
    feedback_service = FeedbackService(db)
    
    try:
        # Update feedback
        updated_feedback = feedback_service.update_feedback(
            feedback_id, int(user_id), content, rating
        )
        
        if not updated_feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found or unauthorized"
            )
        
        logger.info(f"Successfully updated feedback {feedback_id}")
        return FeedbackResponse.from_orm(updated_feedback)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback {feedback_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feedback"
        )


@router.delete("/delete/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete feedback (only by the author or idea owner).
    
    Args:
        feedback_id: ID of the feedback to delete
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If feedback not found or unauthorized
    """
    logger.info(f"Deleting feedback {feedback_id} by user {user_id}")
    
    feedback_service = FeedbackService(db)
    
    try:
        # Delete feedback
        success = feedback_service.delete_feedback(feedback_id, int(user_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found or unauthorized"
            )
        
        logger.info(f"Successfully deleted feedback {feedback_id}")
        return {"message": "Feedback deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting feedback {feedback_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete feedback"
        )