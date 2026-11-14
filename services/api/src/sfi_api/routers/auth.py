import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.config import get_settings
from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.login_attempt import LoginAttempt
from sfi_api.models.refresh_token import RefreshToken
from sfi_api.models.revoked_access_token import RevokedAccessToken
from sfi_api.models.security_event import SecurityEvent
from sfi_api.models.user import User
from sfi_api.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SecurityEventResponse,
    TimezoneUpdateRequest,
    TokenResponse,
    UserResponse,
)
from sfi_api.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    jwt_is_configured,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
_bearer = HTTPBearer(auto_error=False)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _record_security_event(
    session: AsyncSession,
    request: Request,
    event_type: str,
    user_id: uuid.UUID | None = None,
) -> None:
    client_host = request.client.host if request.client is not None else None
    source_ip_hash = (
        hashlib.sha256(client_host.encode()).hexdigest() if client_host else None
    )
    user_agent = request.headers.get("user-agent", "")[:256] or None
    session.add(
        SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            source_ip_hash=source_ip_hash,
            user_agent=user_agent,
        )
    )


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _login_attempt_key(email: str, client_host: str) -> str:
    material = f"{email.strip().lower()}|{client_host}".encode()
    return hashlib.sha256(material).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _refresh_expiration() -> datetime:
    return datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days)


def _is_web_client(request: Request) -> bool:
    return request.headers.get("x-sfi-client") == "web"


def _cookie_options() -> dict:
    settings = get_settings()
    return {
        "secure": settings.refresh_cookie_secure or settings.environment.lower() == "production",
        "samesite": settings.refresh_cookie_samesite,
        "domain": settings.refresh_cookie_domain,
        "path": f"{settings.api_prefix}/auth",
    }


def _set_auth_cookies(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    options = _cookie_options()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        **options,
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=secrets.token_urlsafe(32),
        httponly=False,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        **{**options, "path": "/"},
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    options = _cookie_options()
    response.delete_cookie(key=settings.refresh_cookie_name, **options)
    response.delete_cookie(key=settings.csrf_cookie_name, **{**options, "path": "/"})


def _require_csrf(request: Request) -> None:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.csrf_cookie_name, "")
    header_token = request.headers.get("x-csrf-token", "")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="Validação CSRF ausente ou inválida.")


