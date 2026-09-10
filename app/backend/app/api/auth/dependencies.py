"""FastAPI authentication, permission, and super-admin guards."""

import re
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.request_context import RequestContext
from app.middleware.tenant_context import get_request_context_dependency

bearer_scheme = HTTPBearer(auto_error=False)
_LOCAL_AUTHORITY = re.compile(r"(localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?", re.IGNORECASE)


def _local_authority(value: str, scheme: str) -> tuple[str, int] | None:
    match = _LOCAL_AUTHORITY.fullmatch(value)
    if match is None:
        return None
    port = int(match[2]) if match[2] is not None else (443 if scheme == "https" else 80)
    if not 1 <= port <= 65535:
        return None
    return match[1].lower(), port


def is_local_admin_request(request: Request, settings: Settings) -> bool:
    """Validate the explicit development mode and browser origin without proxy-header trust."""
    if not settings.local_admin_login_enabled or settings.environment != "development":
        return False
    scheme = request.url.scheme
    hosts = request.headers.getlist("host")
    if scheme not in {"http", "https"} or len(hosts) != 1:
        return False
    authority = _local_authority(hosts[0], scheme)
    if authority is None:
        return False
    fetch_sites = request.headers.getlist("sec-fetch-site")
    if fetch_sites and fetch_sites != ["same-origin"]:
        return False
    origins = request.headers.getlist("origin")
    if not origins:
        return True
    if len(origins) != 1:
        return False
    try:
        origin = urlsplit(origins[0])
        return (
            origin.scheme == scheme
            and origins[0] == f"{origin.scheme}://{origin.netloc}"
            and _local_authority(origin.netloc, scheme) == authority
        )
    except ValueError:
        return False


def require_local_admin_request(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if not is_local_admin_request(request, settings):
        raise HTTPException(status_code=404, headers={"Cache-Control": "no-store"})


async def get_current_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
    context: Annotated[RequestContext, Depends(get_request_context_dependency)],
) -> RequestContext:
    if credentials is None or not context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return context


CurrentContext = Annotated[RequestContext, Depends(get_current_context)]


class PermissionChecker:
    def __init__(self, permission: str) -> None:
        self.permission = permission

    async def __call__(self, context: CurrentContext) -> None:
        if not context.has_permission(self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {self.permission}",
            )


def require_permission(permission: str) -> PermissionChecker:
    return PermissionChecker(permission)


class SuperAdminChecker:
    async def __call__(self, context: CurrentContext) -> None:
        if not context.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super-admin access required",
            )


def require_super_admin() -> SuperAdminChecker:
    return SuperAdminChecker()
