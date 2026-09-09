"""Private bounded HTTP transport; embeddings are never a public browser API."""

import json
import logging
from contextlib import asynccontextmanager
from hmac import compare_digest
from time import perf_counter
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .errors import InferenceError
from .runtime import InferenceRuntime

_CONTENT_TYPES = {
    "application/octet-stream",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/x-flac",
}


def create_app(settings: Settings, runtime: InferenceRuntime | None = None) -> FastAPI:
    runtime = runtime or InferenceRuntime(settings)

    @asynccontextmanager
    async def lifespan(_):
        await run_in_threadpool(runtime.initialize)
        yield

    app = FastAPI(
        title="Private speaker inference",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def safe_request_log(request: Request, call_next):
        started = perf_counter()
        status = 500
        job_id = None
        try:
            job_id = str(UUID(request.headers.get("x-job-id", "")))
        except ValueError:
            pass
        route = (
            request.url.path
            if request.url.path in {"/live", "/ready", "/v1/embeddings"}
            else "other"
        )
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            logging.getLogger("voiceup.inference").info(
                json.dumps(
                    {
                        "event": "inference_http",
                        "route": route,
                        "job_id": job_id,
                        "status": status,
                        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                        "device": settings.device,
                    }
                )
            )

    @app.exception_handler(InferenceError)
    async def handle_error(_: Request, exc: InferenceError):
        return JSONResponse(status_code=exc.status_code, content=exc.as_dict())

    @app.get("/ready")
    def ready():
        return runtime.readiness()

    @app.get("/live")
    def live():
        return {"alive": True}

    @app.post("/v1/embeddings")
    async def embeddings(request: Request):
        provided = request.headers.get("x-inference-key", "")
        if not compare_digest(provided.encode(), settings.internal_key.get_secret_value().encode()):
            raise InferenceError("unauthorized", "Internal service authentication required", 401)
        for header in ("x-job-id", "x-tenant-id"):
            try:
                UUID(request.headers.get(header, ""))
            except (ValueError, AttributeError):
                raise InferenceError(
                    "validation_error", "Valid job and tenant context required"
                ) from None
        purpose = request.query_params.get("purpose")
        if purpose not in {"enroll", "identify"}:
            raise InferenceError("validation_error", "Purpose must be enroll or identify")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in _CONTENT_TYPES:
            raise InferenceError("unsupported_audio", "Only WAV and FLAC audio are supported", 415)
        # Reject before reading a body if the model is unavailable or another job owns the GPU.
        with runtime.claim():
            declared = request.headers.get("content-length")
            if declared is not None:
                try:
                    size = int(declared)
                except ValueError:
                    raise InferenceError(
                        "validation_error", "Invalid content length", 400
                    ) from None
                if size < 0 or size > settings.max_upload_bytes:
                    raise InferenceError("audio_limit", "Audio exceeds the upload size limit", 413)
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > settings.max_upload_bytes:
                    raise InferenceError("audio_limit", "Audio exceeds the upload size limit", 413)
                body.extend(chunk)
            return await run_in_threadpool(runtime.extract, bytes(body), purpose)

    return app
