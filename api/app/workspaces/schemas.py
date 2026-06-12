import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "member"]


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: Role


class MemberAddRequest(BaseModel):
    email: EmailStr
    role: Role = "member"


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: Role
