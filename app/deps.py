from fastapi import Header, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.utils.jwt import verify_token
from app.db import get_users_collection
from app.models.user import User, UserInDB


async def get_session_id(x_session_id: Optional[str] = Header(default=None)):
    # Accept session id from header for conversational continuity
    return x_session_id or "anonymous"


# Security scheme for JWT bearer tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify token
    token_data = verify_token(token, token_type="access")
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    users_collection = get_users_collection()
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )

    user_data = users_collection.find_one({"_id": token_data.sub})
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert MongoDB document to UserInDB model
    user_in_db = UserInDB(**user_data)

    # Check if user is active
    if not user_in_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    # Return public user model
    return User(
        id=user_in_db.id,
        email=user_in_db.email,
        full_name=user_in_db.full_name,
        is_active=user_in_db.is_active,
        is_superuser=user_in_db.is_superuser,
        created_at=user_in_db.created_at,
        updated_at=user_in_db.updated_at,
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current active user.

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current superuser.

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user
