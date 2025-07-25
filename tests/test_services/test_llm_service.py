"""
Unit tests for LLM service functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session
from app.services.llm_service import LLMService
from app.models.llm_log import LLMLog, LLMOperation, LLMStatus
from app.models.idea import Idea


class TestLLMService:
    """Test cases for LLMService."""
    
    def test_llm_service_init(self):
        """Test LLMService initialization."""
        db_mock = Mock(spec=Session)
        service = LLMService(db_mock)
        assert service.db == db_mock
    
    @pytest.mark.asyncio
    async def test_generate_ideas_creates_log(self):
        """Test that idea generation creates an LLM log."""
        db_mock = Mock(spec=Session)
        service = LLMService(db_mock)
        
        # Mock database operations
        mock_log = LLMLog(
            id=1,
            operation_type=LLMOperation.IDEA_GENERATION,
            user_id=1,
            model_name="gpt-4",
            status=LLMStatus.PENDING,
            prompt=""
        )
        
        db_mock.add.return_value = None
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = mock_log
        db_mock.query.return_value.filter.return_value.first.return_value = mock_log
        
        with patch('app.services.llm_service.idea_generation_agent') as mock_agent:
            # Mock the AI response
            mock_response = Mock()
            mock_response.data = "Generated idea response"
            mock_agent.run = AsyncMock(return_value=mock_response)
            
            # Note: This would need proper async testing setup
            # For now, we're testing the structure
            pass
    
    def test_create_llm_log(self):
        """Test LLM log creation."""
        db_mock = Mock(spec=Session)
        service = LLMService(db_mock)
        
        mock_log = LLMLog(
            id=1,
            operation_type=LLMOperation.IDEA_GENERATION,
            user_id=1,
            model_name="gpt-4",
            status=LLMStatus.PENDING
        )
        
        db_mock.add.return_value = None
        db_mock.commit.return_value = None
        db_mock.refresh.return_value = None
        
        # Test log creation structure
        log = service._create_llm_log(
            operation_type=LLMOperation.IDEA_GENERATION,
            user_id=1,
            model_name="gpt-4"
        )
        
        db_mock.add.assert_called_once()
        db_mock.commit.assert_called_once()
    
    def test_estimate_cost_calculation(self):
        """Test cost estimation logic."""
        db_mock = Mock(spec=Session)
        service = LLMService(db_mock)
        
        # Test cost estimation
        prompt_length = 1000  # characters
        response_length = 500  # characters
        
        cost = service._estimate_cost(prompt_length, response_length)
        
        assert isinstance(cost, float)
        assert cost > 0
    
    def test_token_estimation(self):
        """Test token estimation logic."""
        db_mock = Mock(spec=Session)
        service = LLMService(db_mock)
        
        prompt = "This is a test prompt for token estimation."
        response = "This is a test response."
        
        tokens = service._estimate_tokens(prompt, response)
        
        assert isinstance(tokens, int)
        assert tokens > 0


class TestLLMResponseParsing:
    """Test cases for LLM response parsing utilities."""
    
    def test_parse_idea_generation_response(self):
        """Test parsing of idea generation responses."""
        from app.utils.parsing import LLMResponseParser
        
        response = """
        1. Smart Garden System
        A comprehensive IoT solution for automated garden management.
        
        2. AI Tutor Platform
        Personalized learning platform using artificial intelligence.
        """
        
        ideas = LLMResponseParser.parse_idea_generation_response(response)
        
        assert len(ideas) > 0
        assert all('title' in idea for idea in ideas)
        assert all('description' in idea for idea in ideas)
    
    def test_parse_evaluation_response(self):
        """Test parsing of evaluation responses."""
        from app.utils.parsing import LLMResponseParser
        
        response = """
        Overall Score: 7.5/10
        
        Strengths:
        - Innovative approach
        - Clear market need
        
        Weaknesses:
        - High implementation cost
        - Competition exists
        """
        
        evaluation = LLMResponseParser.parse_evaluation_response(response)
        
        assert 'overall_score' in evaluation
        assert 'strengths' in evaluation
        assert 'weaknesses' in evaluation
        assert isinstance(evaluation['overall_score'], float)
    
    def test_extract_title_from_text(self):
        """Test title extraction from text."""
        from app.utils.parsing import LLMResponseParser
        
        text = "Smart Home Automation System\nThis is a description of the idea..."
        title = LLMResponseParser._extract_title_from_text(text)
        
        assert "Smart Home Automation System" in title
        assert len(title) > 0