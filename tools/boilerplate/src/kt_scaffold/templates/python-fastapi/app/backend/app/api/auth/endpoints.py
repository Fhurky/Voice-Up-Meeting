"""Login and current-user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import CurrentContext
from app.db.session import get_db
from app.schemas.auth.request import LoginRequest
from app.schemas.auth.response import AuthenticatedUser, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(session)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """Authenticate by username or email and issue a signed access token."""

    return await service.authenticate(body.username, body.password.get_secret_value())


@router.get("/me", response_model=AuthenticatedUser)
async def me(
    context: CurrentContext,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    """Return the active user and tenant after authoritative token validation."""

    return await service.current_user(context)
