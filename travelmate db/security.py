# app/core/security.py
# ============================================================
#  Security — Password hashing, JWT creation & verification
# ============================================================

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import get_settings

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plain-text password. Never store plain passwords."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain password against its hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT tokens ────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    data should contain: {"sub": user_id}
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    Raises JWTError if invalid or expired.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def extract_user_id(token: str) -> Optional[str]:
    """Extract user_id from token, returns None if invalid."""
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None
