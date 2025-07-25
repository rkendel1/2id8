"""
Feedback service for managing idea feedback and sentiment analysis.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.idea import Idea
from app.models.user import User
from app.core.logging import logger
from pydantic import BaseModel
import json


# Feedback model (simplified - in practice you'd have a proper SQLAlchemy model)
class Feedback(BaseModel):
    """Temporary feedback model - should be replaced with proper SQLAlchemy model."""
    id: int
    idea_id: int
    content: str
    rating: Optional[int]
    feedback_type: str
    is_anonymous: bool
    author_id: Optional[int]
    author_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FeedbackService:
    """Service class for feedback management and analysis."""
    
    def __init__(self, db: Session):
        self.db = db
        # Note: In a real implementation, you'd have a proper Feedback model
        # For now, we'll simulate feedback storage
        self._feedback_storage = []  # Temporary in-memory storage
        self._next_id = 1
    
    def create_feedback(
        self,
        idea_id: int,
        content: str,
        author_id: Optional[int] = None,
        rating: Optional[int] = None,
        feedback_type: str = "general",
        is_anonymous: bool = False
    ) -> Feedback:
        """
        Create new feedback for an idea.
        
        Args:
            idea_id: ID of the idea
            content: Feedback content
            author_id: ID of the author (if not anonymous)
            rating: Optional rating (1-10)
            feedback_type: Type of feedback
            is_anonymous: Whether feedback is anonymous
            
        Returns:
            Created feedback
        """
        try:
            # Get author name if not anonymous
            author_name = None
            if not is_anonymous and author_id:
                user = self.db.query(User).filter(User.id == author_id).first()
                author_name = user.username if user else None
            
            # Create feedback (using temporary storage)
            feedback = Feedback(
                id=self._next_id,
                idea_id=idea_id,
                content=content,
                rating=rating,
                feedback_type=feedback_type,
                is_anonymous=is_anonymous,
                author_id=author_id if not is_anonymous else None,
                author_name=author_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self._feedback_storage.append(feedback.dict())
            self._next_id += 1
            
            logger.info(f"Created feedback for idea {idea_id}")
            return feedback
            
        except Exception as e:
            logger.error(f"Error creating feedback: {e}")
            raise
    
    def get_idea_feedback(
        self,
        idea_id: int,
        limit: int = 20,
        offset: int = 0,
        feedback_type: Optional[str] = None
    ) -> List[Feedback]:
        """
        Get feedback for a specific idea.
        
        Args:
            idea_id: ID of the idea
            limit: Maximum number of feedback items
            offset: Number of items to skip
            feedback_type: Optional filter by type
            
        Returns:
            List of feedback
        """
        try:
            # Filter feedback (using temporary storage)
            filtered_feedback = [
                Feedback(**fb) for fb in self._feedback_storage
                if fb["idea_id"] == idea_id and (
                    feedback_type is None or fb["feedback_type"] == feedback_type
                )
            ]
            
            # Sort by created_at desc and apply pagination
            sorted_feedback = sorted(
                filtered_feedback,
                key=lambda x: x.created_at,
                reverse=True
            )
            
            return sorted_feedback[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Error getting feedback for idea {idea_id}: {e}")
            raise
    
    def update_feedback(
        self,
        feedback_id: int,
        author_id: int,
        content: Optional[str] = None,
        rating: Optional[int] = None
    ) -> Optional[Feedback]:
        """
        Update feedback (only by author).
        
        Args:
            feedback_id: ID of the feedback
            author_id: ID of the author
            content: New content
            rating: New rating
            
        Returns:
            Updated feedback or None
        """
        try:
            # Find feedback in temporary storage
            for i, fb_dict in enumerate(self._feedback_storage):
                if fb_dict["id"] == feedback_id and fb_dict["author_id"] == author_id:
                    # Update fields
                    if content is not None:
                        fb_dict["content"] = content
                    if rating is not None:
                        fb_dict["rating"] = rating
                    fb_dict["updated_at"] = datetime.utcnow()
                    
                    # Replace in storage
                    self._feedback_storage[i] = fb_dict
                    
                    logger.info(f"Updated feedback {feedback_id}")
                    return Feedback(**fb_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating feedback {feedback_id}: {e}")
            raise
    
    def delete_feedback(self, feedback_id: int, user_id: int) -> bool:
        """
        Delete feedback (by author or idea owner).
        
        Args:
            feedback_id: ID of the feedback
            user_id: ID of the user requesting deletion
            
        Returns:
            True if successful
        """
        try:
            # Find and remove feedback
            for i, fb_dict in enumerate(self._feedback_storage):
                if fb_dict["id"] == feedback_id:
                    # Check if user can delete (author or idea owner)
                    if fb_dict["author_id"] == user_id or self._is_idea_owner(fb_dict["idea_id"], user_id):
                        del self._feedback_storage[i]
                        logger.info(f"Deleted feedback {feedback_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting feedback {feedback_id}: {e}")
            return False
    
    async def generate_feedback_summary(
        self,
        idea_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate AI-powered feedback summary for an idea.
        
        Args:
            idea_id: ID of the idea
            user_id: User ID for logging
            
        Returns:
            Feedback summary with insights
        """
        try:
            # Get all feedback for the idea
            feedback_list = self.get_idea_feedback(idea_id, limit=100)
            
            if not feedback_list:
                return {
                    "idea_id": idea_id,
                    "total_feedback_count": 0,
                    "average_rating": None,
                    "sentiment_score": None,
                    "key_themes": [],
                    "improvement_suggestions": []
                }
            
            # Calculate basic statistics
            total_count = len(feedback_list)
            ratings = [fb.rating for fb in feedback_list if fb.rating is not None]
            average_rating = sum(ratings) / len(ratings) if ratings else None
            
            # Analyze feedback content (simplified analysis)
            all_content = " ".join([fb.content for fb in feedback_list])
            sentiment_score = self._analyze_sentiment(all_content)
            key_themes = self._extract_key_themes(feedback_list)
            improvement_suggestions = self._extract_improvement_suggestions(feedback_list)
            
            logger.info(f"Generated feedback summary for idea {idea_id}")
            
            return {
                "idea_id": idea_id,
                "total_feedback_count": total_count,
                "average_rating": average_rating,
                "sentiment_score": sentiment_score,
                "key_themes": key_themes,
                "improvement_suggestions": improvement_suggestions
            }
            
        except Exception as e:
            logger.error(f"Error generating feedback summary for idea {idea_id}: {e}")
            raise
    
    def get_feedback_analytics(
        self,
        idea_id: int,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get feedback analytics for an idea.
        
        Args:
            idea_id: ID of the idea
            time_period_days: Time period for analysis
            
        Returns:
            Feedback analytics
        """
        try:
            # Get feedback within time period
            cutoff_date = datetime.utcnow() - timedelta(days=time_period_days)
            feedback_list = [
                Feedback(**fb) for fb in self._feedback_storage
                if fb["idea_id"] == idea_id and 
                datetime.fromisoformat(fb["created_at"].isoformat()) >= cutoff_date
            ]
            
            if not feedback_list:
                return {
                    "total_feedback": 0,
                    "feedback_by_type": {},
                    "rating_distribution": {},
                    "feedback_trends": []
                }
            
            # Analyze feedback types
            feedback_by_type = {}
            for fb in feedback_list:
                feedback_by_type[fb.feedback_type] = feedback_by_type.get(fb.feedback_type, 0) + 1
            
            # Analyze rating distribution
            rating_distribution = {}
            for fb in feedback_list:
                if fb.rating:
                    rating_distribution[str(fb.rating)] = rating_distribution.get(str(fb.rating), 0) + 1
            
            # Calculate daily trends (simplified)
            feedback_trends = self._calculate_feedback_trends(feedback_list)
            
            return {
                "total_feedback": len(feedback_list),
                "feedback_by_type": feedback_by_type,
                "rating_distribution": rating_distribution,
                "feedback_trends": feedback_trends
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback analytics for idea {idea_id}: {e}")
            raise
    
    # Private helper methods
    
    def _is_idea_owner(self, idea_id: int, user_id: int) -> bool:
        """Check if user owns the idea."""
        idea = self.db.query(Idea).filter(Idea.id == idea_id).first()
        return idea and idea.creator_id == user_id
    
    def _analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text (simplified implementation).
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score between -1 (negative) and 1 (positive)
        """
        # Simplified sentiment analysis
        positive_words = ["good", "great", "excellent", "amazing", "love", "perfect", "wonderful"]
        negative_words = ["bad", "terrible", "awful", "hate", "horrible", "poor", "disappointing"]
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 0.0  # Neutral
        
        return (positive_count - negative_count) / total_sentiment_words
    
    def _extract_key_themes(self, feedback_list: List[Feedback]) -> List[str]:
        """
        Extract key themes from feedback.
        
        Args:
            feedback_list: List of feedback
            
        Returns:
            List of key themes
        """
        # Simplified theme extraction
        all_text = " ".join([fb.content.lower() for fb in feedback_list])
        
        # Common themes to look for
        themes = {
            "usability": ["easy", "user-friendly", "intuitive", "simple"],
            "functionality": ["features", "functionality", "capabilities", "performance"],
            "design": ["design", "interface", "ui", "ux", "visual"],
            "value": ["valuable", "useful", "benefit", "worth", "price"],
            "implementation": ["implementation", "development", "technical", "feasibility"]
        }
        
        found_themes = []
        for theme, keywords in themes.items():
            if any(keyword in all_text for keyword in keywords):
                found_themes.append(theme)
        
        return found_themes[:5]  # Return top 5 themes
    
    def _extract_improvement_suggestions(self, feedback_list: List[Feedback]) -> List[str]:
        """
        Extract improvement suggestions from feedback.
        
        Args:
            feedback_list: List of feedback
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Look for feedback that contains suggestions
        suggestion_indicators = ["suggest", "recommend", "should", "could", "improve", "better", "add"]
        
        for fb in feedback_list:
            content_lower = fb.content.lower()
            if any(indicator in content_lower for indicator in suggestion_indicators):
                # Extract the sentence containing the suggestion (simplified)
                sentences = fb.content.split(".")
                for sentence in sentences:
                    if any(indicator in sentence.lower() for indicator in suggestion_indicators):
                        suggestions.append(sentence.strip())
                        break
        
        # Return unique suggestions (limit to 10)
        unique_suggestions = list(set(suggestions))[:10]
        return unique_suggestions
    
    def _calculate_feedback_trends(self, feedback_list: List[Feedback]) -> List[Dict[str, Any]]:
        """
        Calculate feedback trends over time.
        
        Args:
            feedback_list: List of feedback
            
        Returns:
            List of trend data points
        """
        # Group feedback by date
        daily_counts = {}
        for fb in feedback_list:
            date_key = fb.created_at.strftime("%Y-%m-%d")
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        # Convert to trend format
        trends = []
        for date, count in sorted(daily_counts.items()):
            trends.append({
                "date": date,
                "feedback_count": count
            })
        
        return trends