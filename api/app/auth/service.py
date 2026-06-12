import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security
from app.config import get_settings
from app.models import RefreshToken, User


class EmailTakenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailTakenError
    user = User(email=email, password_hash=security.hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not security.verify_password(password, user.password_hash):
        raise InvalidCredentialsError
    return user


async def issue_refresh_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    raw, token_hash = security.generate_refresh_token()
    ttl = timedelta(days=get_settings().refresh_token_ttl_days)
    db.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=datetime.now(UTC) + ttl))
    await db.commit()
    return raw


async def rotate_refresh_token(db: AsyncSession, raw: str) -> tuple[uuid.UUID, str]:
    """Validate the presented token and replace it with a fresh one.

    A revoked token showing up again means it was stolen or replayed, so every
    active session for that user gets revoked.
    """
    token_hash = security.hash_refresh_token(raw)
    token = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token is None:
        raise InvalidRefreshTokenError

    now = datetime.now(UTC)
    if token.revoked_at is not None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        raise InvalidRefreshTokenError
    if token.expires_at <= now:
        raise InvalidRefreshTokenError

    new_raw, new_hash = security.generate_refresh_token()
    ttl = timedelta(days=get_settings().refresh_token_ttl_days)
    new_token = RefreshToken(user_id=token.user_id, token_hash=new_hash, expires_at=now + ttl)
    db.add(new_token)
    await db.flush()
    token.revoked_at = now
    token.replaced_by = new_token.id
    await db.commit()
    return token.user_id, new_raw


async def revoke_refresh_token(db: AsyncSession, raw: str) -> None:
    token_hash = security.hash_refresh_token(raw)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
