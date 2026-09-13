"""Authenticated upload, result and naming endpoints for meetings."""

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import CurrentContext, require_permission
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.domain.meeting import UPLOAD_PART_BYTES
from app.infrastructure.correction_receipts import CorrectionReceiptSigner
from app.infrastructure.meeting_audio import PREVIEW_MAX_BYTES, MeetingAudioStorage
from app.infrastructure.ollama_correction import OllamaCorrectionAdapter
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.infrastructure.repositories.transcript_revision_repository import (
    TranscriptRevisionRepository,
)
from app.schemas.meeting import (
    MeetingCreate,
    MeetingPage,
    MeetingResponse,
    MeetingSpeakerPage,
    MeetingSpeakerRename,
    MeetingSpeakerResponse,
    MeetingTranscriptPage,
    MeetingUploadManifest,
)
from app.schemas.speaker_identity import ErrorResponse
from app.schemas.transcript_correction import TranscriptCorrectionPreview
from app.schemas.transcript_suggestions import (
    ReviewModelList,
    SavedTranscriptCorrection,
    TranscriptCorrectionSave,
    TranscriptCorrectionSelection,
    TranscriptCorrectionSuggestion,
)
from app.services.meeting_service import MeetingService
from app.services.speaker_ports import SpeakerError
from app.services.transcript_correction import TranscriptCorrectionService
from app.services.transcript_suggestions import TranscriptSuggestionService

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
    responses={
        code: {"model": ErrorResponse}
        for code in [400, 401, 403, 404, 409, 410, 413, 415, 422, 503]
    },
)


def get_meeting_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MeetingService:
    return MeetingService(
        MeetingRepository(session),
        MeetingAudioStorage(settings.audio_storage_path / "meetings"),
        settings,
    )


Service = Annotated[MeetingService, Depends(get_meeting_service)]


async def get_transcript_correction_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[TranscriptCorrectionService]:
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
        yield TranscriptCorrectionService(
            MeetingRepository(session), OllamaCorrectionAdapter(settings, client)
        )


CorrectionService = Annotated[
    TranscriptCorrectionService, Depends(get_transcript_correction_service)
]


async def get_transcript_suggestion_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[TranscriptSuggestionService]:
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
        yield TranscriptSuggestionService(
            MeetingRepository(session),
            TranscriptRevisionRepository(session),
            OllamaCorrectionAdapter(settings, client),
            CorrectionReceiptSigner(settings),
        )


