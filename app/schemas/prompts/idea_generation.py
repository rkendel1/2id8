"""
Pydantic-AI prompts for idea generation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pydantic_ai import Agent


class IdeaGenerationContext(BaseModel):
    """Context model for idea generation prompts."""
    problem_description: str = Field(..., min_length=50, max_length=2000)
    target_audience: Optional[str] = Field(None, max_length=500)
    industry_or_domain: Optional[str] = Field(None, max_length=200)
    constraints: List[str] = Field(default_factory=list, max_items=10)
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    existing_solutions: List[str] = Field(default_factory=list, max_items=5)
    success_criteria: List[str] = Field(default_factory=list, max_items=8)
    additional_context: Optional[str] = Field(None, max_length=1000)


class IdeaGenerationPrompt(BaseModel):
    """Structured prompt for idea generation."""
    context: IdeaGenerationContext
    num_ideas: int = Field(default=3, ge=1, le=10)
    creativity_level: float = Field(default=0.7, ge=0.0, le=1.0)
    focus_areas: List[str] = Field(default_factory=list, max_items=5)
    
    def to_prompt_text(self) -> str:
        """Convert to structured prompt text for the LLM."""
        prompt_parts = [
            "You are an expert innovation consultant and idea generation specialist.",
            "Your task is to generate creative, practical, and valuable ideas based on the provided context.",
            "",
            f"PROBLEM/CHALLENGE: {self.context.problem_description}",
        ]
        
        if self.context.target_audience:
            prompt_parts.append(f"TARGET AUDIENCE: {self.context.target_audience}")
        
        if self.context.industry_or_domain:
            prompt_parts.append(f"INDUSTRY/DOMAIN: {self.context.industry_or_domain}")
        
        if self.context.constraints:
            prompt_parts.extend([
                "CONSTRAINTS:",
                *[f"- {constraint}" for constraint in self.context.constraints]
            ])
        
        if self.context.budget_range:
            prompt_parts.append(f"BUDGET RANGE: {self.context.budget_range}")
        
        if self.context.timeline:
            prompt_parts.append(f"TIMELINE: {self.context.timeline}")
        
        if self.context.existing_solutions:
            prompt_parts.extend([
                "EXISTING SOLUTIONS TO CONSIDER:",
                *[f"- {solution}" for solution in self.context.existing_solutions]
            ])
        
        if self.context.success_criteria:
            prompt_parts.extend([
                "SUCCESS CRITERIA:",
                *[f"- {criteria}" for criteria in self.context.success_criteria]
            ])
        
        if self.focus_areas:
            prompt_parts.extend([
                "FOCUS AREAS:",
                *[f"- {area}" for area in self.focus_areas]
            ])
        
        if self.context.additional_context:
            prompt_parts.append(f"ADDITIONAL CONTEXT: {self.context.additional_context}")
        
        prompt_parts.extend([
            "",
            f"Please generate {self.num_ideas} innovative, practical, and well-structured ideas.",
            "For each idea, provide:",
            "1. A clear, descriptive title",
            "2. A detailed description (100-300 words)",
            "3. Key benefits and value proposition",
            "4. Implementation approach or next steps",
            "5. Potential challenges and mitigation strategies",
            "6. Success metrics or evaluation criteria",
            "",
            "Focus on creativity, feasibility, and potential impact.",
            "Ensure each idea is distinct and addresses the core problem effectively."
        ])
        
        return "\n".join(prompt_parts)


# Create the pydantic-ai agent for idea generation
idea_generation_agent = Agent(
    model="gpt-4",
    system_prompt="""You are an expert innovation consultant and idea generation specialist.
    You excel at creating practical, innovative, and impactful ideas that solve real problems.
    Always structure your responses clearly and provide actionable insights."""
)