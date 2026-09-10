"""Authentication responses containing public identifiers only."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AuthOptions(BaseModel):
    local_admin_login_enabled: bool


class LocalAdminErrorDetail(BaseModel):
    code: Literal["not_found", "local_admin_unavailable"]
    message: str


class LocalAdminErrorResponse(BaseModel):
    detail: LocalAdminErrorDetail


class AuthenticatedUser(BaseModel):
    public_id: UUID
    username: str
    tenant_id: UUID
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    is_super_admin: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: AuthenticatedUser
