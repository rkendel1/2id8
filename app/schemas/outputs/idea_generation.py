"""
Pydantic-AI output models for idea generation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class GeneratedIdea(BaseModel):
    """Model for a single generated idea."""
    title: str = Field(..., min_length=10, max_length=500)
    description: str = Field(..., min_length=100, max_length=2000)
    key_benefits: List[str] = Field(..., min_items=1, max_items=10)
    implementation_approach: str = Field(..., min_length=50, max_length=1000)
    potential_challenges: List[str] = Field(default_factory=list, max_items=8)
    mitigation_strategies: List[str] = Field(default_factory=list, max_items=8)
    success_metrics: List[str] = Field(..., min_items=1, max_items=8)
    estimated_effort: Optional[str] = None
    estimated_timeline: Optional[str] = None
    target_impact: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class IdeaGenerationOutput(BaseModel):
    """Output model for idea generation responses."""
    ideas: List[GeneratedIdea] = Field(..., min_items=1, max_items=10)
    generation_context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IdeaIterationInput(BaseModel):
    """Input model for idea iteration requests."""
    original_idea: GeneratedIdea
    feedback: str = Field(..., min_length=20, max_length=2000)
    iteration_focus: List[str] = Field(default_factory=list, max_items=5)
    specific_improvements: List[str] = Field(default_factory=list, max_items=8)


class IdeaIterationOutput(BaseModel):
    """Output model for idea iteration responses."""
    original_idea: GeneratedIdea
    improved_idea: GeneratedIdea
    changes_made: List[str] = Field(..., min_items=1, max_items=10)
    improvement_summary: str = Field(..., min_length=50, max_length=1000)
    iteration_metadata: Dict[str, Any] = Field(default_factory=dict)
    iterated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }