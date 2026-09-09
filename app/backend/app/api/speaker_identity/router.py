"""Authenticated, bounded and typed public speaker pilot endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import CurrentContext, require_permission
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.repositories.speaker_repository import SpeakerRepository
from app.schemas.speaker_identity import (
    ErrorResponse,
    RecordingResponse,
    SpeakerJobCreate,
    SpeakerJobPage,
    SpeakerJobResponse,
    SpeakerProfilePage,
    SpeakerProfileRename,
    SpeakerProfileResponse,
)
from app.services.speaker_service import SpeakerService

router = APIRouter(
    tags=["Speaker identity"],
    responses={
        code: {"model": ErrorResponse} for code in [400, 401, 403, 404, 409, 410, 413, 415, 422]
    },
)


def get_speaker_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SpeakerService:
    return SpeakerService(SpeakerRepository(session), AudioStorage(settings), settings)


Service = Annotated[SpeakerService, Depends(get_speaker_service)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[\x21-\x7e]+$"),
]
Offset = Annotated[int, Query(ge=0, le=1000000)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post(
    "/recordings",
    status_code=201,
    response_model=RecordingResponse,
    dependencies=[Depends(require_permission("speaker_analysis:run"))],
)
async def upload_recording(
    file: UploadFile,
    context: CurrentContext,
    service: Service,
    idempotency_key: IdempotencyKey,
) -> RecordingResponse:
    try:
        return await service.upload(context, idempotency_key, file, file.filename)
    finally:
        await file.close()


@router.post(
    "/speaker-jobs",
    status_code=202,
    response_model=SpeakerJobResponse,
    dependencies=[Depends(require_permission("speaker_analysis:run"))],
)
async def create_job(
    body: SpeakerJobCreate,
    context: CurrentContext,
    service: Service,
    idempotency_key: IdempotencyKey,
) -> SpeakerJobResponse:
    return await service.start_job(context, idempotency_key, body)


@router.get(
    "/speaker-jobs",
    response_model=SpeakerJobPage,
    dependencies=[Depends(require_permission("speaker_analysis:read"))],
)
async def list_jobs(
    context: CurrentContext, service: Service, offset: Offset = 0, limit: Limit = 20
) -> SpeakerJobPage:
    return await service.list_jobs(context, offset, limit)


@router.get(
    "/speaker-jobs/{public_id}",
    response_model=SpeakerJobResponse,
    dependencies=[Depends(require_permission("speaker_analysis:read"))],
)
async def get_job(public_id: UUID, context: CurrentContext, service: Service) -> SpeakerJobResponse:
    return await service.get_job(context, str(public_id))


@router.get(
    "/speaker-profiles",
    response_model=SpeakerProfilePage,
    dependencies=[Depends(require_permission("speaker_profiles:read"))],
)
async def list_profiles(
    context: CurrentContext, service: Service, offset: Offset = 0, limit: Limit = 20
) -> SpeakerProfilePage:
    return await service.list_profiles(context, offset, limit)


@router.patch(
    "/speaker-profiles/{public_id}",
    response_model=SpeakerProfileResponse,
    dependencies=[Depends(require_permission("speaker_profiles:write"))],
)
async def rename_profile(
    public_id: UUID,
    body: SpeakerProfileRename,
    context: CurrentContext,
    service: Service,
) -> SpeakerProfileResponse:
    return await service.rename_profile(context, str(public_id), body.name)


@router.delete(
    "/speaker-profiles/{public_id}",
    status_code=204,
    dependencies=[Depends(require_permission("speaker_profiles:write"))],
)
async def delete_profile(public_id: UUID, context: CurrentContext, service: Service) -> Response:
    await service.delete_profile(context, str(public_id))
    return Response(status_code=204)


@router.delete(
    "/recordings/{public_id}",
    status_code=204,
    dependencies=[Depends(require_permission("speaker_analysis:run"))],
)
async def delete_recording(public_id: UUID, context: CurrentContext, service: Service) -> Response:
    await service.delete_recording(context, str(public_id))
    return Response(status_code=204)
