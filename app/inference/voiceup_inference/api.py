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
from .meeting_memory import MAX_MEMORY_JSON_BYTES
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
            if request.url.path
            in {
                "/live",
                "/ready",
                "/meeting-ready",
                "/v1/embeddings",
                "/v1/meeting-chunks",
                "/v1/meeting-memory",
            }
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

    @app.get("/meeting-ready")
    def meeting_ready():
        return runtime.meeting_readiness()

    def authenticate(request: Request) -> None:
        provided = request.headers.get("x-inference-key", "")
        if not compare_digest(
            provided.encode(), settings.internal_key.get_secret_value().encode()
        ):
            raise InferenceError(
                "unauthorized", "Internal service authentication required", 401
            )
        for header in ("x-job-id", "x-tenant-id"):
            try:
                UUID(request.headers.get(header, ""))
            except (ValueError, AttributeError):
                raise InferenceError(
                    "validation_error", "Valid job and tenant context required"
                ) from None

    async def read_audio(request: Request, *, maximum: int | None = None) -> bytes:
        maximum = settings.max_upload_bytes if maximum is None else maximum
        content_type = (
            request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        )
        if content_type not in _CONTENT_TYPES:
            raise InferenceError(
                "unsupported_audio", "Only WAV and FLAC audio are supported", 415
            )
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                size = int(declared)
            except ValueError:
                raise InferenceError(
                    "validation_error", "Invalid content length", 400
                ) from None
            if size < 0 or size > maximum:
                raise InferenceError(
                    "audio_limit", "Audio exceeds the upload size limit", 413
                )
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > maximum:
                raise InferenceError(
                    "audio_limit", "Audio exceeds the upload size limit", 413
                )
            body.extend(chunk)
        return bytes(body)

    @app.post("/v1/embeddings")
    async def embeddings(request: Request):
        authenticate(request)
        purpose = request.query_params.get("purpose")
        if purpose not in {"enroll", "identify"}:
            raise InferenceError(
                "validation_error", "Purpose must be enroll or identify"
            )
        # Reject before reading a body if the model is unavailable or another job owns the GPU.
        with runtime.claim():
            body = await read_audio(request)
            return await run_in_threadpool(runtime.extract, body, purpose)

    @app.post("/v1/meeting-chunks")
    async def meeting_chunks(request: Request):
        authenticate(request)
        language = request.query_params.get("language")
        if language not in {None, "tr", "en"}:
            raise InferenceError(
                "validation_error", "Language must be tr, en, or omitted"
            )
        counts = {}
        for name in ("max_speakers", "num_speakers"):
            raw = request.query_params.get(name)
            if raw is None:
                counts[name] = None
                continue
            if (
                len(raw) > 4
                or not raw.isascii()
                or not raw.isdecimal()
                or not 1 <= int(raw) <= 1000
            ):
                raise InferenceError(
                    "validation_error", "Speaker counts must be integers from 1 to 1000"
                )
            counts[name] = int(raw)
        if (
            counts["max_speakers"] is not None
            and counts["num_speakers"] is not None
            and counts["num_speakers"] > counts["max_speakers"]
        ):
            raise InferenceError(
                "validation_error", "Speaker count must not exceed its upper bound"
            )
        runtime.meeting_readiness()
        with runtime.claim():
            body = await read_audio(request, maximum=120 * 1024 * 1024)
            return await run_in_threadpool(
                runtime.meeting_chunk, body, language, **counts
            )

    @app.post("/v1/meeting-memory")
    async def meeting_memory(request: Request):
        authenticate(request)
        if (
            request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            != "application/json"
        ):
            raise InferenceError(
                "validation_error", "JSON meeting evidence is required", 415
            )
        declared = request.headers.get("content-length")
        if declared is not None and (
            len(declared) > 12
            or not declared.isdecimal()
            or int(declared) > MAX_MEMORY_JSON_BYTES
        ):
            raise InferenceError(
                "audio_limit", "Meeting evidence exceeds its size limit", 413
            )
        runtime.meeting_readiness()
        with runtime.claim():
            body = bytearray()
            async for part in request.stream():
                if len(body) + len(part) > MAX_MEMORY_JSON_BYTES:
                    raise InferenceError(
                        "audio_limit", "Meeting evidence exceeds its size limit", 413
                    )
                body.extend(part)
            try:
                payload = json.loads(body)
            except (ValueError, RecursionError):
                raise InferenceError(
                    "validation_error", "Invalid meeting evidence JSON", 422
                ) from None
            return await run_in_threadpool(runtime.meeting_memory, payload)

    return app
