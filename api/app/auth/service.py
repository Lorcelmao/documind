import uuid
from datetime import UTC, datetime, timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security
from app.config import get_settings
from app.models import RefreshToken, User

# verified against when the email is unknown, so login latency does not
# reveal whether an account exists
_DUMMY_HASH = security.hash_password("timing-equalizer-dummy-password")


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
    password_hash = await run_in_threadpool(security.hash_password, password)
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # concurrent register with the same email lost the race on the unique index
        await db.rollback()
        raise EmailTakenError from None
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    password_hash = user.password_hash if user is not None else _DUMMY_HASH
    # argon2 is CPU heavy; the threadpool keeps the event loop free
    valid = await run_in_threadpool(security.verify_password, password, password_hash)
    if user is None or not valid:
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

    The revocation is an atomic claim: under concurrency exactly one request
    wins the UPDATE, every other request sees zero rows and goes through the
    replay handling instead of minting a second live session.
    """
    token_hash = security.hash_refresh_token(raw)
    now = datetime.now(UTC)

    claimed = (
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
            .returning(RefreshToken.id, RefreshToken.user_id, RefreshToken.expires_at)
        )
    ).first()

    if claimed is None:
        await _handle_replayed_token(db, token_hash, now)
        raise InvalidRefreshTokenError

    token_id, user_id, expires_at = claimed
    if expires_at <= now:
        await db.commit()  # keep the expired token revoked
        raise InvalidRefreshTokenError

    new_raw, new_hash = security.generate_refresh_token()
    ttl = timedelta(days=get_settings().refresh_token_ttl_days)
    new_token = RefreshToken(user_id=user_id, token_hash=new_hash, expires_at=now + ttl)
    db.add(new_token)
    await db.flush()
    await db.execute(
        update(RefreshToken).where(RefreshToken.id == token_id).values(replaced_by=new_token.id)
    )
    await db.commit()
    return user_id, new_raw


async def _handle_replayed_token(db: AsyncSession, token_hash: str, now: datetime) -> None:
    """A token that could not be claimed is either unknown or already revoked.

    Recently revoked tokens get a short grace window because two tabs or a
    re-run client effect can legitimately race the rotation. A replay outside
    that window means the token leaked, so every active session is revoked.
    """
    token = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token is None or token.revoked_at is None:
        return
    grace = timedelta(seconds=get_settings().refresh_reuse_grace_seconds)
    if now - token.revoked_at <= grace:
        return
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == token.user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await db.commit()


async def revoke_refresh_token(db: AsyncSession, raw: str) -> None:
    token_hash = security.hash_refresh_token(raw)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
