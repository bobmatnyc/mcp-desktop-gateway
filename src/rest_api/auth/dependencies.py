"""
Authentication dependencies for REST API
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Security scheme
security = HTTPBearer()

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class User(BaseModel):
    """User model for authentication"""
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: bool = True
    is_claude_ai: bool = False  # Flag for Claude.AI users
    permissions: list[str] = []


class TokenData(BaseModel):
    """Token payload data"""
    sub: str  # Subject (user ID)
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    email: Optional[str] = None
    is_claude_ai: bool = False


def create_access_token(user_id: str, email: Optional[str] = None, is_claude_ai: bool = False) -> str:
    """Create a JWT access token"""
    now = datetime.utcnow()
    expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "sub": user_id,
        "email": email,
        "is_claude_ai": is_claude_ai,
        "iat": now,
        "exp": expire
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenData(**payload)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from JWT token
    
    For development, accepts a special token "dev-token" that creates a test user.
    In production, this should verify against your user database.
    """
    token = credentials.credentials
    
    # Development mode - accept test token
    if token == "dev-token":
        return User(
            id="dev-user",
            email="dev@example.com",
            name="Development User",
            is_active=True,
            permissions=["*"]  # All permissions in dev mode
        )
    
    # Verify JWT token
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create user from token data
    # In production, you would fetch the user from database here
    user = User(
        id=token_data.sub,
        email=token_data.email,
        is_claude_ai=token_data.is_claude_ai,
        is_active=True
    )
    
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
        
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_permission(permission: str):
    """Dependency to require specific permission"""
    async def permission_checker(user: User = Depends(get_current_user)):
        if "*" in user.permissions or permission in user.permissions:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission}"
        )
    return permission_checker


# Claude.AI specific authentication
async def get_claude_ai_user(user: User = Depends(get_current_user)) -> User:
    """Ensure the user is authenticated via Claude.AI"""
    if not user.is_claude_ai:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Claude.AI authentication"
        )
    return user