"""Security utilities for password hashing and verification."""

import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    # Convert strings to bytes
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")

    # Verify password
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password as a string
    """
    # Convert password to bytes
    password_bytes = password.encode("utf-8")

    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode("utf-8")
