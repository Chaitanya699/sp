"""
NIM Sentinel Core Security Module

JWT authentication, RBAC, password hashing, and security utilities.
"""

import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from nim_sentinel.core.config import get_settings
from nim_sentinel.core.errors import (
    InvalidTokenError,
    TokenExpiredError,
)
from passlib.context import CryptContext
from pydantic import BaseModel

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Decoded JWT token data."""
    sub: str  # user_id
    username: str
    roles: list[str]
    tenant_id: str | None = None
    exp: int
    iat: int
    jti: str  # JWT ID for revocation


class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: str
    hashed_password: str
    roles: list[str]
    tenant_id: str | None = None
    is_active: bool = True
    created_at: datetime
    last_login: datetime | None = None


class RolePermissions(BaseModel):
    """Role-based permissions."""
    role: str
    permissions: set[str]
    description: str = ""


# Default role permissions
DEFAULT_ROLES = {
    "admin": RolePermissions(
        role="admin",
        permissions={"*"},
        description="Full system access",
    ),
    "analyst": RolePermissions(
        role="analyst",
        permissions={
            "chat",
            "documents:read",
            "documents:write",
            "documents:delete",
            "threads:read",
            "threads:write",
            "mongo:query",
            "web:search",
            "vision:analyze",
        },
        description="Data analyst with document and query access",
    ),
    "viewer": RolePermissions(
        role="viewer",
        permissions={
            "chat",
            "documents:read",
            "threads:read",
            "vision:analyze",
        },
        description="Read-only access",
    ),
}


def create_access_token(
    user_id: str,
    username: str,
    roles: list[str],
    tenant_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiration_minutes)

    jti = secrets.token_urlsafe(16)
    to_encode = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "tenant_id": tenant_id,
        "exp": int(expire.timestamp()),
        "iat": int(time.time()),
        "jti": jti,
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenData(**payload)
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError() from e
        raise InvalidTokenError(str(e)) from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"nim_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return hash_api_key(api_key) == hashed_key


def check_permission(user_roles: list[str], required_permission: str) -> bool:
    """Check if user has a specific permission."""
    # Admin has all permissions
    if "admin" in user_roles:
        return True

    # Check each role
    for role in user_roles:
        if role in DEFAULT_ROLES:
            role_perms = DEFAULT_ROLES[role].permissions
            if "*" in role_perms or required_permission in role_perms:
                return True

    return False


def check_any_permission(user_roles: list[str], required_permissions: list[str]) -> bool:
    """Check if user has any of the required permissions."""
    return any(check_permission(user_roles, perm) for perm in required_permissions)


def check_all_permissions(user_roles: list[str], required_permissions: list[str]) -> bool:
    """Check if user has all required permissions."""
    return all(check_permission(user_roles, perm) for perm in required_permissions)


def get_user_permissions(user_roles: list[str]) -> set[str]:
    """Get all permissions for a user's roles."""
    permissions = set()
    for role in user_roles:
        if role in DEFAULT_ROLES:
            permissions.update(DEFAULT_ROLES[role].permissions)
    return permissions


class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - window_seconds

        if key not in self._requests:
            self._requests[key] = []

        # Clean old requests
        self._requests[key] = [ts for ts in self._requests[key] if ts > window_start]

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(now)
        return True

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in window."""
        now = time.time()
        window_start = now - window_seconds

        if key not in self._requests:
            return max_requests

        current = len([ts for ts in self._requests[key] if ts > window_start])
        return max(0, max_requests - current)

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._requests:
            del self._requests[key]


# Global rate limiter instance (replace with Redis in production)
rate_limiter = RateLimiter()


def sanitize_input(text: str, max_length: int = 100000) -> str:
    """Sanitize user input."""
    if not text:
        return ""

    # Truncate
    if len(text) > max_length:
        text = text[:max_length]

    # Remove null bytes
    text = text.replace("\x00", "")

    # Normalize whitespace
    text = " ".join(text.split())

    return text


def validate_file_type(filename: str, allowed_extensions: list[str]) -> bool:
    """Validate file extension."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    return ext in [e.lower().lstrip(".") for e in allowed_extensions]


def generate_correlation_id() -> str:
    """Generate a correlation ID for request tracing."""
    return secrets.token_urlsafe(16)


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return secrets.compare_digest(a, b)
