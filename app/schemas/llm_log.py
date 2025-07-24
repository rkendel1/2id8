"""
LLM log schemas for tracking AI interactions.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.llm_log import LLMOperation, LLMStatus


class LLMLogBase(BaseModel):
    """Base LLM log schema with common fields."""
    operation_type: LLMOperation
    model_name: str
    prompt: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    context_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMLogCreate(LLMLogBase):
    """Schema for creating LLM log entries."""
    idea_id: Optional[int] = None


class LLMLogUpdate(BaseModel):
    """Schema for updating LLM log entries."""
    status: Optional[LLMStatus] = None
    response: Optional[str] = None
    response_time_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: Optional[int] = None
    estimated_cost: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LLMLogResponse(LLMLogBase):
    """Schema for LLM log response."""
    id: int
    status: LLMStatus
    response: Optional[str]
    response_time_ms: Optional[int]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    error_message: Optional[str]
    error_code: Optional[str]
    retry_count: int
    estimated_cost: Optional[float]
    user_id: int
    idea_id: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class LLMLogListResponse(BaseModel):
    """Schema for LLM log list response."""
    id: int
    operation_type: LLMOperation
    status: LLMStatus
    model_name: str
    response_time_ms: Optional[int]
    total_tokens: Optional[int]
    estimated_cost: Optional[float]
    user_id: int
    idea_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True