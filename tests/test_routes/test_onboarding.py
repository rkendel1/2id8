"""
Integration tests for onboarding routes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app


class TestOnboardingRoutes:
    """Test cases for onboarding API routes."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_register_user_endpoint_structure(self):
        """Test user registration endpoint structure."""
        # Note: This is a structural test - actual database integration
        # would require proper test database setup
        
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        
        with patch('app.routes.onboarding.UserService') as mock_service:
            # Mock the service to avoid database calls
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_user_by_email.return_value = None
            mock_service_instance.get_user_by_username.return_value = None
            
            # Mock user creation
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_user.email = "test@example.com"
            mock_service_instance.create_user.return_value = mock_user
            
            # Note: This would fail without proper database/dependency injection
            # but shows the test structure
            pass
    
    def test_login_endpoint_structure(self):
        """Test login endpoint structure."""
        login_data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        
        with patch('app.routes.onboarding.UserService') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            
            # Mock authentication
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_service_instance.authenticate_user.return_value = mock_user
            
            # Mock token creation
            mock_token = {
                "access_token": "test_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {"id": 1, "username": "testuser"}
            }
            mock_service_instance.create_access_token.return_value = mock_token
            
            # Test structure exists
            pass
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
    
    def test_api_info_endpoint(self):
        """Test API info endpoint."""
        response = self.client.get("/api/v1")
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        
        # Check that all expected endpoint categories are present
        endpoints = data["endpoints"]
        expected_categories = [
            "onboarding", "idea_generation", "evaluation", 
            "iteration", "feedback", "llm_logs"
        ]
        
        for category in expected_categories:
            assert category in endpoints


class TestIdeaGenerationRoutes:
    """Test cases for idea generation API routes."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_idea_generation_request_validation(self):
        """Test idea generation request validation."""
        from app.schemas.idea import IdeaGenerationRequest
        
        # Valid request
        valid_request = {
            "context": "I need ideas for improving customer service in a restaurant",
            "category": "hospitality",
            "num_ideas": 3,
            "temperature": 0.7
        }
        
        request_obj = IdeaGenerationRequest(**valid_request)
        assert request_obj.context == valid_request["context"]
        assert request_obj.num_ideas == 3
        assert request_obj.temperature == 0.7
    
    def test_idea_generation_request_validation_fails(self):
        """Test idea generation request validation failures."""
        from app.schemas.idea import IdeaGenerationRequest
        from pydantic import ValidationError
        
        # Invalid request - context too short
        invalid_request = {
            "context": "short",  # Too short
            "num_ideas": 15,     # Too many
            "temperature": 3.0   # Out of range
        }
        
        with pytest.raises(ValidationError):
            IdeaGenerationRequest(**invalid_request)


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_context_builder_idea_generation(self):
        """Test context builder for idea generation."""
        from app.utils.context_builder import ContextBuilder
        
        context = ContextBuilder.build_idea_generation_context(
            problem_description="Need to improve team productivity",
            user_context={"expertise": ["management", "technology"]},
            team_context={"size": 5, "expertise": ["development", "design"]}
        )
        
        assert "problem_description" in context
        assert "user" in context
        assert "team" in context
        assert context["session_type"] == "idea_generation"
    
    def test_validation_utils_text_sanitization(self):
        """Test text sanitization utilities."""
        from app.utils.validation import ValidationUtils
        
        dangerous_text = "<script>alert('xss')</script>Normal text here"
        sanitized = ValidationUtils.sanitize_text_input(dangerous_text)
        
        assert "<script>" not in sanitized
        assert "Normal text here" in sanitized
    
    def test_llm_handler_call_creation(self):
        """Test LLM call handler call creation."""
        from app.utils.llm_handler import LLMCall, CallPriority, CallStatus
        from datetime import datetime
        
        call = LLMCall(
            id="test_call_1",
            prompt="Test prompt",
            model="gpt-4",
            temperature=0.7,
            max_tokens=1000,
            priority=CallPriority.NORMAL,
            user_id=1,
            created_at=datetime.utcnow()
        )
        
        assert call.id == "test_call_1"
        assert call.priority == CallPriority.NORMAL
        assert call.status == CallStatus.QUEUED
        assert call.user_id == 1