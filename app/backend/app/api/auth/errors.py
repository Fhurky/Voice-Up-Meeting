"""Safe transport mapping for the local administrator selection boundary."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas.auth.response import LocalAdminErrorDetail, LocalAdminErrorResponse
from app.services.auth_service import LocalAdminUnavailableError


def register_auth_errors(application: FastAPI) -> None:
    @application.exception_handler(LocalAdminUnavailableError)
    async def local_admin_unavailable(
        _request: Request, _exc: LocalAdminUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=LocalAdminErrorResponse(
                detail=LocalAdminErrorDetail(
                    code="local_admin_unavailable",
                    message="An unambiguous active local administrator is unavailable.",
                )
            ).model_dump(),
            headers={"Cache-Control": "no-store"},
        )
