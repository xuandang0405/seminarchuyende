from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import jwt
import bcrypt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    claims: Optional[dict] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    if claims:
        to_encode.update(claims)
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None


import secrets
import hashlib
import base64
import hmac
from urllib.parse import urlparse


def generate_random_token(nbytes: int = 32) -> str:
    """Generates a cryptographically secure URL-safe random string."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Deterministic SHA-256 hash for storage of refresh tokens and action tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generates a fresh CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(cookie_token: Optional[str], header_token: Optional[str]) -> bool:
    """Verifies CSRF token matching using constant-time comparison."""
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)


def generate_pkce_pair() -> tuple[str, str]:
    """Generates code_verifier and code_challenge (S256) for OAuth 2.0 PKCE."""
    code_verifier = secrets.token_urlsafe(64)
    # S256 challenge: BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


def is_safe_return_url(return_url: Optional[str], allowed_paths: Optional[list[str]] = None) -> bool:
    """Validates that a return URL is safe against open redirect vulnerabilities."""
    if not return_url:
        return True
    
    # Disallow backslashes and protocol-relative URLs
    if "\\" in return_url or return_url.startswith("//"):
        return False
        
    parsed = urlparse(return_url)
    
    # Must be relative path only (no scheme or netloc)
    if parsed.scheme or parsed.netloc:
        return False
        
    path = parsed.path
    if not path.startswith("/"):
        return False

    if allowed_paths:
        # Check if path prefix matches any allowed path
        return any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in allowed_paths)
        
    return True

