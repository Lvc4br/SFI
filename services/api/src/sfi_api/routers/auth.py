from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.revoked_access_token import RevokedAccessToken
from sfi_api.models.user import User
from sfi_api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from sfi_api.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    jwt_is_configured,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
_bearer = HTTPBearer(auto_error=False)


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    if not jwt_is_configured():
        raise HTTPException(status_code=503, detail="Autenticação não configurada.")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
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
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    if not jwt_is_configured():
        raise HTTPException(status_code=503, detail="Autenticação não configurada.")

    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta desativada.")
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:  # noqa: B008
    return UserResponse.model_validate(user)



@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
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

    payload = decode_access_token(credentials.credentials)
    revoked_token = RevokedAccessToken(
        user_id=user.id,
        jti=payload["jti"],
        expires_at=datetime.fromtimestamp(payload["exp"], UTC),
    )
    session.add(revoked_token)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este token já foi revogado.",
        ) from None
