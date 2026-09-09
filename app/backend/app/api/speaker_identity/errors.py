"""Typed error mapping shared by speaker endpoints and their dependencies."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.services.speaker_ports import SpeakerError
from app.services.speaker_service import error_message


def register_speaker_errors(application: FastAPI) -> None:
    @application.exception_handler(SpeakerError)
    async def speaker_error(_request: Request, exc: SpeakerError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": error_message(exc.code)}},
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message": error_message("validation_error"),
                }
            },
        )

    @application.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        codes = {
            400: "invalid_request",
            401: "unauthenticated",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            413: "audio_limit",
            415: "unsupported_audio",
        }
        code = codes.get(exc.status_code, "request_failed")
        message = (
            "Invalid or missing access token." if exc.status_code == 401 else error_message(code)
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": code, "message": message}},
            headers=exc.headers,
        )
