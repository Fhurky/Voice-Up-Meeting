"""Authenticated upload, result and naming endpoints for meetings."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import CurrentContext, require_permission
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.domain.meeting import UPLOAD_PART_BYTES
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.repositories.meeting_repository import MeetingRepository
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
from app.services.meeting_service import MeetingService
from app.services.speaker_ports import SpeakerError

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
