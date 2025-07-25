"""
Validation utilities for input validation and data sanitization.
"""

import re
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, validator, ValidationError
from app.core.logging import logger


class ValidationError(Exception):
    """Custom validation error."""
    pass


class ValidationUtils:
    """Utility class for various validation operations."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid email format
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Validate username format.
        
        Args:
            username: Username to validate
            
        Returns:
            True if valid username
        """
        # Username: 3-50 chars, alphanumeric + underscore/hyphen, start with letter
        pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{2,49}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Union[bool, List[str]]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with validation results and requirements
        """
        requirements = {
            "min_length": len(password) >= 8,
            "has_uppercase": bool(re.search(r'[A-Z]', password)),
            "has_lowercase": bool(re.search(r'[a-z]', password)),
            "has_number": bool(re.search(r'\d', password)),
            "has_special": bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            "no_common_patterns": not ValidationUtils._has_common_patterns(password)
        }
        
        is_valid = all(requirements.values())
        
        failed_requirements = [
            req for req, passed in requirements.items() if not passed
        ]
        
        return {
            "is_valid": is_valid,
            "requirements": requirements,
            "failed_requirements": failed_requirements
        }
    
    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 1000) -> str:
        """
        Sanitize text input by removing dangerous characters and limiting length.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not isinstance(text, str):
            return ""
        
        # Remove potential HTML/script tags
        text = re.sub(r'<[^>]*>', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Trim to max length
        text = text[:max_length]
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def validate_idea_title(title: str) -> Dict[str, Union[bool, str]]:
        """
        Validate idea title.
        
        Args:
            title: Title to validate
            
        Returns:
            Validation result
        """
        if not title or not title.strip():
            return {"is_valid": False, "error": "Title cannot be empty"}
        
        title = title.strip()
        
        if len(title) < 10:
            return {"is_valid": False, "error": "Title must be at least 10 characters"}
        
        if len(title) > 500:
            return {"is_valid": False, "error": "Title must be less than 500 characters"}
        
        # Check for inappropriate content
        if ValidationUtils._contains_inappropriate_content(title):
            return {"is_valid": False, "error": "Title contains inappropriate content"}
        
        return {"is_valid": True, "sanitized_title": ValidationUtils.sanitize_text_input(title, 500)}
    
    @staticmethod
    def validate_idea_description(description: str) -> Dict[str, Union[bool, str]]:
        """
        Validate idea description.
        
        Args:
            description: Description to validate
            
        Returns:
            Validation result
        """
        if not description or not description.strip():
            return {"is_valid": False, "error": "Description cannot be empty"}
        
        description = description.strip()
        
        if len(description) < 50:
            return {"is_valid": False, "error": "Description must be at least 50 characters"}
        
        if len(description) > 5000:
            return {"is_valid": False, "error": "Description must be less than 5000 characters"}
        
        # Check for inappropriate content
        if ValidationUtils._contains_inappropriate_content(description):
            return {"is_valid": False, "error": "Description contains inappropriate content"}
        
        return {"is_valid": True, "sanitized_description": ValidationUtils.sanitize_text_input(description, 5000)}
    
    @staticmethod
    def validate_tags(tags: List[str]) -> Dict[str, Union[bool, str, List[str]]]:
        """
        Validate and sanitize tags.
        
        Args:
            tags: List of tags to validate
            
        Returns:
            Validation result with sanitized tags
        """
        if not tags:
            return {"is_valid": True, "sanitized_tags": []}
        
        if len(tags) > 20:
            return {"is_valid": False, "error": "Maximum 20 tags allowed"}
        
        sanitized_tags = []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            
            tag = tag.strip().lower()
            
            if len(tag) < 2:
                continue
            
            if len(tag) > 50:
                tag = tag[:50]
            
            # Remove special characters except hyphens and underscores
            tag = re.sub(r'[^a-zA-Z0-9_-]', '', tag)
            
            if tag and tag not in sanitized_tags:
                sanitized_tags.append(tag)
        
        return {"is_valid": True, "sanitized_tags": sanitized_tags}
    
    @staticmethod
    def validate_rating(rating: Optional[int]) -> Dict[str, Union[bool, str]]:
        """
        Validate rating value.
        
        Args:
            rating: Rating to validate
            
        Returns:
            Validation result
        """
        if rating is None:
            return {"is_valid": True}
        
        if not isinstance(rating, int):
            return {"is_valid": False, "error": "Rating must be an integer"}
        
        if rating < 1 or rating > 10:
            return {"is_valid": False, "error": "Rating must be between 1 and 10"}
        
        return {"is_valid": True}
    
    @staticmethod
    def validate_json_data(data: Any, max_size_kb: int = 100) -> Dict[str, Union[bool, str]]:
        """
        Validate JSON data size and structure.
        
        Args:
            data: JSON data to validate
            max_size_kb: Maximum size in KB
            
        Returns:
            Validation result
        """
        try:
            import json
            json_str = json.dumps(data)
            size_kb = len(json_str.encode('utf-8')) / 1024
            
            if size_kb > max_size_kb:
                return {"is_valid": False, "error": f"JSON data exceeds {max_size_kb}KB limit"}
            
            # Check for deeply nested structures
            if ValidationUtils._get_json_depth(data) > 10:
                return {"is_valid": False, "error": "JSON structure is too deeply nested"}
            
            return {"is_valid": True}
            
        except Exception as e:
            return {"is_valid": False, "error": f"Invalid JSON data: {str(e)}"}
    
    @staticmethod
    def validate_team_name(name: str) -> Dict[str, Union[bool, str]]:
        """
        Validate team name.
        
        Args:
            name: Team name to validate
            
        Returns:
            Validation result
        """
        if not name or not name.strip():
            return {"is_valid": False, "error": "Team name cannot be empty"}
        
        name = name.strip()
        
        if len(name) < 3:
            return {"is_valid": False, "error": "Team name must be at least 3 characters"}
        
        if len(name) > 255:
            return {"is_valid": False, "error": "Team name must be less than 255 characters"}
        
        # Allow letters, numbers, spaces, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\s_-]+$', name):
            return {"is_valid": False, "error": "Team name contains invalid characters"}
        
        return {"is_valid": True, "sanitized_name": name}
    
    @staticmethod
    def validate_file_upload(
        file_content: bytes,
        allowed_extensions: List[str],
        max_size_mb: int = 10
    ) -> Dict[str, Union[bool, str]]:
        """
        Validate file upload.
        
        Args:
            file_content: File content as bytes
            allowed_extensions: List of allowed file extensions
            max_size_mb: Maximum file size in MB
            
        Returns:
            Validation result
        """
        # Check file size
        size_mb = len(file_content) / (1024 * 1024)
        if size_mb > max_size_mb:
            return {"is_valid": False, "error": f"File size exceeds {max_size_mb}MB limit"}
        
        # Additional file type validation could be added here
        # (e.g., magic number checking)
        
        return {"is_valid": True}
    
    @staticmethod
    def validate_search_query(query: str) -> Dict[str, Union[bool, str]]:
        """
        Validate search query.
        
        Args:
            query: Search query to validate
            
        Returns:
            Validation result
        """
        if not query or not query.strip():
            return {"is_valid": False, "error": "Search query cannot be empty"}
        
        query = query.strip()
        
        if len(query) < 2:
            return {"is_valid": False, "error": "Search query must be at least 2 characters"}
        
        if len(query) > 200:
            return {"is_valid": False, "error": "Search query must be less than 200 characters"}
        
        # Remove potentially dangerous characters
        sanitized_query = re.sub(r'[<>"\';]', '', query)
        
        return {"is_valid": True, "sanitized_query": sanitized_query}
    
    # Private helper methods
    
    @staticmethod
    def _has_common_patterns(password: str) -> bool:
        """Check if password has common weak patterns."""
        common_patterns = [
            "123456", "password", "qwerty", "abc123", "admin",
            "letmein", "welcome", "monkey", "dragon"
        ]
        
        password_lower = password.lower()
        return any(pattern in password_lower for pattern in common_patterns)
    
    @staticmethod
    def _contains_inappropriate_content(text: str) -> bool:
        """Check if text contains inappropriate content."""
        # Basic inappropriate content detection
        inappropriate_words = [
            # Add inappropriate words/phrases as needed
            # This is a simplified list
        ]
        
        text_lower = text.lower()
        return any(word in text_lower for word in inappropriate_words)
    
    @staticmethod
    def _get_json_depth(obj: Any, depth: int = 0) -> int:
        """Get the maximum depth of a JSON object."""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(ValidationUtils._get_json_depth(value, depth + 1) for value in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(ValidationUtils._get_json_depth(item, depth + 1) for item in obj)
        else:
            return depth


class InputSanitizer:
    """Utility class for sanitizing various types of input."""
    
    @staticmethod
    def sanitize_for_database(value: str) -> str:
        """
        Sanitize input for database storage.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
        """
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Limit length
        value = value[:10000]  # Reasonable limit for most fields
        
        return value
    
    @staticmethod
    def sanitize_for_logging(value: str, max_length: int = 500) -> str:
        """
        Sanitize input for logging (remove sensitive data).
        
        Args:
            value: Value to sanitize
            max_length: Maximum length for log entry
            
        Returns:
            Sanitized value safe for logging
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Remove potential sensitive patterns
        sensitive_patterns = [
            r'password["\s]*[:=]["\s]*[^"&\s]+',
            r'token["\s]*[:=]["\s]*[^"&\s]+',
            r'key["\s]*[:=]["\s]*[^"&\s]+',
        ]
        
        for pattern in sensitive_patterns:
            value = re.sub(pattern, '[REDACTED]', value, flags=re.IGNORECASE)
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length] + "..."
        
        return value