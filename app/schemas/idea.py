"""
Idea schemas for request validation and response serialization.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.idea import IdeaStatus, IdeaPriority


class IdeaBase(BaseModel):
    """Base idea schema with common fields."""
    title: str = Field(..., min_length=10, max_length=500)
    description: str = Field(..., min_length=50)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = []
    priority: IdeaPriority = IdeaPriority.MEDIUM
    problem_statement: Optional[str] = None
    solution_details: Optional[str] = None
    target_audience: Optional[str] = None
    success_metrics: Optional[Dict[str, Any]] = None


class IdeaCreate(IdeaBase):
    """Schema for idea creation requests."""
    team_id: Optional[int] = None


class IdeaUpdate(BaseModel):
    """Schema for idea update requests."""
    title: Optional[str] = Field(None, min_length=10, max_length=500)
    description: Optional[str] = Field(None, min_length=50)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    status: Optional[IdeaStatus] = None
    priority: Optional[IdeaPriority] = None
    problem_statement: Optional[str] = None
    solution_details: Optional[str] = None
    target_audience: Optional[str] = None
    success_metrics: Optional[Dict[str, Any]] = None


class IdeaEvaluation(BaseModel):
    """Schema for idea evaluation data."""
    evaluation_score: float = Field(..., ge=0.0, le=10.0)
    evaluation_criteria: Dict[str, Any]
    feedback: Optional[str] = None


class IdeaResponse(IdeaBase):
    """Schema for idea response."""
    id: int
    status: IdeaStatus
    ai_generated: bool
    ai_confidence_score: Optional[float]
    evaluation_score: Optional[float]
    evaluation_criteria: Optional[Dict[str, Any]]
    creator_id: int
    team_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    evaluated_at: Optional[datetime]

    class Config:
        from_attributes = True


class IdeaListResponse(BaseModel):
    """Schema for idea list response."""
    id: int
    title: str
    description: str
    category: Optional[str]
    tags: Optional[List[str]]
    status: IdeaStatus
    priority: IdeaPriority
    ai_generated: bool
    evaluation_score: Optional[float]
    creator_id: int
    team_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IdeaGenerationRequest(BaseModel):
    """Schema for AI idea generation requests."""
    context: str = Field(..., min_length=50, max_length=2000)
    category: Optional[str] = Field(None, max_length=100)
    target_audience: Optional[str] = None
    constraints: Optional[List[str]] = []
    num_ideas: int = Field(default=3, ge=1, le=10)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    team_id: Optional[int] = None