"""
Pydantic-AI prompts for idea evaluation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pydantic_ai import Agent


class EvaluationCriteria(BaseModel):
    """Model for evaluation criteria."""
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    weight: float = Field(..., ge=0.0, le=1.0)
    scale_min: int = Field(default=1, ge=1)
    scale_max: int = Field(default=10, ge=2)


class IdeaEvaluationContext(BaseModel):
    """Context model for idea evaluation prompts."""
    idea_title: str = Field(..., max_length=500)
    idea_description: str = Field(..., min_length=50)
    problem_statement: Optional[str] = None
    target_audience: Optional[str] = None
    success_metrics: Optional[Dict[str, Any]] = None
    constraints: List[str] = Field(default_factory=list)
    existing_solutions: List[str] = Field(default_factory=list)
    additional_context: Optional[str] = None


class IdeaEvaluationPrompt(BaseModel):
    """Structured prompt for idea evaluation."""
    context: IdeaEvaluationContext
    evaluation_criteria: List[EvaluationCriteria] = Field(
        default_factory=lambda: [
            EvaluationCriteria(
                name="Feasibility",
                description="How realistic and achievable is this idea?",
                weight=0.25
            ),
            EvaluationCriteria(
                name="Impact Potential",
                description="What is the potential positive impact or value?",
                weight=0.25
            ),
            EvaluationCriteria(
                name="Innovation Level",
                description="How novel and creative is this approach?",
                weight=0.20
            ),
            EvaluationCriteria(
                name="Market Fit",
                description="How well does this solve the target problem?",
                weight=0.30
            )
        ]
    )
    detailed_analysis: bool = True
    
    def to_prompt_text(self) -> str:
        """Convert to structured prompt text for the LLM."""
        prompt_parts = [
            "You are an expert business analyst and innovation evaluator.",
            "Your task is to thoroughly evaluate the provided idea using structured criteria.",
            "",
            f"IDEA TO EVALUATE:",
            f"Title: {self.context.idea_title}",
            f"Description: {self.context.idea_description}",
        ]
        
        if self.context.problem_statement:
            prompt_parts.append(f"Problem Statement: {self.context.problem_statement}")
        
        if self.context.target_audience:
            prompt_parts.append(f"Target Audience: {self.context.target_audience}")
        
        if self.context.success_metrics:
            prompt_parts.extend([
                "Success Metrics:",
                *[f"- {k}: {v}" for k, v in self.context.success_metrics.items()]
            ])
        
        if self.context.constraints:
            prompt_parts.extend([
                "Constraints:",
                *[f"- {constraint}" for constraint in self.context.constraints]
            ])
        
        if self.context.existing_solutions:
            prompt_parts.extend([
                "Existing Solutions to Compare Against:",
                *[f"- {solution}" for solution in self.context.existing_solutions]
            ])
        
        if self.context.additional_context:
            prompt_parts.append(f"Additional Context: {self.context.additional_context}")
        
        prompt_parts.extend([
            "",
            "EVALUATION CRITERIA:",
        ])
        
        for criteria in self.evaluation_criteria:
            weight_pct = int(criteria.weight * 100)
            prompt_parts.append(
                f"- {criteria.name} ({weight_pct}%): {criteria.description} "
                f"(Scale: {criteria.scale_min}-{criteria.scale_max})"
            )
        
        prompt_parts.extend([
            "",
            "Please provide a comprehensive evaluation including:",
            "1. Individual scores for each criterion with detailed justification",
            "2. Overall weighted score calculation",
            "3. Key strengths and weaknesses",
            "4. Specific recommendations for improvement",
            "5. Risk assessment and mitigation strategies",
            "6. Implementation timeline and resource requirements",
            "7. Success probability assessment",
            "",
            "Be objective, thorough, and provide actionable insights."
        ])
        
        return "\n".join(prompt_parts)


# Create the pydantic-ai agent for idea evaluation
idea_evaluation_agent = Agent(
    model="gpt-4",
    system_prompt="""You are an expert business analyst and innovation evaluator.
    You excel at objectively assessing ideas using structured criteria and providing
    actionable insights. Always be thorough, fair, and constructive in your evaluations."""
)