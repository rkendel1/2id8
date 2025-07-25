"""
Team schemas for request validation and response serialization.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.team import TeamRole


class TeamBase(BaseModel):
    """Base team schema with common fields."""
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    max_members: int = Field(default=10, ge=1, le=100)
    is_public: bool = False


class TeamCreate(TeamBase):
    """Schema for team creation requests."""
    pass


class TeamUpdate(BaseModel):
    """Schema for team update requests."""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    max_members: Optional[int] = Field(None, ge=1, le=100)
    is_public: Optional[bool] = None


class TeamMemberBase(BaseModel):
    """Base team member schema."""
    user_id: int
    role: TeamRole = TeamRole.MEMBER


class TeamMemberCreate(TeamMemberBase):
    """Schema for adding team members."""
    pass


class TeamMemberUpdate(BaseModel):
    """Schema for updating team member role."""
    role: TeamRole


class TeamMemberResponse(TeamMemberBase):
    """Schema for team member response."""
    id: int
    team_id: int
    joined_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamResponse(TeamBase):
    """Schema for team response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: List[TeamMemberResponse] = []

    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    """Schema for team list response."""
    id: int
    name: str
    description: Optional[str]
    is_public: bool
    member_count: int
    created_at: datetime

    class Config:
        from_attributes = True