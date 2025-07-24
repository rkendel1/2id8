"""
Onboarding routes for user registration and initial setup.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_database_session
from app.schemas.user import UserCreate, UserResponse, UserToken, UserLogin
from app.services.user_service import UserService
from app.core.logging import logger

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_database_session)
):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created user data
        
    Raises:
        HTTPException: If user already exists or registration fails
    """
    logger.info(f"Registering new user: {user_data.username}")
    
    user_service = UserService(db)
    
    try:
        # Check if user already exists
        if user_service.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        if user_service.get_user_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username already exists"
            )
        
        # Create user
        user = user_service.create_user(user_data)
        logger.info(f"Successfully registered user: {user.username}")
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/login", response_model=UserToken)
async def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_database_session)
):
    """
    Authenticate user and return access token.
    
    Args:
        login_data: User login credentials
        db: Database session
        
    Returns:
        Authentication token and user data
        
    Raises:
        HTTPException: If credentials are invalid
    """
    logger.info(f"Login attempt for user: {login_data.username}")
    
    user_service = UserService(db)
    
    try:
        # Authenticate user
        user = user_service.authenticate_user(login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Generate token
        token_data = user_service.create_access_token(user)
        logger.info(f"Successfully authenticated user: {user.username}")
        
        return token_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.get("/verify-email/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_database_session)
):
    """
    Verify user email address.
    
    Args:
        token: Email verification token
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    logger.info(f"Email verification attempt with token: {token[:10]}...")
    
    user_service = UserService(db)
    
    try:
        success = user_service.verify_email(token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        logger.info("Email verification successful")
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during email verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )