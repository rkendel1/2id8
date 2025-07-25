"""
Idea model for storing and managing generated ideas.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base
import enum


class IdeaStatus(enum.Enum):
    """Enumeration for idea status."""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_DEVELOPMENT = "in_development"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class IdeaPriority(enum.Enum):
    """Enumeration for idea priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Idea(Base):
    """
    Idea model for storing generated and evaluated ideas.
    """
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Categorization
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, nullable=True)  # List of tags as JSON
    
    # Status and priority
    status = Column(SQLEnum(IdeaStatus), default=IdeaStatus.DRAFT, nullable=False)
    priority = Column(SQLEnum(IdeaPriority), default=IdeaPriority.MEDIUM, nullable=False)
    
    # AI-generated content and evaluation
    ai_generated = Column(Boolean, default=False, nullable=False)
    ai_confidence_score = Column(Float, nullable=True)
    evaluation_score = Column(Float, nullable=True)
    evaluation_criteria = Column(JSON, nullable=True)  # Store evaluation criteria as JSON
    
    # Content and context
    problem_statement = Column(Text, nullable=True)
    solution_details = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    success_metrics = Column(JSON, nullable=True)
    
    # Relationships
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    creator = relationship("User", back_populates="ideas")
    team = relationship("Team", back_populates="ideas")
    llm_logs = relationship("LLMLog", back_populates="idea")

    def __repr__(self):
        return f"<Idea(id={self.id}, title='{self.title[:50]}...', status={self.status})>"