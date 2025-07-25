"""
Idea generation routes for AI-powered idea creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.dependencies import get_database_session, get_current_user_id, validate_openai_config
from app.schemas.idea import IdeaGenerationRequest, IdeaResponse, IdeaCreate
from app.schemas.outputs.idea_generation import IdeaGenerationOutput
from app.services.idea_service import IdeaService
from app.services.llm_service import LLMService
from app.core.logging import logger

router = APIRouter(prefix="/idea-generation", tags=["idea-generation"])


@router.post("/generate", response_model=IdeaGenerationOutput)
async def generate_ideas(
    request: IdeaGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(validate_openai_config)
):
    """
    Generate new ideas using AI based on provided context.
    
    Args:
        request: Idea generation request with context and parameters
        background_tasks: FastAPI background tasks
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Generated ideas with structured output
        
    Raises:
        HTTPException: If generation fails
    """
    logger.info(f"Generating ideas for user {user_id} with context: {request.context[:100]}...")
    
    idea_service = IdeaService(db)
    llm_service = LLMService(db)
    
    try:
        # Generate ideas using LLM service
        generation_output = await llm_service.generate_ideas(
            context=request.context,
            user_id=user_id,
            num_ideas=request.num_ideas,
            temperature=request.temperature,
            category=request.category,
            target_audience=request.target_audience,
            constraints=request.constraints,
            team_id=request.team_id
        )
        
        # Store generated ideas in background
        background_tasks.add_task(
            _store_generated_ideas,
            generation_output,
            request,
            user_id,
            db
        )
        
        logger.info(f"Successfully generated {len(generation_output.ideas)} ideas")
        return generation_output
        
    except Exception as e:
        logger.error(f"Error generating ideas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate ideas"
        )


@router.post("/iterate/{idea_id}", response_model=IdeaResponse)
async def iterate_idea(
    idea_id: int,
    feedback: str,
    specific_improvements: List[str] = [],
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(validate_openai_config)
):
    """
    Iterate and improve an existing idea based on feedback.
    
    Args:
        idea_id: ID of the idea to iterate
        feedback: Feedback for improvement
        specific_improvements: Specific areas to improve
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        Updated idea
        
    Raises:
        HTTPException: If idea not found or iteration fails
    """
    logger.info(f"Iterating idea {idea_id} for user {user_id}")
    
    idea_service = IdeaService(db)
    llm_service = LLMService(db)
    
    try:
        # Get existing idea
        idea = idea_service.get_idea(idea_id)
        if not idea:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found"
            )
        
        # Check ownership/permissions
        if idea.creator_id != int(user_id):
            # TODO: Check team permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this idea"
            )
        
        # Iterate idea using LLM service
        iteration_output = await llm_service.iterate_idea(
            idea=idea,
            feedback=feedback,
            specific_improvements=specific_improvements,
            user_id=user_id
        )
        
        # Update idea with improvements
        updated_idea = idea_service.update_idea_from_iteration(idea_id, iteration_output)
        
        logger.info(f"Successfully iterated idea {idea_id}")
        return IdeaResponse.from_orm(updated_idea)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error iterating idea {idea_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to iterate idea"
        )


@router.get("/batch-generate", response_model=List[IdeaGenerationOutput])
async def batch_generate_ideas(
    contexts: List[str],
    num_ideas_per_context: int = 3,
    category: str = None,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(get_current_user_id),
    _: bool = Depends(validate_openai_config)
):
    """
    Generate ideas for multiple contexts in batch.
    
    Args:
        contexts: List of contexts for idea generation
        num_ideas_per_context: Number of ideas to generate per context
        category: Optional category filter
        db: Database session
        user_id: Current authenticated user ID
        
    Returns:
        List of generation outputs for each context
        
    Raises:
        HTTPException: If batch generation fails
    """
    if len(contexts) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 contexts allowed per batch"
        )
    
    logger.info(f"Batch generating ideas for {len(contexts)} contexts")
    
    llm_service = LLMService(db)
    results = []
    
    try:
        for context in contexts:
            generation_output = await llm_service.generate_ideas(
                context=context,
                user_id=user_id,
                num_ideas=num_ideas_per_context,
                category=category
            )
            results.append(generation_output)
        
        logger.info(f"Successfully completed batch generation for {len(contexts)} contexts")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch idea generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate ideas in batch"
        )


async def _store_generated_ideas(
    generation_output: IdeaGenerationOutput,
    request: IdeaGenerationRequest,
    user_id: str,
    db: Session
):
    """
    Background task to store generated ideas in the database.
    
    Args:
        generation_output: Generated ideas output
        request: Original request
        user_id: User ID
        db: Database session
    """
    try:
        idea_service = IdeaService(db)
        
        for generated_idea in generation_output.ideas:
            idea_create = IdeaCreate(
                title=generated_idea.title,
                description=generated_idea.description,
                category=request.category,
                tags=generated_idea.key_benefits[:5],  # Use first 5 benefits as tags
                problem_statement=request.context,
                solution_details=generated_idea.implementation_approach,
                target_audience=request.target_audience,
                team_id=request.team_id
            )
            
            idea_service.create_idea(idea_create, creator_id=int(user_id), ai_generated=True)
        
        logger.info(f"Stored {len(generation_output.ideas)} generated ideas for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error storing generated ideas: {e}")
        # Don't raise here as this is a background task