import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return {}


def hash_device_key(plain: str) -> str:
    """SHA-256 (hex) of an IoT device key.

    Deliberately NOT bcrypt. Device keys are 256-bit random tokens, not
    human-chosen passwords, so there is no dictionary attack to slow down — and
    this runs on the ingest hot path, once per device every few seconds. bcrypt
    would add ~100 ms per reading to defend against nothing.
    """
    return hashlib.sha256(plain.encode()).hexdigest()


def generate_device_key() -> str:
    """Opaque device key. 32 random bytes → 43 URL-safe chars, baked into firmware."""
    return secrets.token_urlsafe(32)
