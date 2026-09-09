"""Bound upload bodies before Starlette spools multipart files to disk."""

import asyncio
from tempfile import SpooledTemporaryFile

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyLimitExceeded(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Upload body limit exceeded")


class AudioUploadLimitMiddleware:
    def __init__(self, app: ASGIApp, *, path: str, maximum: int) -> None:
        self.app = app
        self.path = path
        # A single file plus the multipart framing and ordinary headers.
        self.maximum = maximum + 65536

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != self.path
        ):
            await self.app(scope, receive, send)
            return
        try:
            headers = dict(scope.get("headers", []))
            if b"content-length" in headers and int(headers[b"content-length"]) > self.maximum:
                raise BodyLimitExceeded()
            # Validate the complete bounded body before multipart parsing. Exceptions raised from
            # a receive callback can be converted to a generic 400 by FastAPI/BaseHTTPMiddleware.
            # This spool is always closed, including oversized or disconnected uploads.
            with SpooledTemporaryFile(max_size=1024 * 1024) as body:
                size = 0
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > self.maximum:
                        raise BodyLimitExceeded()
                    await asyncio.to_thread(body.write, chunk)
                    if not message.get("more_body", False):
                        break
                body.seek(0)
                delivered = False

                async def replay() -> Message:
                    nonlocal delivered
                    if delivered:
                        return await receive()
                    chunk = await asyncio.to_thread(body.read, 1024 * 1024)
                    more = body.tell() < size
                    delivered = not more
                    return {"type": "http.request", "body": chunk, "more_body": more}

                await self.app(scope, replay, send)
        except BodyLimitExceeded:
            response = JSONResponse(
                status_code=413,
                content={
                    "detail": {
                        "code": "audio_limit",
                        "message": "The upload exceeds the allowed size.",
                    }
                },
            )
            await response(scope, receive, send)
