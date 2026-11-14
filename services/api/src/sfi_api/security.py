from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from sfi_api.config import get_settings

_password_hash = PasswordHash.recommended()
_issuer = "sfi-api"
_audience = "sfi-clients"


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(subject: str) -> tuple[str, int]:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("SFI_JWT_SECRET_KEY não foi configurada.")
    expires_in = settings.access_token_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iss": _issuer,
        "aud": _audience,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("SFI_JWT_SECRET_KEY não foi configurada.")
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=_issuer,
        audience=_audience,
        options={"require": ["sub", "iss", "aud", "iat", "exp", "jti"]},
    )
