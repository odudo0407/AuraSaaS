"""JWT and password hashing utilities."""

from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError
from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None


def decode_access_token_lenient(token: str) -> dict | None:
    """Decode token ignoring expiration — used for refresh."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
    except JWTError:
        return None
