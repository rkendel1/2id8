"""
LLM log model for tracking AI interactions and debugging.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base
import enum


class LLMOperation(enum.Enum):
    """Enumeration for LLM operation types."""
    IDEA_GENERATION = "idea_generation"
    IDEA_EVALUATION = "idea_evaluation"
    IDEA_ITERATION = "idea_iteration"
    FEEDBACK_ANALYSIS = "feedback_analysis"
    CONTEXT_BUILDING = "context_building"
    OTHER = "other"


class LLMStatus(enum.Enum):
    """Enumeration for LLM operation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class LLMLog(Base):
    """
    LLM log model for tracking AI interactions, debugging, and performance monitoring.
    """
    __tablename__ = "llm_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Operation details
    operation_type = Column(SQLEnum(LLMOperation), nullable=False, index=True)
    status = Column(SQLEnum(LLMStatus), default=LLMStatus.PENDING, nullable=False)
    
    # Request details
    model_name = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Response details
    response = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Context and metadata
    context_data = Column(JSON, nullable=True)  # Store context as JSON
    metadata = Column(JSON, nullable=True)      # Additional metadata
    
    # Cost tracking
    estimated_cost = Column(Float, nullable=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="llm_logs")
    idea = relationship("Idea", back_populates="llm_logs")

    def __repr__(self):
        return f"<LLMLog(id={self.id}, operation={self.operation_type}, status={self.status})>"