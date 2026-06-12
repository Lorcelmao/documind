import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Workspace, WorkspaceMember


class UserNotFoundError(Exception):
    pass


class AlreadyMemberError(Exception):
    pass


async def create_workspace(db: AsyncSession, owner_id: uuid.UUID, name: str) -> Workspace:
    workspace = Workspace(name=name)
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner_id, role="owner"))
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def list_user_workspaces(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Workspace, str]]:
    rows = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at)
    )
    return [(workspace, role) for workspace, role in rows.all()]


async def get_membership(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    return await db.get(WorkspaceMember, (workspace_id, user_id))


async def list_members(
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[tuple[WorkspaceMember, str]]:
    rows = await db.execute(
        select(WorkspaceMember, User.email)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at)
    )
    return [(member, email) for member, email in rows.all()]


async def add_member(
    db: AsyncSession, workspace_id: uuid.UUID, email: str, role: str
) -> tuple[WorkspaceMember, str]:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise UserNotFoundError
    existing = await db.get(WorkspaceMember, (workspace_id, user.id))
    if existing is not None:
        raise AlreadyMemberError
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role)
    db.add(member)
    await db.commit()
    return member, user.email
