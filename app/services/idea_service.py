"""
Idea service for idea lifecycle management.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.idea import Idea, IdeaStatus, IdeaPriority
from app.models.team import Team, TeamMember
from app.schemas.idea import IdeaCreate, IdeaUpdate, IdeaEvaluation
from app.schemas.outputs.idea_generation import IdeaIterationOutput
from app.core.logging import logger
import json


class IdeaService:
    """Service class for idea management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_idea(self, idea_id: int) -> Optional[Idea]:
        """Get idea by ID."""
        return self.db.query(Idea).filter(Idea.id == idea_id).first()
    
    def get_user_ideas(
        self, 
        user_id: int, 
        limit: int = 20, 
        offset: int = 0,
        status: Optional[IdeaStatus] = None,
        category: Optional[str] = None
    ) -> List[Idea]:
        """Get ideas created by a user."""
        query = self.db.query(Idea).filter(Idea.creator_id == user_id)
        
        if status:
            query = query.filter(Idea.status == status)
        
        if category:
            query = query.filter(Idea.category == category)
        
        return query.order_by(Idea.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_team_ideas(
        self, 
        team_id: int, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Idea]:
        """Get ideas for a team."""
        return (
            self.db.query(Idea)
            .filter(Idea.team_id == team_id)
            .order_by(Idea.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def create_idea(
        self, 
        idea_data: IdeaCreate, 
        creator_id: int,
        ai_generated: bool = False,
        ai_confidence_score: Optional[float] = None
    ) -> Idea:
        """
        Create a new idea.
        
        Args:
            idea_data: Idea creation data
            creator_id: ID of the user creating the idea
            ai_generated: Whether the idea was AI-generated
            ai_confidence_score: Confidence score if AI-generated
            
        Returns:
            Created idea
        """
        try:
            idea = Idea(
                title=idea_data.title,
                description=idea_data.description,
                category=idea_data.category,
                tags=idea_data.tags,
                priority=idea_data.priority,
                problem_statement=idea_data.problem_statement,
                solution_details=idea_data.solution_details,
                target_audience=idea_data.target_audience,
                success_metrics=idea_data.success_metrics,
                creator_id=creator_id,
                team_id=idea_data.team_id,
                ai_generated=ai_generated,
                ai_confidence_score=ai_confidence_score,
                status=IdeaStatus.DRAFT
            )
            
            self.db.add(idea)
            self.db.commit()
            self.db.refresh(idea)
            
            logger.info(f"Created idea: {idea.title} (ID: {idea.id})")
            return idea
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating idea: {e}")
            raise
    
    def update_idea(self, idea_id: int, idea_data: IdeaUpdate) -> Optional[Idea]:
        """
        Update an existing idea.
        
        Args:
            idea_id: ID of the idea to update
            idea_data: Update data
            
        Returns:
            Updated idea or None
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        try:
            update_data = idea_data.dict(exclude_unset=True)
            
            for key, value in update_data.items():
                if hasattr(idea, key):
                    setattr(idea, key, value)
            
            idea.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(idea)
            
            logger.info(f"Updated idea {idea_id}")
            return idea
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating idea {idea_id}: {e}")
            raise
    
    def update_idea_evaluation(
        self, 
        idea_id: int, 
        evaluation_data: IdeaEvaluation
    ) -> Optional[Idea]:
        """
        Update idea evaluation data.
        
        Args:
            idea_id: ID of the idea to update
            evaluation_data: Evaluation data
            
        Returns:
            Updated idea or None
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        try:
            idea.evaluation_score = evaluation_data.evaluation_score
            idea.evaluation_criteria = evaluation_data.evaluation_criteria
            idea.evaluated_at = datetime.utcnow()
            idea.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(idea)
            
            logger.info(f"Updated evaluation for idea {idea_id}")
            return idea
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating evaluation for idea {idea_id}: {e}")
            raise
    
    def update_idea_from_iteration(
        self, 
        idea_id: int, 
        iteration_output: IdeaIterationOutput
    ) -> Optional[Idea]:
        """
        Update idea from iteration results.
        
        Args:
            idea_id: ID of the idea to update
            iteration_output: Iteration results
            
        Returns:
            Updated idea or None
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        try:
            improved_idea = iteration_output.improved_idea
            
            # Update with improved content
            idea.title = improved_idea.title
            idea.description = improved_idea.description
            idea.solution_details = improved_idea.implementation_approach
            idea.target_audience = improved_idea.target_impact
            idea.updated_at = datetime.utcnow()
            
            # Update tags with key benefits
            if improved_idea.key_benefits:
                idea.tags = improved_idea.key_benefits[:5]
            
            self.db.commit()
            self.db.refresh(idea)
            
            logger.info(f"Updated idea {idea_id} from iteration")
            return idea
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating idea {idea_id} from iteration: {e}")
            raise
    
    def delete_idea(self, idea_id: int) -> bool:
        """
        Delete an idea.
        
        Args:
            idea_id: ID of the idea to delete
            
        Returns:
            True if successful
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return False
        
        try:
            self.db.delete(idea)
            self.db.commit()
            
            logger.info(f"Deleted idea {idea_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting idea {idea_id}: {e}")
            return False
    
    def can_user_access_idea(self, idea_id: int, user_id: int) -> bool:
        """
        Check if user can access an idea.
        
        Args:
            idea_id: ID of the idea
            user_id: ID of the user
            
        Returns:
            True if user can access the idea
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return False
        
        # Creator can always access
        if idea.creator_id == user_id:
            return True
        
        # Team members can access team ideas
        if idea.team_id:
            team_member = (
                self.db.query(TeamMember)
                .filter(
                    and_(
                        TeamMember.team_id == idea.team_id,
                        TeamMember.user_id == user_id
                    )
                )
                .first()
            )
            return team_member is not None
        
        return False
    
    def can_user_modify_idea(self, idea_id: int, user_id: int) -> bool:
        """
        Check if user can modify an idea.
        
        Args:
            idea_id: ID of the idea
            user_id: ID of the user
            
        Returns:
            True if user can modify the idea
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return False
        
        # Creator can always modify
        if idea.creator_id == user_id:
            return True
        
        # Team admins can modify team ideas
        if idea.team_id:
            team_member = (
                self.db.query(TeamMember)
                .filter(
                    and_(
                        TeamMember.team_id == idea.team_id,
                        TeamMember.user_id == user_id,
                        TeamMember.role.in_(["admin", "owner"])
                    )
                )
                .first()
            )
            return team_member is not None
        
        return False
    
    def search_ideas(
        self, 
        query: str, 
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[Idea]:
        """
        Search ideas accessible to user.
        
        Args:
            query: Search query
            user_id: User ID
            limit: Maximum results
            offset: Results offset
            
        Returns:
            List of matching ideas
        """
        # Get user's team IDs
        user_team_ids = (
            self.db.query(TeamMember.team_id)
            .filter(TeamMember.user_id == user_id)
            .subquery()
        )
        
        # Search in accessible ideas
        ideas = (
            self.db.query(Idea)
            .filter(
                and_(
                    or_(
                        Idea.creator_id == user_id,
                        Idea.team_id.in_(user_team_ids)
                    ),
                    or_(
                        Idea.title.ilike(f"%{query}%"),
                        Idea.description.ilike(f"%{query}%"),
                        Idea.category.ilike(f"%{query}%")
                    )
                )
            )
            .order_by(Idea.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return ideas
    
    # Placeholder methods for iteration functionality
    def create_iteration_history(
        self, 
        idea_id: int, 
        iteration_output: IdeaIterationOutput, 
        user_id: str
    ):
        """Create iteration history record."""
        # TODO: Implement iteration history storage
        logger.info(f"Created iteration history for idea {idea_id}")
    
    def get_iteration_history(self, idea_id: int, limit: int, offset: int):
        """Get iteration history for an idea."""
        # TODO: Implement iteration history retrieval
        return []
    
    def apply_iteration_results(self, idea_id: int, iteration_output: IdeaIterationOutput):
        """Apply iteration results to idea."""
        return self.update_idea_from_iteration(idea_id, iteration_output)
    
    def revert_to_iteration(self, idea_id: int, iteration_id: int):
        """Revert idea to specific iteration."""
        # TODO: Implement iteration revert
        return self.get_idea(idea_id)
    
    def create_idea_branch(
        self, 
        idea_id: int, 
        branch_description: str, 
        iteration_focus: List[str], 
        user_id: int
    ):
        """Create a branch (copy) of an idea."""
        original_idea = self.get_idea(idea_id)
        if not original_idea:
            return None
        
        # Create a copy
        idea_data = IdeaCreate(
            title=f"{original_idea.title} (Branch)",
            description=f"{original_idea.description}\n\nBranch: {branch_description}",
            category=original_idea.category,
            tags=original_idea.tags,
            priority=original_idea.priority,
            problem_statement=original_idea.problem_statement,
            solution_details=original_idea.solution_details,
            target_audience=original_idea.target_audience,
            success_metrics=original_idea.success_metrics,
            team_id=original_idea.team_id
        )
        
        return self.create_idea(idea_data, user_id)