SuggestionService = Annotated[
    TranscriptSuggestionService, Depends(get_transcript_suggestion_service)
]
IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[\x21-\x7e]+$")
]
Offset = Annotated[int, Query(ge=0, le=1000000)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post(
    "",
    status_code=201,
    response_model=MeetingResponse,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
)
async def create_meeting(
    body: MeetingCreate, context: CurrentContext, service: Service, idempotency_key: IdempotencyKey
) -> MeetingResponse:
    return await service.create(context, idempotency_key, body)


@router.get(
    "",
    response_model=MeetingPage,
    dependencies=[Depends(require_permission("meeting_analysis:read"))],
)
async def list_meetings(
    context: CurrentContext, service: Service, offset: Offset = 0, limit: Limit = 20
) -> MeetingPage:
    return await service.list(context, offset, limit)


@router.get(
    "/review-models",
    operation_id="meeting_review_models",
    response_model=ReviewModelList,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    dependencies=[
        Depends(require_permission("meeting_analysis:read")),
        Depends(require_permission("meeting_analysis:run")),
    ],
)
async def list_review_models(
    context: CurrentContext, service: SuggestionService, response: Response
) -> ReviewModelList:
    result = await service.models(context)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get(
    "/{public_id}",
    response_model=MeetingResponse,
    dependencies=[Depends(require_permission("meeting_analysis:read"))],
)
async def get_meeting(
    public_id: UUID, context: CurrentContext, service: Service
) -> MeetingResponse:
    return await service.get(context, str(public_id))


@router.get(
    "/{public_id}/upload-parts",
    response_model=MeetingUploadManifest,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
)
async def upload_manifest(
    public_id: UUID, context: CurrentContext, service: Service
) -> MeetingUploadManifest:
    return await service.manifest(context, str(public_id))


@router.put(
    "/{public_id}/upload-parts/{index}",
    response_model=MeetingUploadManifest,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload_part(
    public_id: UUID,
    index: Annotated[int, Path(ge=0, le=511)],
    request: Request,
    context: CurrentContext,
    service: Service,
    sha256: Annotated[str, Header(alias="X-Chunk-SHA256", pattern=r"^[a-f0-9]{64}$")],
) -> MeetingUploadManifest:
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "application/octet-stream"
    ):
        raise SpeakerError("unsupported_audio", 415)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > UPLOAD_PART_BYTES:
            raise SpeakerError("audio_limit", 413)
        data.extend(chunk)
    return await service.append(context, str(public_id), index, bytes(data), sha256)


@router.post(
    "/{public_id}/complete",
    status_code=202,
    response_model=MeetingResponse,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
)
async def complete_upload(
    public_id: UUID, context: CurrentContext, service: Service
) -> MeetingResponse:
    return await service.complete(context, str(public_id))


@router.post(
    "/{public_id}/cancel",
    response_model=MeetingResponse,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
)
async def cancel_meeting(
    public_id: UUID, context: CurrentContext, service: Service
) -> MeetingResponse:
    return await service.cancel(context, str(public_id))


@router.post(
    "/{public_id}/retry",
    status_code=202,
    response_model=MeetingResponse,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
)
async def retry_meeting(
    public_id: UUID, context: CurrentContext, service: Service
) -> MeetingResponse:
    return await service.retry(context, str(public_id))


@router.delete(
    "/{public_id}",
    status_code=204,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
)
async def delete_meeting(public_id: UUID, context: CurrentContext, service: Service) -> Response:
    await service.delete(context, str(public_id))
    return Response(status_code=204)


@router.get(
    "/{public_id}/speakers",
    response_model=MeetingSpeakerPage,
    dependencies=[Depends(require_permission("meeting_analysis:read"))],
)
async def list_speakers(
    public_id: UUID,
    context: CurrentContext,
    service: Service,
    offset: Offset = 0,
    limit: Limit = 20,
) -> MeetingSpeakerPage:
    return await service.speakers(context, str(public_id), offset, limit)


@router.patch(
    "/{public_id}/speakers/{speaker_public_id}",
    response_model=MeetingSpeakerResponse,
    dependencies=[Depends(require_permission("meeting_analysis:run"))],
)
async def rename_speaker(
    public_id: UUID,
    speaker_public_id: UUID,
    body: MeetingSpeakerRename,
    context: CurrentContext,
    service: Service,
) -> MeetingSpeakerResponse:
    return await service.rename(context, str(public_id), str(speaker_public_id), body)


@router.get(
    "/{public_id}/transcript",
    response_model=MeetingTranscriptPage,
    dependencies=[Depends(require_permission("meeting_analysis:read"))],
)
async def get_transcript(
    public_id: UUID,
    context: CurrentContext,
    service: Service,
    offset: Offset = 0,
    limit: Limit = 50,
) -> MeetingTranscriptPage:
    return await service.transcript(context, str(public_id), offset, limit)


@router.post(
    "/{public_id}/transcript/{transcript_id}/correction-preview",
    operation_id="meeting_transcript_correction_preview",
    response_model=TranscriptCorrectionPreview,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    dependencies=[
        Depends(require_permission("meeting_analysis:read")),
        Depends(require_permission("meeting_analysis:run")),
    ],
)
async def preview_transcript_correction(
    public_id: UUID,
    transcript_id: UUID,
    context: CurrentContext,
    service: CorrectionService,
    response: Response,
) -> TranscriptCorrectionPreview:
    result = await service.preview(context, str(public_id), str(transcript_id))
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/{public_id}/transcript/{transcript_id}/correction-suggestion",
    operation_id="meeting_transcript_correction_suggestion",
    response_model=TranscriptCorrectionSuggestion,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    dependencies=[
        Depends(require_permission("meeting_analysis:read")),
        Depends(require_permission("meeting_analysis:run")),
    ],
)
async def suggest_transcript_correction(
    public_id: UUID,
    transcript_id: UUID,
    body: TranscriptCorrectionSelection,
    context: CurrentContext,
    service: SuggestionService,
    response: Response,
) -> TranscriptCorrectionSuggestion:
    result = await service.suggest(context, str(public_id), str(transcript_id), body)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/{public_id}/transcript/{transcript_id}/corrections",
    operation_id="meeting_transcript_correction_save",
    response_model=SavedTranscriptCorrection,
    dependencies=[
        Depends(require_permission("meeting_analysis:read")),
        Depends(require_permission("meeting_analysis:run")),
    ],
)
async def save_transcript_correction(
    public_id: UUID,
    transcript_id: UUID,
    body: TranscriptCorrectionSave,
    context: CurrentContext,
    service: SuggestionService,
    response: Response,
) -> SavedTranscriptCorrection:
    result = await service.save(context, str(public_id), str(transcript_id), body.save_token)
    response.headers["Cache-Control"] = "no-store"
    return result


class AudioPreviewRoute(APIRoute):
    """Keep the preview range error code without changing other route validation."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError as exc:
                if any(
                    error["loc"][:2]
                    in {
                        ("query", "start_seconds"),
                        ("query", "end_seconds"),
                    }
                    for error in exc.errors()
                ):
                    raise SpeakerError("invalid_audio_range", 422) from exc
                raise

        return handler


async def get_audio_preview(
    public_id: UUID,
    context: CurrentContext,
    service: Service,
    start_seconds: Annotated[float, Query(ge=0, allow_inf_nan=False)],
    end_seconds: Annotated[float, Query(gt=0, allow_inf_nan=False)],
) -> Response:
    data = await service.audio_preview(context, str(public_id), start_seconds, end_seconds)
    return Response(
        content=data,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


router.add_api_route(
    "/{public_id}/audio-preview",
    get_audio_preview,
    methods=["GET"],
    operation_id="meeting_audio_preview",
    response_class=Response,
    responses={
        200: {
            "description": "At most 30 seconds of source audio as mono PCM16 WAV.",
            "content": {
                "audio/wav": {
                    "schema": {"type": "string", "format": "binary", "maxLength": PREVIEW_MAX_BYTES}
                }
            },
        }
    },
    dependencies=[Depends(require_permission("meeting_analysis:read"))],
    route_class_override=AudioPreviewRoute,
)
