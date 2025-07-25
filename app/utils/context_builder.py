"""
Context builder utility for constructing prompts and contexts for LLM operations.
"""

from typing import Dict, List, Any, Optional
from app.models.idea import Idea
from app.models.user import User
from app.models.team import Team
from app.core.logging import logger


class ContextBuilder:
    """Utility class for building context for LLM operations."""
    
    @staticmethod
    def build_idea_generation_context(
        problem_description: str,
        user_context: Optional[Dict[str, Any]] = None,
        team_context: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for idea generation.
        
        Args:
            problem_description: Core problem to solve
            user_context: User-specific context
            team_context: Team-specific context
            additional_context: Additional context data
            
        Returns:
            Complete context dictionary
        """
        context = {
            "problem_description": problem_description,
            "timestamp": "now",
            "session_type": "idea_generation"
        }
        
        if user_context:
            context["user"] = {
                "expertise_areas": user_context.get("expertise", []),
                "industry_background": user_context.get("industry", ""),
                "preferences": user_context.get("preferences", {}),
                "past_ideas_categories": user_context.get("past_categories", [])
            }
        
        if team_context:
            context["team"] = {
                "team_size": team_context.get("size", 1),
                "team_expertise": team_context.get("expertise", []),
                "team_goals": team_context.get("goals", []),
                "collaboration_style": team_context.get("style", "cooperative")
            }
        
        if additional_context:
            context.update(additional_context)
        
        logger.debug(f"Built idea generation context with {len(context)} fields")
        return context
    
    @staticmethod
    def build_evaluation_context(
        idea: Idea,
        evaluation_criteria: List[str],
        market_context: Optional[Dict[str, Any]] = None,
        competitive_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for idea evaluation.
        
        Args:
            idea: Idea to evaluate
            evaluation_criteria: Criteria for evaluation
            market_context: Market-specific context
            competitive_context: Competitive landscape context
            
        Returns:
            Complete evaluation context
        """
        context = {
            "idea": {
                "title": idea.title,
                "description": idea.description,
                "category": idea.category,
                "tags": idea.tags or [],
                "problem_statement": idea.problem_statement,
                "target_audience": idea.target_audience,
                "ai_generated": idea.ai_generated
            },
            "evaluation_criteria": evaluation_criteria,
            "session_type": "idea_evaluation"
        }
        
        if market_context:
            context["market"] = {
                "size": market_context.get("size", "unknown"),
                "trends": market_context.get("trends", []),
                "growth_rate": market_context.get("growth_rate", "unknown"),
                "target_segments": market_context.get("segments", [])
            }
        
        if competitive_context:
            context["competition"] = {
                "existing_solutions": competitive_context.get("solutions", []),
                "key_players": competitive_context.get("players", []),
                "differentiation_opportunities": competitive_context.get("opportunities", [])
            }
        
        logger.debug(f"Built evaluation context for idea {idea.id}")
        return context
    
    @staticmethod
    def build_iteration_context(
        original_idea: Idea,
        feedback: str,
        improvement_areas: List[str],
        iteration_goals: List[str]
    ) -> Dict[str, Any]:
        """
        Build context for idea iteration.
        
        Args:
            original_idea: Original idea to iterate
            feedback: Feedback received
            improvement_areas: Areas requiring improvement
            iteration_goals: Goals for this iteration
            
        Returns:
            Iteration context
        """
        context = {
            "original_idea": {
                "title": original_idea.title,
                "description": original_idea.description,
                "current_status": original_idea.status.value,
                "evaluation_score": original_idea.evaluation_score,
                "creation_date": original_idea.created_at.isoformat(),
                "last_updated": original_idea.updated_at.isoformat()
            },
            "feedback": feedback,
            "improvement_areas": improvement_areas,
            "iteration_goals": iteration_goals,
            "session_type": "idea_iteration"
        }
        
        # Add evaluation context if available
        if original_idea.evaluation_criteria:
            context["previous_evaluation"] = original_idea.evaluation_criteria
        
        logger.debug(f"Built iteration context for idea {original_idea.id}")
        return context
    
    @staticmethod
    def build_user_profile_context(user: User) -> Dict[str, Any]:
        """
        Build user profile context.
        
        Args:
            user: User instance
            
        Returns:
            User context dictionary
        """
        context = {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "bio": user.bio,
            "account_age_days": (user.created_at - user.created_at).days if user.created_at else 0,
            "is_verified": user.is_verified,
            "last_active": user.last_login_at.isoformat() if user.last_login_at else None
        }
        
        logger.debug(f"Built user profile context for user {user.id}")
        return context
    
    @staticmethod
    def build_team_context(team: Team, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build team context.
        
        Args:
            team: Team instance
            members: List of team members with their roles
            
        Returns:
            Team context dictionary
        """
        context = {
            "team_id": team.id,
            "team_name": team.name,
            "description": team.description,
            "member_count": len(members),
            "is_public": team.is_public,
            "created_date": team.created_at.isoformat(),
            "members": [
                {
                    "user_id": member.get("user_id"),
                    "role": member.get("role"),
                    "username": member.get("username", "Unknown")
                }
                for member in members
            ]
        }
        
        # Analyze team composition
        roles = [member.get("role") for member in members]
        context["team_composition"] = {
            "admin_count": roles.count("admin"),
            "member_count": roles.count("member"),
            "viewer_count": roles.count("viewer"),
            "owner_count": roles.count("owner")
        }
        
        logger.debug(f"Built team context for team {team.id}")
        return context
    
    @staticmethod
    def build_comparison_context(
        ideas: List[Idea],
        comparison_criteria: List[str],
        user_priorities: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Build context for comparing multiple ideas.
        
        Args:
            ideas: List of ideas to compare
            comparison_criteria: Criteria for comparison
            user_priorities: User's priority weights for criteria
            
        Returns:
            Comparison context dictionary
        """
        context = {
            "ideas": [
                {
                    "id": idea.id,
                    "title": idea.title,
                    "description": idea.description[:200] + "..." if len(idea.description) > 200 else idea.description,
                    "category": idea.category,
                    "status": idea.status.value,
                    "priority": idea.priority.value,
                    "evaluation_score": idea.evaluation_score,
                    "ai_generated": idea.ai_generated,
                    "created_date": idea.created_at.isoformat()
                }
                for idea in ideas
            ],
            "comparison_criteria": comparison_criteria,
            "idea_count": len(ideas),
            "session_type": "idea_comparison"
        }
        
        if user_priorities:
            context["user_priorities"] = user_priorities
        
        # Add aggregate statistics
        scores = [idea.evaluation_score for idea in ideas if idea.evaluation_score]
        if scores:
            context["score_statistics"] = {
                "min_score": min(scores),
                "max_score": max(scores),
                "avg_score": sum(scores) / len(scores),
                "score_range": max(scores) - min(scores)
            }
        
        logger.debug(f"Built comparison context for {len(ideas)} ideas")
        return context
    
    @staticmethod
    def enhance_context_with_history(
        base_context: Dict[str, Any],
        user_history: Optional[List[Dict[str, Any]]] = None,
        team_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Enhance context with historical data.
        
        Args:
            base_context: Base context to enhance
            user_history: User's historical data
            team_history: Team's historical data
            
        Returns:
            Enhanced context with historical insights
        """
        enhanced_context = base_context.copy()
        
        if user_history:
            enhanced_context["user_history"] = {
                "total_ideas_created": len(user_history),
                "successful_ideas": len([item for item in user_history if item.get("status") == "completed"]),
                "average_evaluation_score": sum(
                    item.get("evaluation_score", 0) for item in user_history
                ) / len(user_history) if user_history else 0,
                "preferred_categories": ContextBuilder._extract_preferred_categories(user_history),
                "collaboration_frequency": sum(
                    1 for item in user_history if item.get("team_id")
                ) / len(user_history) if user_history else 0
            }
        
        if team_history:
            enhanced_context["team_history"] = {
                "total_team_ideas": len(team_history),
                "team_success_rate": len([
                    item for item in team_history if item.get("status") in ["approved", "completed"]
                ]) / len(team_history) if team_history else 0,
                "team_collaboration_patterns": ContextBuilder._analyze_collaboration_patterns(team_history)
            }
        
        logger.debug("Enhanced context with historical data")
        return enhanced_context
    
    @staticmethod
    def _extract_preferred_categories(history: List[Dict[str, Any]]) -> List[str]:
        """Extract user's preferred categories from history."""
        category_counts = {}
        for item in history:
            category = item.get("category")
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Return top 3 categories
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        return [category for category, _ in sorted_categories[:3]]
    
    @staticmethod
    def _analyze_collaboration_patterns(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze team collaboration patterns from history."""
        total_items = len(history)
        collaborative_items = len([item for item in history if item.get("contributors", 0) > 1])
        
        return {
            "collaboration_rate": collaborative_items / total_items if total_items > 0 else 0,
            "average_contributors": sum(
                item.get("contributors", 1) for item in history
            ) / total_items if total_items > 0 else 1,
            "most_active_periods": []  # Could be enhanced with time analysis
        }