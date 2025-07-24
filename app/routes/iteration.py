"""
Iteration routes for idea refinement and improvement workflows.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_database_session, get_current_user_id, validate_openai_config
from app.schemas.idea import IdeaResponse, IdeaUpdate
from app.schemas.outputs.idea_generation import IdeaIterationOutput
from app.services.idea_service import IdeaService
from app.services.llm_service import LLMService
from app.core.logging import logger

router = APIRouter(prefix="/iteration", tags=["iteration"])


@router.post("/refine/{idea_id}", response_model=IdeaIterationOutput)
async def refine_idea(
    idea_id: int,
    feedback: str,
    focus_areas: List[str] = [],
    iteration_goals: List[str] = [],
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(validate_openai_config)
):
    """
    Refine an idea based on specific feedback and focus areas.
    
    Args:
        idea_id: ID of the idea to refine
        feedback: Detailed feedback for refinement
        focus_areas: Specific areas to focus on during refinement
        iteration_goals: Goals for this iteration
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Iteration results with original and improved idea
        
    Raises:
        HTTPException: If idea not found or refinement fails
    """
    logger.info(f"Refining idea {idea_id} for user {user_id}")
    
    idea_service = IdeaService(db)
    llm_service = LLMService(db)
    
    try:
        # Get the idea
        idea = idea_service.get_idea(idea_id)
        if not idea:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found"
            )
        
        # Check permissions
        if not idea_service.can_user_modify_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this idea"
            )
        
        # Perform refinement
        iteration_output = await llm_service.refine_idea(
            idea=idea,
            feedback=feedback,
            focus_areas=focus_areas,
            iteration_goals=iteration_goals,
            user_id=user_id
        )
        
        # Create iteration history record
        idea_service.create_iteration_history(idea_id, iteration_output, user_id)
        
        logger.info(f"Successfully refined idea {idea_id}")
        return iteration_output
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refining idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refine idea"
        )


@router.post("/apply-refinement/{idea_id}", response_model=IdeaResponse)
async def apply_refinement(
    idea_id: int,
    iteration_output: IdeaIterationOutput,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Apply refinement results to update the original idea.
    
    Args:
        idea_id: ID of the idea to update
        iteration_output: Refinement results to apply
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Updated idea
        
    Raises:
        HTTPException: If idea not found or update fails
    """
    logger.info(f"Applying refinement to idea {idea_id} for user {user_id}")
    
    idea_service = IdeaService(db)
    
    try:
        # Get the idea
        idea = idea_service.get_idea(idea_id)
        if not idea:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found"
            )
        
        # Check permissions
        if not idea_service.can_user_modify_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this idea"
            )
        
        # Apply refinement
        updated_idea = idea_service.apply_iteration_results(idea_id, iteration_output)
        
        logger.info(f"Successfully applied refinement to idea {idea_id}")
        return IdeaResponse.from_orm(updated_idea)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying refinement to idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply refinement"
        )


@router.get("/history/{idea_id}")
async def get_iteration_history(
    idea_id: int,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get iteration history for an idea.
    
    Args:
        idea_id: ID of the idea
        limit: Maximum number of iterations to return
        offset: Number of iterations to skip
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        List of iteration history records
        
    Raises:
        HTTPException: If idea not found or access denied
    """
    logger.info(f"Getting iteration history for idea {idea_id}")
    
    idea_service = IdeaService(db)
    
    try:
        # Check permissions
        if not idea_service.can_user_access_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this idea"
            )
        
        # Get iteration history
        history = idea_service.get_iteration_history(idea_id, limit, offset)
        
        logger.info(f"Retrieved {len(history)} iteration records for idea {idea_id}")
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting iteration history for idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get iteration history"
        )


@router.post("/revert/{idea_id}/{iteration_id}", response_model=IdeaResponse)
async def revert_to_iteration(
    idea_id: int,
    iteration_id: int,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Revert an idea to a specific iteration.
    
    Args:
        idea_id: ID of the idea
        iteration_id: ID of the iteration to revert to
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Reverted idea
        
    Raises:
        HTTPException: If idea/iteration not found or revert fails
    """
    logger.info(f"Reverting idea {idea_id} to iteration {iteration_id}")
    
    idea_service = IdeaService(db)
    
    try:
        # Check permissions
        if not idea_service.can_user_modify_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this idea"
            )
        
        # Revert to iteration
        reverted_idea = idea_service.revert_to_iteration(idea_id, iteration_id)
        
        logger.info(f"Successfully reverted idea {idea_id} to iteration {iteration_id}")
        return IdeaResponse.from_orm(reverted_idea)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reverting idea {idea_id} to iteration {iteration_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revert idea"
        )


@router.post("/branch/{idea_id}", response_model=IdeaResponse)
async def branch_idea(
    idea_id: int,
    branch_description: str,
    iteration_focus: List[str] = [],
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new branch (copy) of an idea for alternative exploration.
    
    Args:
        idea_id: ID of the idea to branch
        branch_description: Description of the branch purpose
        iteration_focus: Focus areas for the branch
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        New branched idea
        
    Raises:
        HTTPException: If idea not found or branching fails
    """
    logger.info(f"Branching idea {idea_id} for user {user_id}")
    
    idea_service = IdeaService(db)
    
    try:
        # Check permissions
        if not idea_service.can_user_access_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this idea"
            )
        
        # Create branch
        branched_idea = idea_service.create_idea_branch(
            idea_id, 
            branch_description, 
            iteration_focus, 
            int(user_id)
        )
        
        logger.info(f"Successfully branched idea {idea_id} to new idea {branched_idea.id}")
        return IdeaResponse.from_orm(branched_idea)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error branching idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to branch idea"
        )