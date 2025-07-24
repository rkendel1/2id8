"""
Pydantic-AI output models for idea evaluation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class CriterionScore(BaseModel):
    """Model for individual criterion evaluation score."""
    criterion_name: str = Field(..., max_length=100)
    score: float = Field(..., ge=0.0, le=10.0)
    max_score: float = Field(default=10.0, ge=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    weighted_score: float = Field(..., ge=0.0)
    justification: str = Field(..., min_length=50, max_length=1000)
    strengths: List[str] = Field(default_factory=list, max_items=5)
    weaknesses: List[str] = Field(default_factory=list, max_items=5)


class RiskAssessment(BaseModel):
    """Model for risk assessment."""
    risk_category: str = Field(..., max_length=100)
    risk_level: str = Field(..., regex="^(Low|Medium|High|Critical)$")
    description: str = Field(..., min_length=20, max_length=500)
    probability: float = Field(..., ge=0.0, le=1.0)
    impact: float = Field(..., ge=0.0, le=10.0)
    mitigation_strategies: List[str] = Field(default_factory=list, max_items=5)


class ImprovementRecommendation(BaseModel):
    """Model for improvement recommendations."""
    category: str = Field(..., max_length=100)
    priority: str = Field(..., regex="^(Low|Medium|High|Critical)$")
    recommendation: str = Field(..., min_length=30, max_length=500)
    expected_impact: str = Field(..., min_length=20, max_length=300)
    effort_required: str = Field(..., max_length=200)
    timeline: Optional[str] = Field(None, max_length=100)


class IdeaEvaluationOutput(BaseModel):
    """Output model for idea evaluation responses."""
    idea_title: str = Field(..., max_length=500)
    overall_score: float = Field(..., ge=0.0, le=10.0)
    max_possible_score: float = Field(default=10.0)
    success_probability: float = Field(..., ge=0.0, le=1.0)
    
    # Detailed scoring
    criterion_scores: List[CriterionScore] = Field(..., min_items=1, max_items=20)
    
    # Analysis
    key_strengths: List[str] = Field(..., min_items=1, max_items=10)
    key_weaknesses: List[str] = Field(..., min_items=1, max_items=10)
    
    # Recommendations and risks
    improvement_recommendations: List[ImprovementRecommendation] = Field(
        default_factory=list, max_items=15
    )
    risk_assessments: List[RiskAssessment] = Field(default_factory=list, max_items=10)
    
    # Implementation details
    estimated_timeline: Optional[str] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    implementation_phases: List[str] = Field(default_factory=list, max_items=8)
    
    # Meta information
    evaluation_confidence: float = Field(..., ge=0.0, le=1.0)
    evaluation_methodology: str = Field(..., min_length=50, max_length=500)
    additional_notes: Optional[str] = Field(None, max_length=1000)
    evaluated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ComparisonEvaluationOutput(BaseModel):
    """Output model for comparing multiple ideas."""
    ideas_evaluated: List[str] = Field(..., min_items=2, max_items=10)
    individual_evaluations: List[IdeaEvaluationOutput] = Field(..., min_items=2, max_items=10)
    
    # Comparative analysis
    ranking: List[Dict[str, Any]] = Field(..., min_items=2, max_items=10)
    comparative_strengths: Dict[str, List[str]] = Field(default_factory=dict)
    comparative_weaknesses: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Recommendations
    top_recommendation: str = Field(..., max_length=500)
    selection_rationale: str = Field(..., min_length=100, max_length=1000)
    portfolio_recommendations: Optional[str] = Field(None, max_length=1000)
    
    compared_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }