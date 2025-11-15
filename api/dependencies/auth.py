"""Authentication dependencies for API endpoints."""

from typing import Optional
from datetime import datetime

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from database import get_db
from database.models import APIKey

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """
    Validate API key from request header.

    Args:
        api_key: API key from X-API-Key header
        db: Database session

    Returns:
        APIKey model if valid, None otherwise

    Raises:
        HTTPException: If API key is invalid or expired
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Look up API key in database
    db_key = db.query(APIKey).filter(APIKey.key == api_key).first()

    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check if key is active
    if not db_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is inactive",
        )

    # Check if key is expired
    if db_key.expires_at and db_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has expired",
        )

    # Update last used timestamp
    db_key.last_used_at = datetime.utcnow()
    db.commit()

    return db_key


async def get_optional_api_key(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """
    Get API key if provided, but don't require it.

    Useful for endpoints that work with or without authentication.
    """
    if not api_key:
        return None

    try:
        return await get_api_key(api_key, db)
    except HTTPException:
        return None


def require_permission(permission: str):
    """
    Dependency factory to require specific permission.

    Args:
        permission: Permission name to require (e.g., "create:video")

    Returns:
        Dependency function that checks permission

    Example:
        @app.post("/api/videos", dependencies=[Depends(require_permission("create:video"))])
        async def create_video():
            ...
    """
    async def permission_checker(
        api_key: APIKey = Depends(get_api_key)
    ):
        # If permissions list is empty or contains "*", allow all
        if not api_key.permissions or "*" in api_key.permissions:
            return api_key

        # Check if required permission is in list
        if permission not in api_key.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}",
            )

        return api_key

    return permission_checker
