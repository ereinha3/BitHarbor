from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from passlib.context import CryptContext

from bitharbor.settings import SecuritySettings, get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(
    subject: str,
    security: SecuritySettings | None = None,
    additional_claims: Dict[str, Any] | None = None,
) -> str:
    settings = security or get_settings().security
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: Dict[str, Any] = {"sub": subject, "iat": now, "exp": expire}
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str, security: SecuritySettings | None = None) -> Dict[str, Any]:
    settings = security or get_settings().security
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

