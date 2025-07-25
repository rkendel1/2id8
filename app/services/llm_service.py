"""
LLM service for orchestrating AI interactions using pydantic-ai.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import time
import json
from app.models.llm_log import LLMLog, LLMOperation, LLMStatus
from app.models.idea import Idea
from app.schemas.prompts.idea_generation import IdeaGenerationPrompt, IdeaGenerationContext, idea_generation_agent
from app.schemas.prompts.evaluation import IdeaEvaluationPrompt, IdeaEvaluationContext, idea_evaluation_agent
from app.schemas.outputs.idea_generation import IdeaGenerationOutput, GeneratedIdea, IdeaIterationOutput
from app.core.config import settings
from app.core.logging import logger
from pydantic_ai import Agent


class LLMService:
    """Service class for LLM operations and orchestration."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_ideas(
        self,
        context: str,
        user_id: str,
        num_ideas: int = 3,
        temperature: Optional[float] = None,
        category: Optional[str] = None,
        target_audience: Optional[str] = None,
        constraints: List[str] = None,
        team_id: Optional[int] = None
    ) -> IdeaGenerationOutput:
        """
        Generate ideas using AI based on provided context.
        
        Args:
            context: Problem description or context
            user_id: User ID for logging
            num_ideas: Number of ideas to generate
            temperature: Model temperature
            category: Optional category
            target_audience: Optional target audience
            constraints: Optional constraints
            team_id: Optional team ID
            
        Returns:
            Generated ideas output
        """
        # Create LLM log entry
        llm_log = self._create_llm_log(
            operation_type=LLMOperation.IDEA_GENERATION,
            user_id=int(user_id),
            model_name=settings.openai_model,
            temperature=temperature or settings.openai_temperature
        )
        
        try:
            # Update log status
            self._update_llm_log_status(llm_log.id, LLMStatus.PROCESSING)
            start_time = time.time()
            
            # Create generation context
            generation_context = IdeaGenerationContext(
                problem_description=context,
                target_audience=target_audience,
                industry_or_domain=category,
                constraints=constraints or []
            )
            
            # Create prompt
            prompt = IdeaGenerationPrompt(
                context=generation_context,
                num_ideas=num_ideas,
                creativity_level=temperature or settings.openai_temperature
            )
            
            # Store prompt in log
            self._update_llm_log_prompt(llm_log.id, prompt.to_prompt_text())
            
            # Generate ideas using pydantic-ai
            response = await idea_generation_agent.run(prompt.to_prompt_text())
            
            # Process response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse response into structured format
            generated_ideas = self._parse_idea_generation_response(response.data, num_ideas)
            
            # Create output
            output = IdeaGenerationOutput(
                ideas=generated_ideas,
                generation_context={
                    "context": context,
                    "category": category,
                    "target_audience": target_audience,
                    "constraints": constraints
                },
                metadata={
                    "model": settings.openai_model,
                    "temperature": temperature or settings.openai_temperature,
                    "response_time_ms": response_time_ms
                }
            )
            
            # Update log with success
            self._update_llm_log_completion(
                llm_log.id,
                response.data,
                response_time_ms,
                estimated_cost=self._estimate_cost(len(prompt.to_prompt_text()), len(response.data))
            )
            
            logger.info(f"Generated {len(generated_ideas)} ideas for user {user_id}")
            return output
            
        except Exception as e:
            # Update log with error
            self._update_llm_log_error(llm_log.id, str(e))
            logger.error(f"Error generating ideas: {e}")
            raise
    
    async def iterate_idea(
        self,
        idea: Idea,
        feedback: str,
        specific_improvements: List[str],
        user_id: str
    ) -> IdeaIterationOutput:
        """
        Iterate and improve an existing idea.
        
        Args:
            idea: Original idea to iterate
            feedback: Feedback for improvement
            specific_improvements: Specific areas to improve
            user_id: User ID for logging
            
        Returns:
            Iteration output with original and improved idea
        """
        # Create LLM log entry
        llm_log = self._create_llm_log(
            operation_type=LLMOperation.IDEA_ITERATION,
            user_id=int(user_id),
            model_name=settings.openai_model,
            idea_id=idea.id
        )
        
        try:
            self._update_llm_log_status(llm_log.id, LLMStatus.PROCESSING)
            start_time = time.time()
            
            # Create iteration prompt
            prompt = f"""
            You are an expert innovation consultant. Please improve the following idea based on the feedback provided.

            ORIGINAL IDEA:
            Title: {idea.title}
            Description: {idea.description}
            Problem Statement: {idea.problem_statement or 'Not specified'}
            Solution Details: {idea.solution_details or 'Not specified'}
            Target Audience: {idea.target_audience or 'Not specified'}

            FEEDBACK FOR IMPROVEMENT:
            {feedback}

            SPECIFIC AREAS TO IMPROVE:
            {chr(10).join(f'- {improvement}' for improvement in specific_improvements)}

            Please provide an improved version of this idea that addresses the feedback and specific improvements requested.
            Maintain the core concept while enhancing the areas mentioned.
            
            Respond with a structured improvement including:
            1. Improved title
            2. Enhanced description
            3. Better implementation approach
            4. Addressed concerns from feedback
            5. Summary of changes made
            """
            
            self._update_llm_log_prompt(llm_log.id, prompt)
            
            # Generate iteration using basic agent
            agent = Agent(model=settings.openai_model)
            response = await agent.run(prompt)
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse response into iteration output
            iteration_output = self._parse_iteration_response(response.data, idea)
            
            # Update log with success
            self._update_llm_log_completion(
                llm_log.id,
                response.data,
                response_time_ms,
                estimated_cost=self._estimate_cost(len(prompt), len(response.data))
            )
            
            logger.info(f"Iterated idea {idea.id} for user {user_id}")
            return iteration_output
            
        except Exception as e:
            self._update_llm_log_error(llm_log.id, str(e))
            logger.error(f"Error iterating idea {idea.id}: {e}")
            raise
    
    async def refine_idea(
        self,
        idea: Idea,
        feedback: str,
        focus_areas: List[str],
        iteration_goals: List[str],
        user_id: str
    ) -> IdeaIterationOutput:
        """
        Refine an idea with specific focus areas and goals.
        
        Args:
            idea: Idea to refine
            feedback: Refinement feedback
            focus_areas: Areas to focus on
            iteration_goals: Goals for this iteration
            user_id: User ID for logging
            
        Returns:
            Refinement results
        """
        # For now, use the same logic as iterate_idea with additional context
        enhanced_feedback = f"""
        {feedback}
        
        FOCUS AREAS:
        {chr(10).join(f'- {area}' for area in focus_areas)}
        
        ITERATION GOALS:
        {chr(10).join(f'- {goal}' for goal in iteration_goals)}
        """
        
        return await self.iterate_idea(idea, enhanced_feedback, focus_areas, user_id)
    
    def get_user_llm_logs(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        operation_type: Optional[LLMOperation] = None,
        status: Optional[LLMStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LLMLog]:
        """Get LLM logs for a user with filtering."""
        query = self.db.query(LLMLog).filter(LLMLog.user_id == user_id)
        
        if operation_type:
            query = query.filter(LLMLog.operation_type == operation_type)
        
        if status:
            query = query.filter(LLMLog.status == status)
        
        if start_date:
            query = query.filter(LLMLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(LLMLog.created_at <= end_date)
        
        return query.order_by(LLMLog.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_idea_llm_logs(
        self,
        idea_id: int,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[LLMLog]:
        """Get LLM logs for a specific idea."""
        return (
            self.db.query(LLMLog)
            .filter(LLMLog.idea_id == idea_id, LLMLog.user_id == user_id)
            .order_by(LLMLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_llm_log_by_id(self, log_id: int) -> Optional[LLMLog]:
        """Get LLM log by ID."""
        return self.db.query(LLMLog).filter(LLMLog.id == log_id).first()
    
    def delete_llm_log(self, log_id: int, user_id: int) -> bool:
        """Delete an LLM log."""
        log = self.db.query(LLMLog).filter(
            LLMLog.id == log_id, 
            LLMLog.user_id == user_id
        ).first()
        
        if not log:
            return False
        
        try:
            self.db.delete(log)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting LLM log {log_id}: {e}")
            return False
    
    def get_user_usage_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage analytics for a user."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = self.db.query(LLMLog).filter(
            LLMLog.user_id == user_id,
            LLMLog.created_at >= start_date
        ).all()
        
        return {
            "total_requests": len(logs),
            "successful_requests": len([log for log in logs if log.status == LLMStatus.COMPLETED]),
            "failed_requests": len([log for log in logs if log.status == LLMStatus.FAILED]),
            "total_tokens": sum(log.total_tokens or 0 for log in logs),
            "operations_by_type": self._group_by_operation_type(logs),
            "daily_usage": self._calculate_daily_usage(logs)
        }
    
    def get_user_cost_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get cost analytics for a user."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = self.db.query(LLMLog).filter(
            LLMLog.user_id == user_id,
            LLMLog.created_at >= start_date
        ).all()
        
        total_cost = sum(log.estimated_cost or 0 for log in logs)
        
        return {
            "total_cost": total_cost,
            "average_cost_per_request": total_cost / len(logs) if logs else 0,
            "cost_by_operation": self._group_costs_by_operation(logs),
            "daily_costs": self._calculate_daily_costs(logs)
        }
    
    # Private helper methods
    
    def _create_llm_log(
        self,
        operation_type: LLMOperation,
        user_id: int,
        model_name: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        idea_id: Optional[int] = None
    ) -> LLMLog:
        """Create a new LLM log entry."""
        log = LLMLog(
            operation_type=operation_type,
            user_id=user_id,
            idea_id=idea_id,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens or settings.max_tokens,
            status=LLMStatus.PENDING,
            prompt="",  # Will be updated later
            started_at=datetime.utcnow()
        )
        
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        
        return log
    
    def _update_llm_log_status(self, log_id: int, status: LLMStatus):
        """Update LLM log status."""
        log = self.db.query(LLMLog).filter(LLMLog.id == log_id).first()
        if log:
            log.status = status
            if status == LLMStatus.PROCESSING:
                log.started_at = datetime.utcnow()
            self.db.commit()
    
    def _update_llm_log_prompt(self, log_id: int, prompt: str):
        """Update LLM log prompt."""
        log = self.db.query(LLMLog).filter(LLMLog.id == log_id).first()
        if log:
            log.prompt = prompt
            # Estimate prompt tokens (rough approximation)
            log.prompt_tokens = len(prompt.split()) * 1.3  # Rough token estimation
            self.db.commit()
    
    def _update_llm_log_completion(
        self,
        log_id: int,
        response: str,
        response_time_ms: int,
        estimated_cost: float
    ):
        """Update LLM log with completion data."""
        log = self.db.query(LLMLog).filter(LLMLog.id == log_id).first()
        if log:
            log.status = LLMStatus.COMPLETED
            log.response = response
            log.response_time_ms = response_time_ms
            log.estimated_cost = estimated_cost
            log.completed_at = datetime.utcnow()
            # Estimate completion tokens
            log.completion_tokens = len(response.split()) * 1.3
            log.total_tokens = (log.prompt_tokens or 0) + (log.completion_tokens or 0)
            self.db.commit()
    
    def _update_llm_log_error(self, log_id: int, error_message: str):
        """Update LLM log with error."""
        log = self.db.query(LLMLog).filter(LLMLog.id == log_id).first()
        if log:
            log.status = LLMStatus.FAILED
            log.error_message = error_message
            log.completed_at = datetime.utcnow()
            self.db.commit()
    
    def _estimate_cost(self, prompt_length: int, response_length: int) -> float:
        """Estimate API cost based on token usage."""
        # Rough token estimation and pricing for GPT-4
        prompt_tokens = prompt_length / 4  # Rough approximation
        completion_tokens = response_length / 4
        
        # GPT-4 pricing (approximate)
        prompt_cost = prompt_tokens * 0.00003  # $0.03 per 1K tokens
        completion_cost = completion_tokens * 0.00006  # $0.06 per 1K tokens
        
        return prompt_cost + completion_cost
    
    def _parse_idea_generation_response(self, response: str, num_ideas: int) -> List[GeneratedIdea]:
        """Parse AI response into structured ideas."""
        # This is a simplified parser - in practice, you'd want more robust parsing
        ideas = []
        
        # For now, create placeholder ideas based on the response
        # In practice, you'd parse the actual AI response structure
        for i in range(min(num_ideas, 3)):  # Limit to reasonable number
            idea = GeneratedIdea(
                title=f"Generated Idea {i+1}",
                description=f"AI-generated idea based on context. Response excerpt: {response[:200]}...",
                key_benefits=["Innovative approach", "Market potential", "Scalable solution"],
                implementation_approach="Detailed implementation plan would be here",
                potential_challenges=["Resource requirements", "Market competition"],
                mitigation_strategies=["Strategic partnerships", "Phased rollout"],
                success_metrics=["User adoption", "Revenue growth", "Market share"],
                confidence_score=0.8
            )
            ideas.append(idea)
        
        return ideas
    
    def _parse_iteration_response(self, response: str, original_idea: Idea) -> IdeaIterationOutput:
        """Parse iteration response into structured output."""
        # Create original idea representation
        original_generated_idea = GeneratedIdea(
            title=original_idea.title,
            description=original_idea.description,
            key_benefits=original_idea.tags or [],
            implementation_approach=original_idea.solution_details or "",
            success_metrics=list(original_idea.success_metrics.keys()) if original_idea.success_metrics else []
        )
        
        # Create improved idea (simplified for now)
        improved_idea = GeneratedIdea(
            title=f"{original_idea.title} (Improved)",
            description=f"Enhanced version: {response[:300]}...",
            key_benefits=["Enhanced benefits", "Improved approach"],
            implementation_approach="Improved implementation strategy",
            success_metrics=["Enhanced metrics", "Better tracking"]
        )
        
        return IdeaIterationOutput(
            original_idea=original_generated_idea,
            improved_idea=improved_idea,
            changes_made=["Enhanced description", "Improved implementation", "Better structure"],
            improvement_summary="AI-powered improvements applied based on feedback"
        )
    
    def _group_by_operation_type(self, logs: List[LLMLog]) -> Dict[str, int]:
        """Group logs by operation type."""
        groups = {}
        for log in logs:
            op_type = log.operation_type.value
            groups[op_type] = groups.get(op_type, 0) + 1
        return groups
    
    def _calculate_daily_usage(self, logs: List[LLMLog]) -> Dict[str, int]:
        """Calculate daily usage statistics."""
        daily_usage = {}
        for log in logs:
            date_key = log.created_at.strftime("%Y-%m-%d")
            daily_usage[date_key] = daily_usage.get(date_key, 0) + 1
        return daily_usage
    
    def _group_costs_by_operation(self, logs: List[LLMLog]) -> Dict[str, float]:
        """Group costs by operation type."""
        groups = {}
        for log in logs:
            op_type = log.operation_type.value
            cost = log.estimated_cost or 0
            groups[op_type] = groups.get(op_type, 0) + cost
        return groups
    
    def _calculate_daily_costs(self, logs: List[LLMLog]) -> Dict[str, float]:
        """Calculate daily cost statistics."""
        daily_costs = {}
        for log in logs:
            date_key = log.created_at.strftime("%Y-%m-%d")
            cost = log.estimated_cost or 0
            daily_costs[date_key] = daily_costs.get(date_key, 0) + cost
        return daily_costs