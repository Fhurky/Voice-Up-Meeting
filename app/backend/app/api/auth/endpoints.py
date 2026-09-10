"""Login and current-user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import (
    CurrentContext,
    is_local_admin_request,
    require_local_admin_request,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.auth.request import LoginRequest
from app.schemas.auth.response import (
    AuthenticatedUser,
    AuthOptions,
    LocalAdminErrorResponse,
    LoginResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(session)


@router.get("/options", response_model=AuthOptions)
async def options(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthOptions:
    response.headers["Cache-Control"] = "no-store"
    return AuthOptions(local_admin_login_enabled=is_local_admin_request(request, settings))


@router.post(
    "/local-admin",
    response_model=LoginResponse,
    dependencies=[Depends(require_local_admin_request)],
    responses={code: {"model": LocalAdminErrorResponse} for code in (404, 503)},
)
async def local_admin(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    response.headers["Cache-Control"] = "no-store"
    return await service.authenticate_local_admin(settings.local_admin_username)


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