async def _token_response(
    user: User,
    session: AsyncSession,
    family_id: uuid.UUID | None = None,
    response: Response | None = None,
    include_refresh_token: bool = True,
) -> TokenResponse:
    access_token, expires_in = create_access_token(str(user.id), user.token_version)
    refresh_token = _new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=_hash_refresh_token(refresh_token),
            expires_at=_refresh_expiration(),
        )
    )
    await session.commit()
    if response is not None:
        _set_auth_cookies(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token if include_refresh_token else None,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    if not jwt_is_configured():
        raise HTTPException(status_code=503, detail="Autenticação não configurada.")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        timezone=payload.timezone,
    )
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail.",
        ) from None
    _record_security_event(session, request, "account_registered", user.id)
    web_client = _is_web_client(request)
    return await _token_response(
        user,
        session,
        response=response if web_client else None,
        include_refresh_token=not web_client,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    if not jwt_is_configured():
        raise HTTPException(status_code=503, detail="Autenticação não configurada.")

    now = datetime.now(UTC)
    client_host = request.client.host if request.client is not None else "unknown"
    attempt_key = _login_attempt_key(payload.email, client_host)
    await session.execute(
        delete(LoginAttempt).where(
            LoginAttempt.updated_at < now - timedelta(days=30)
        )
    )
    attempt = await session.scalar(
        select(LoginAttempt)
        .where(LoginAttempt.key_hash == attempt_key)
        .with_for_update()
    )
    if attempt is not None:
        locked_until = (
            _as_utc(attempt.locked_until) if attempt.locked_until is not None else None
        )
        if locked_until is not None and locked_until > now:
            retry_after = max(1, ceil((locked_until - now).total_seconds()))
            _record_security_event(session, request, "login_rate_limited")
            await session.commit()
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde antes de tentar novamente.",
                headers={"Retry-After": str(retry_after)},
            )
        window_started = _as_utc(attempt.window_started_at)
        if now - window_started >= timedelta(minutes=15) or locked_until is not None:
            attempt.failed_attempts = 0
            attempt.window_started_at = now
            attempt.locked_until = None

    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    password_valid = user is not None and verify_password(
        payload.password, user.password_hash
    )
    if not password_valid:
        _record_security_event(
            session, request, "login_failed", user.id if user is not None else None
        )
        if attempt is None:
            attempt = LoginAttempt(
                key_hash=attempt_key,
                failed_attempts=0,
                window_started_at=now,
            )
            session.add(attempt)
        attempt.failed_attempts += 1
        if attempt.failed_attempts >= 5:
            attempt.locked_until = now + timedelta(minutes=15)
            _record_security_event(
                session, request, "login_rate_limited", user.id if user is not None else None
            )
            await session.commit()
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde antes de tentar novamente.",
                headers={"Retry-After": "900"},
            )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta desativada.")
    if attempt is not None:
        await session.delete(attempt)
    _record_security_event(session, request, "login_succeeded", user.id)
    web_client = _is_web_client(request)
    return await _token_response(
        user,
        session,
        response=response if web_client else None,
        include_refresh_token=not web_client,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    settings = get_settings()
    body_token = payload.refresh_token if payload is not None else None
    cookie_token = request.cookies.get(settings.refresh_cookie_name) if request else None
    from_cookie = body_token is None
    refresh_token = body_token or cookie_token
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")
    if from_cookie:
        _require_csrf(request)
    token_hash = _hash_refresh_token(refresh_token)
    result = await session.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    stored = result.scalar_one_or_none()
    if stored is None:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")

    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == stored.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        _record_security_event(session, request, "refresh_reuse_detected", stored.user_id)
        await session.commit()
        raise HTTPException(status_code=401, detail="Reutilização detectada; sessão revogada.")

    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado.")

    user = await session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    replacement = _new_refresh_token()
    replacement_hash = _hash_refresh_token(replacement)
    stored.revoked_at = now
    stored.replaced_by_hash = replacement_hash
    session.add(
        RefreshToken(
            user_id=stored.user_id,
            family_id=stored.family_id,
            token_hash=replacement_hash,
            expires_at=_refresh_expiration(),
        )
    )
    access_token, expires_in = create_access_token(str(user.id), user.token_version)
    _record_security_event(session, request, "refresh_rotated", user.id)
    await session.commit()
    web_client = from_cookie or _is_web_client(request)
    if web_client and response is not None:
        _set_auth_cookies(response, replacement)
    return TokenResponse(
        access_token=access_token,
        refresh_token=None if web_client else replacement,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:  # noqa: B008
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_payload = decode_access_token(credentials.credentials)
    revoked_token = RevokedAccessToken(
        user_id=user.id,
        jti=access_payload["jti"],
        expires_at=datetime.fromtimestamp(access_payload["exp"], UTC),
    )
    session.add(revoked_token)

    body_refresh_token = payload.refresh_token if payload is not None else None
    cookie_refresh_token = (
        request.cookies.get(get_settings().refresh_cookie_name) if request else None
    )
    from_cookie = body_refresh_token is None and cookie_refresh_token is not None
    refresh_token = body_refresh_token or cookie_refresh_token
    if from_cookie:
        _require_csrf(request)

    if refresh_token is not None:
        refresh_result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == _hash_refresh_token(refresh_token),
                RefreshToken.user_id == user.id,
            ).with_for_update()
        )
        refresh_record = refresh_result.scalar_one_or_none()
        if refresh_record is not None:
            await session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == refresh_record.family_id,
                    RefreshToken.user_id == user.id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(UTC))
            )

    _record_security_event(session, request, "logout", user.id)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este token já foi revogado.",
        ) from None
    if response is not None and (from_cookie or (request and _is_web_client(request))):
        _clear_auth_cookies(response)


@router.get("/security-events", response_model=list[SecurityEventResponse])
async def list_security_events(
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[SecurityEventResponse]:
    result = await session.scalars(
        select(SecurityEvent)
        .where(SecurityEvent.user_id == user.id)
        .order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc())
        .limit(limit)
    )
    return [SecurityEventResponse.model_validate(event) for event in result.all()]


@router.patch("/me/timezone", response_model=UserResponse)
async def update_timezone(
    payload: TimezoneUpdateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> UserResponse:
    user.timezone = payload.timezone
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha atual incorreta.",
        )
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A nova senha deve ser diferente da senha atual.",
        )

    now = datetime.now(UTC)
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    _record_security_event(session, request, "password_changed", user.id)
    await session.commit()
    if _is_web_client(request):
        _clear_auth_cookies(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    user.token_version += 1
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    _record_security_event(session, request, "logout_all", user.id)
    await session.commit()
    if _is_web_client(request):
        _clear_auth_cookies(response)
