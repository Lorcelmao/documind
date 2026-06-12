import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import CurrentUser
from app.database import DbSession
from app.models import WorkspaceMember
from app.workspaces import service
from app.workspaces.schemas import (
    MemberAddRequest,
    MemberResponse,
    WorkspaceCreateRequest,
    WorkspaceResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def require_workspace_role(*roles: str):
    """Dependency factory: caller must be a member of the workspace with one of the roles."""

    async def check(workspace_id: uuid.UUID, user: CurrentUser, db: DbSession) -> WorkspaceMember:
        membership = await service.get_membership(db, workspace_id, user.id)
        if membership is None:
            # 404 rather than 403 so outsiders cannot probe which workspace ids exist
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
        if membership.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Requires role: " + " or ".join(roles))
        return membership

    return check


AnyMember = Annotated[WorkspaceMember, Depends(require_workspace_role("owner", "member"))]
OwnerOnly = Annotated[WorkspaceMember, Depends(require_workspace_role("owner"))]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WorkspaceResponse)
async def create_workspace(
    body: WorkspaceCreateRequest, user: CurrentUser, db: DbSession
) -> WorkspaceResponse:
    workspace = await service.create_workspace(db, user.id, body.name)
    return WorkspaceResponse(id=workspace.id, name=workspace.name, role="owner")


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(user: CurrentUser, db: DbSession) -> list[WorkspaceResponse]:
    rows = await service.list_user_workspaces(db, user.id)
    return [WorkspaceResponse(id=ws.id, name=ws.name, role=role) for ws, role in rows]


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
async def list_members(
    workspace_id: uuid.UUID, _membership: AnyMember, db: DbSession
) -> list[MemberResponse]:
    rows = await service.list_members(db, workspace_id)
    return [
        MemberResponse(user_id=member.user_id, email=email, role=member.role)
        for member, email in rows
    ]


@router.post(
    "/{workspace_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=MemberResponse,
)
async def add_member(
    workspace_id: uuid.UUID, body: MemberAddRequest, _membership: OwnerOnly, db: DbSession
) -> MemberResponse:
    try:
        member, email = await service.add_member(db, workspace_id, body.email.lower(), body.role)
    except service.UserNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user with that email") from None
    except service.AlreadyMemberError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already a member") from None
    return MemberResponse(user_id=member.user_id, email=email, role=member.role)
