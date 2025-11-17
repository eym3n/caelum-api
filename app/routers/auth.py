"""Authentication router with JWT-based endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import User, UserCreate, Token, RefreshTokenRequest
from app.db import get_users_collection
from app.utils.security import verify_password, get_password_hash
from app.utils.jwt import create_access_token, create_refresh_token, verify_token
from app.deps import get_current_user
from pymongo.errors import DuplicateKeyError
import uuid

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    """
    Register a new user account.

    Args:
        user_in: User registration data (email, password, optional full_name)

    Returns:
        The created user

    Raises:
        HTTPException: If email already exists or database unavailable
    """
    users_collection = get_users_collection()
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )

    # Check if user with email already exists
    existing_user = users_collection.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user document
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()

    user_doc = {
        "_id": user_id,
        "email": user_in.email,
        "full_name": user_in.full_name,
        "hashed_password": get_password_hash(user_in.password),
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }

    try:
        users_collection.insert_one(user_doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    return User(
        id=user_id,
        email=user_in.email,
        full_name=user_in.full_name,
        is_active=True,
        is_superuser=False,
        created_at=now,
        updated_at=now,
    )


@router.post("/login", response_model=Token)
async def login(email: str, password: str):
    """
    Login with email and password to get access and refresh tokens.

    Args:
        email: User's email address
        password: User's password

    Returns:
        Access token and refresh token

    Raises:
        HTTPException: If credentials are invalid or database unavailable
    """
    users_collection = get_users_collection()
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )

    # Find user by email
    user_data = users_collection.find_one({"email": email})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    # Create tokens
    user_id = user_data["_id"]
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Get a new access token using a refresh token.

    Args:
        request: Request containing the refresh token

    Returns:
        New access token and refresh token

    Raises:
        HTTPException: If refresh token is invalid
    """
    # Verify refresh token
    token_data = verify_token(request.refresh_token, token_type="refresh")
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    users_collection = get_users_collection()
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )

    user_data = users_collection.find_one({"_id": token_data.sub})
    if not user_data or not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens
    user_id = token_data.sub
    access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    return Token(
        access_token=access_token, refresh_token=new_refresh_token, token_type="bearer"
    )


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.

    Args:
        current_user: The current authenticated user (from JWT token)

    Returns:
        Current user's information
    """
    return current_user


@router.get("/test-protected")
async def test_protected(current_user: User = Depends(get_current_user)):
    """
    Test endpoint to verify authentication is working.

    Args:
        current_user: The current authenticated user (from JWT token)

    Returns:
        Success message with user email
    """
    return {
        "message": "Authentication is working!",
        "user_email": current_user.email,
        "user_id": current_user.id,
    }
