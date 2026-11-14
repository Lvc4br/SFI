from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from sfi_api.config import get_settings

_password_hash = PasswordHash.recommended()
_issuer = "sfi-api"
_audience = "sfi-clients"


def jwt_is_configured() -> bool:
    secret = get_settings().jwt_secret_key
    return bool(secret and len(secret.encode("utf-8")) >= 32)


def _jwt_secret() -> str:
    secret = get_settings().jwt_secret_key
    if not secret or len(secret.encode("utf-8")) < 32:
        raise RuntimeError("SFI_JWT_SECRET_KEY deve ter pelo menos 32 bytes.")
    return secret


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(subject: str, token_version: int = 0) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iss": _issuer,
        "aud": _audience,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid4()),
        "ver": token_version,
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        _jwt_secret(),
        algorithms=[settings.jwt_algorithm],
        issuer=_issuer,
        audience=_audience,
        options={"require": ["sub", "iss", "aud", "iat", "exp", "jti", "ver"]},
    )
