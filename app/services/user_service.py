"""
User service for user management and authentication.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import secrets
from app.models.user import User
from app.schemas.user import UserCreate, UserToken, UserResponse
from app.core.config import settings
from app.core.logging import logger


class UserService:
    """Service class for user management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user
            
        Raises:
            IntegrityError: If user already exists
        """
        try:
            # Hash password
            hashed_password = self._hash_password(user_data.password)
            
            # Create user
            user = User(
                email=user_data.email,
                username=user_data.username,
                full_name=user_data.full_name,
                bio=user_data.bio,
                avatar_url=user_data.avatar_url,
                hashed_password=hashed_password,
                is_active=True,
                is_verified=False
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Created user: {user.username}")
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"User creation failed - integrity error: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"User creation failed: {e}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username/password.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            Authenticated user or None
        """
        # Try to find user by username or email
        user = self.get_user_by_username(username) or self.get_user_by_email(username)
        
        if not user:
            return None
        
        if not self._verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def create_access_token(self, user: User) -> UserToken:
        """
        Create access token for user.
        
        Args:
            user: User to create token for
            
        Returns:
            Token data
        """
        # TODO: Implement proper JWT token generation
        # For now, return a placeholder token
        token = self._generate_token(user.id)
        
        return UserToken(
            access_token=token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.from_orm(user)
        )
    
    def verify_email(self, token: str) -> bool:
        """
        Verify user email with token.
        
        Args:
            token: Email verification token
            
        Returns:
            True if verification successful
        """
        # TODO: Implement proper email verification
        # For now, return True as placeholder
        logger.info(f"Email verification attempted with token: {token[:10]}...")
        return True
    
    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """
        Update user data.
        
        Args:
            user_id: User ID to update
            **kwargs: Fields to update
            
        Returns:
            Updated user or None
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        try:
            for key, value in kwargs.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Updated user {user_id}")
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate user account.
        
        Args:
            user_id: User ID to deactivate
            
        Returns:
            True if successful
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        try:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Deactivated user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256."""
        # TODO: Use proper password hashing like bcrypt
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        try:
            salt, password_hash = hashed_password.split(":")
            computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return password_hash == computed_hash
        except Exception:
            return False
    
    def _generate_token(self, user_id: int) -> str:
        """Generate access token."""
        # TODO: Implement proper JWT token generation
        return f"token_{user_id}_{secrets.token_urlsafe(32)}"