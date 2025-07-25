"""
Evaluation routes for AI-powered idea evaluation and analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_database_session, get_current_user_id, validate_openai_config
from app.schemas.idea import IdeaEvaluation, IdeaResponse
from app.schemas.outputs.evaluation import IdeaEvaluationOutput, ComparisonEvaluationOutput
from app.services.idea_service import IdeaService
from app.services.evaluation_service import EvaluationService
from app.core.logging import logger

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/evaluate/{idea_id}", response_model=IdeaEvaluationOutput)
async def evaluate_idea(
    idea_id: int,
    custom_criteria: Optional[List[dict]] = None,
    detailed_analysis: bool = True,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(validate_openai_config)
):
    """
    Evaluate a specific idea using AI-powered analysis.
    
    Args:
        idea_id: ID of the idea to evaluate
        custom_criteria: Optional custom evaluation criteria
        detailed_analysis: Whether to perform detailed analysis
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Comprehensive evaluation results
        
    Raises:
        HTTPException: If idea not found or evaluation fails
    """
    logger.info(f"Evaluating idea {idea_id} for user {user_id}")
    
    idea_service = IdeaService(db)
    evaluation_service = EvaluationService(db)
    
    try:
        # Get the idea
        idea = idea_service.get_idea(idea_id)
        if not idea:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found"
            )
        
        # Check permissions (ideas can be evaluated by team members)
        if not idea_service.can_user_access_idea(idea_id, int(user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to evaluate this idea"
            )
        
        # Perform evaluation
        evaluation_output = await evaluation_service.evaluate_idea(
            idea=idea,
            user_id=user_id,
            custom_criteria=custom_criteria,
            detailed_analysis=detailed_analysis
        )
        
        # Store evaluation results
        evaluation_service.store_evaluation_results(idea_id, evaluation_output)
        
        logger.info(f"Successfully evaluated idea {idea_id} with score {evaluation_output.overall_score}")
        return evaluation_output
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate idea"
        )


@router.post("/compare", response_model=ComparisonEvaluationOutput)
async def compare_ideas(
    idea_ids: List[int],
    comparison_criteria: Optional[List[dict]] = None,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(validate_openai_config)
):
    """
    Compare multiple ideas side by side using AI analysis.
    
    Args:
        idea_ids: List of idea IDs to compare (2-10 ideas)
        comparison_criteria: Optional custom comparison criteria
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Comparative analysis results
        
    Raises:
        HTTPException: If ideas not found or comparison fails
    """
    if len(idea_ids) < 2 or len(idea_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can compare between 2 and 10 ideas"
        )
    
    logger.info(f"Comparing {len(idea_ids)} ideas for user {user_id}")
    
    idea_service = IdeaService(db)
    evaluation_service = EvaluationService(db)
    
    try:
        # Get all ideas
        ideas = []
        for idea_id in idea_ids:
            idea = idea_service.get_idea(idea_id)
            if not idea:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Idea {idea_id} not found"
                )
            
            # Check permissions
            if not idea_service.can_user_access_idea(idea_id, int(user_id)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not authorized to access idea {idea_id}"
                )
            
            ideas.append(idea)
        
        # Perform comparison
        comparison_output = await evaluation_service.compare_ideas(
            ideas=ideas,
            user_id=user_id,
            comparison_criteria=comparison_criteria
        )
        
        logger.info(f"Successfully compared {len(ideas)} ideas")
        return comparison_output
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing ideas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare ideas"
        )


@router.put("/update-evaluation/{idea_id}", response_model=IdeaResponse)
async def update_idea_evaluation(
    idea_id: int,
    evaluation_data: IdeaEvaluation,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Update manual evaluation data for an idea.
    
    Args:
        idea_id: ID of the idea to update
        evaluation_data: Manual evaluation data
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Updated idea with evaluation data
        
    Raises:
        HTTPException: If idea not found or update fails
    """
    logger.info(f"Updating evaluation for idea {idea_id} by user {user_id}")
    
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
        
        # Update evaluation
        updated_idea = idea_service.update_idea_evaluation(idea_id, evaluation_data)
        
        logger.info(f"Successfully updated evaluation for idea {idea_id}")
        return IdeaResponse.from_orm(updated_idea)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating evaluation for idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update evaluation"
        )


@router.get("/batch-evaluate", response_model=List[IdeaEvaluationOutput])
async def batch_evaluate_ideas(
    idea_ids: List[int],
    quick_evaluation: bool = True,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(validate_openai_config)
):
    """
    Evaluate multiple ideas in batch.
    
    Args:
        idea_ids: List of idea IDs to evaluate
        quick_evaluation: Whether to perform quick evaluation
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        List of evaluation results
        
    Raises:
        HTTPException: If evaluation fails
    """
    if len(idea_ids) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 ideas allowed per batch evaluation"
        )
    
    logger.info(f"Batch evaluating {len(idea_ids)} ideas for user {user_id}")
    
    idea_service = IdeaService(db)
    evaluation_service = EvaluationService(db)
    results = []
    
    try:
        for idea_id in idea_ids:
            idea = idea_service.get_idea(idea_id)
            if not idea:
                logger.warning(f"Idea {idea_id} not found, skipping")
                continue
            
            if not idea_service.can_user_access_idea(idea_id, int(user_id)):
                logger.warning(f"No access to idea {idea_id}, skipping")
                continue
            
            try:
                evaluation_output = await evaluation_service.evaluate_idea(
                    idea=idea,
                    user_id=user_id,
                    detailed_analysis=not quick_evaluation
                )
                
                evaluation_service.store_evaluation_results(idea_id, evaluation_output)
                results.append(evaluation_output)
                
            except Exception as e:
                logger.error(f"Error evaluating idea {idea_id}: {e}")
                continue
        
        logger.info(f"Successfully completed batch evaluation for {len(results)} ideas")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch evaluation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete batch evaluation"
        )