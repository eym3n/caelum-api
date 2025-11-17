"""JWT token utilities for authentication."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from app.config import Config
from app.models.user import TokenPayload


def create_access_token(user_id: str) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user_id: The user's unique identifier

    Returns:
        Encoded JWT access token
    """
    expires_delta = timedelta(minutes=Config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {"sub": user_id, "exp": expire, "type": "access"}

    encoded_jwt = jwt.encode(
        to_encode, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token for a user.

    Args:
        user_id: The user's unique identifier

    Returns:
        Encoded JWT refresh token
    """
    expires_delta = timedelta(days=Config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {"sub": user_id, "exp": expire, "type": "refresh"}

    encoded_jwt = jwt.encode(
        to_encode, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
        )

        token_data = TokenPayload(**payload)

        # Verify token type matches
        if token_data.type != token_type:
            return None

        # Check if token is expired
        # Make sure both datetimes are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        # Ensure exp is timezone-aware
        if token_data.exp.tzinfo is None:
            # If exp is naive, assume it's UTC
            token_exp = token_data.exp.replace(tzinfo=timezone.utc)
        else:
            token_exp = token_data.exp

        if token_exp < now:
            return None

        return token_data

    except JWTError:
        return None
