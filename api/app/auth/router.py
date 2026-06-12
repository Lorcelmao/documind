from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.auth import service
from app.auth.deps import CurrentUser
from app.auth.schemas import AccessTokenResponse, LoginRequest, RegisterRequest, UserResponse
from app.auth.security import create_access_token
from app.config import get_settings
from app.database import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, raw: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/auth",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(body: RegisterRequest, db: DbSession) -> UserResponse:
    try:
        user = await service.register_user(db, body.email.lower(), body.password)
    except service.EmailTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    return user


@router.post("/login", response_model=AccessTokenResponse)
async def login(body: LoginRequest, response: Response, db: DbSession) -> AccessTokenResponse:
    try:
        user = await service.authenticate(db, body.email.lower(), body.password)
    except service.InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from None
    raw = await service.issue_refresh_token(db, user.id)
    _set_refresh_cookie(response, raw)
    return AccessTokenResponse(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    try:
        user_id, new_raw = await service.rotate_refresh_token(db, refresh_token)
    except service.InvalidRefreshTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from None
    _set_refresh_cookie(response, new_raw)
    return AccessTokenResponse(access_token=create_access_token(user_id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    if refresh_token is not None:
        await service.revoke_refresh_token(db, refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path="/auth")


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return user
