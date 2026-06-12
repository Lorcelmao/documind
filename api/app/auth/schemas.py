import uuid

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    # bounded so oversized input cannot be fed into argon2
    password: str = Field(max_length=128)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str

    model_config = {"from_attributes": True}


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
