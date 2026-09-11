"""Tenant-qualified PostgreSQL persistence and exact vector ranking."""

from datetime import UTC, datetime

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_context import RequestContext
from app.domain.models.speaker_identity import (
    Recording,
    SpeakerJob,
    SpeakerProfile,
    SpeakerSample,
)
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.domain.speaker_identity import (
    MEETING_MODEL_ID,
    MEETING_MODEL_REVISION,
    MEETING_PREPROCESSING_VERSION,
    MODEL_ID,
    MODEL_REVISION,
)
from app.services.speaker_ports import SpeakerError


class SpeakerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def actor(self, context: RequestContext) -> tuple[int, int]:
        tenant = await self.session.scalar(
            select(Tenant.tenant_id).where(
                Tenant.public_id == str(context.tenant_id),
                Tenant.is_deleted.is_(False),
                Tenant.is_active.is_(True),
            )
        )
        user = await self.session.scalar(
            select(User.user_id).where(
                User.public_id == str(context.subject),
                User.is_deleted.is_(False),
                User.is_active.is_(True),
            )
        )
        if tenant is None or user is None:
            raise SpeakerError("not_found", 404)
        return tenant, user

    async def lock_tenant(self, tenant_id: int) -> None:
        # Serialize mutations and centroid decisions within one tenant, including absent rows.
        await self.session.execute(select(func.pg_advisory_xact_lock(tenant_id)))

    async def recording(
        self, tenant_id: int, public_id: str, *, active: bool = True
    ) -> Recording | None:
        query = select(Recording).where(
            Recording.tenant_id == tenant_id, Recording.public_id == public_id
        )
        if active:
            query = query.where(Recording.is_deleted.is_(False))
        return (await self.session.scalars(query)).one_or_none()

    async def recording_by_key(self, tenant_id: int, key: str) -> Recording | None:
        return (
            await self.session.scalars(
                select(Recording).where(
                    Recording.tenant_id == tenant_id, Recording.idempotency_key == key
                )
            )
        ).one_or_none()

    async def recording_by_storage_key(self, tenant_id: int, storage_key: str) -> Recording | None:
        """Check committed ownership even after retry keys expire or soft deletion occurs."""
        return (
            await self.session.scalars(
                select(Recording).where(
                    Recording.tenant_id == tenant_id,
                    Recording.storage_key == storage_key,
                )
            )
        ).one_or_none()

    async def recordings_by_ids(self, tenant_id: int, recording_ids: set[int]) -> list[Recording]:
        return list(
            await self.session.scalars(
                select(Recording).where(
                    Recording.tenant_id == tenant_id,
                    Recording.recording_id.in_(recording_ids),
                    Recording.is_deleted.is_(False),
                )
            )
        )

    async def profile(
        self, tenant_id: int, public_id: str, *, active: bool = True
    ) -> SpeakerProfile | None:
        query = select(SpeakerProfile).where(
            SpeakerProfile.tenant_id == tenant_id, SpeakerProfile.public_id == public_id
        )
        if active:
            query = query.where(SpeakerProfile.is_deleted.is_(False))
        return (await self.session.scalars(query)).one_or_none()

    async def profile_by_id(self, tenant_id: int, profile_id: int) -> SpeakerProfile | None:
        return (
            await self.session.scalars(
                select(SpeakerProfile).where(
                    SpeakerProfile.tenant_id == tenant_id,
                    SpeakerProfile.speaker_profile_id == profile_id,
                    SpeakerProfile.is_deleted.is_(False),
                )
            )
        ).one_or_none()

    async def profiles(
        self, tenant_id: int, offset: int, limit: int
    ) -> tuple[list[SpeakerProfile], int]:
        filters = (
            SpeakerProfile.tenant_id == tenant_id,
            SpeakerProfile.is_deleted.is_(False),
        )
        total = await self.session.scalar(
            select(func.count()).select_from(SpeakerProfile).where(*filters)
        )
        rows = await self.session.scalars(
            select(SpeakerProfile)
            .where(*filters)
            .order_by(
                SpeakerProfile.created_at.desc(),
                SpeakerProfile.speaker_profile_id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(rows), int(total or 0)

    async def ranked(
        self, tenant_id: int, vector: list[float]
    ) -> list[tuple[SpeakerProfile, float]]:
        distance = SpeakerProfile.embedding.cosine_distance(vector)
        rows = await self.session.execute(
            select(SpeakerProfile, distance.label("distance"))
            .where(
                SpeakerProfile.tenant_id == tenant_id,
                SpeakerProfile.is_deleted.is_(False),
                SpeakerProfile.model_id == MODEL_ID,
                SpeakerProfile.model_revision == MODEL_REVISION,
            )
            .order_by(distance, SpeakerProfile.public_id)
            .limit(2)
        )
        return [(profile, max(-1.0, min(1.0, 1.0 - float(value)))) for profile, value in rows]

    async def ranked_meeting(
        self, tenant_id: int, vector: list[float]
    ) -> list[tuple[SpeakerProfile, float]]:
        distance = SpeakerProfile.meeting_embedding.cosine_distance(vector)
        rows = await self.session.execute(
            select(SpeakerProfile, distance.label("distance"))
            .join(
                Recording,
                and_(
                    Recording.tenant_id == SpeakerProfile.tenant_id,
                    Recording.recording_id == SpeakerProfile.meeting_recording_id,
                ),
            )
            .where(
                SpeakerProfile.tenant_id == tenant_id,
                SpeakerProfile.is_deleted.is_(False),
                SpeakerProfile.meeting_embedding.is_not(None),
                SpeakerProfile.meeting_model_id == MEETING_MODEL_ID,
                SpeakerProfile.meeting_model_revision == MEETING_MODEL_REVISION,
                SpeakerProfile.meeting_preprocessing_version == MEETING_PREPROCESSING_VERSION,
                Recording.is_deleted.is_(False),
                Recording.file_removed_at.is_(None),
                Recording.sha256 == SpeakerProfile.meeting_source_sha256,
            )
            .order_by(distance, SpeakerProfile.public_id)
            .limit(2)
        )
        return [(profile, max(-1.0, min(1.0, 1.0 - float(value)))) for profile, value in rows]

    async def samples(self, tenant_id: int, profile_id: int) -> list[SpeakerSample]:
        rows = await self.session.scalars(
            select(SpeakerSample)
            .where(
                SpeakerSample.tenant_id == tenant_id,
                SpeakerSample.speaker_profile_id == profile_id,
                SpeakerSample.is_deleted.is_(False),
            )
            .order_by(SpeakerSample.speaker_sample_id)
        )
        return list(rows)

    async def job(self, tenant_id: int, public_id: str) -> tuple[SpeakerJob, Recording] | None:
        row = (
            await self.session.execute(
                select(SpeakerJob, Recording)
                .join(
                    Recording,
                    and_(
                        Recording.tenant_id == SpeakerJob.tenant_id,
                        Recording.recording_id == SpeakerJob.recording_id,
                    ),
                )
                .where(
                    SpeakerJob.tenant_id == tenant_id,
                    SpeakerJob.public_id == public_id,
                    SpeakerJob.is_deleted.is_(False),
                )
            )
        ).first()
        return (row[0], row[1]) if row else None

    async def job_by_key(
        self, tenant_id: int, purpose: str, key: str
    ) -> tuple[SpeakerJob, Recording] | None:
        row = (
            await self.session.execute(
                select(SpeakerJob, Recording)
                .join(
                    Recording,
                    and_(
                        Recording.tenant_id == SpeakerJob.tenant_id,
                        Recording.recording_id == SpeakerJob.recording_id,
                    ),
                )
                .where(
                    SpeakerJob.tenant_id == tenant_id,
                    SpeakerJob.purpose == purpose,
                    SpeakerJob.idempotency_key == key,
                    SpeakerJob.is_deleted.is_(False),
                )
            )
        ).first()
        return (row[0], row[1]) if row else None

    async def jobs(
        self, tenant_id: int, offset: int, limit: int
    ) -> tuple[list[tuple[SpeakerJob, Recording]], int]:
        filters = (SpeakerJob.tenant_id == tenant_id, SpeakerJob.is_deleted.is_(False))
        total = await self.session.scalar(
            select(func.count()).select_from(SpeakerJob).where(*filters)
        )
        rows = await self.session.execute(
            select(SpeakerJob, Recording)
            .join(
                Recording,
                and_(
                    Recording.tenant_id == SpeakerJob.tenant_id,
                    Recording.recording_id == SpeakerJob.recording_id,
                ),
            )
            .where(*filters)
            .order_by(SpeakerJob.created_at.desc(), SpeakerJob.speaker_job_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [(row[0], row[1]) for row in rows], int(total or 0)

    async def recording_in_use(self, tenant_id: int, recording_id: int) -> bool:
        sample = await self.session.scalar(
            select(SpeakerSample.speaker_sample_id)
            .where(
                SpeakerSample.tenant_id == tenant_id,
                SpeakerSample.recording_id == recording_id,
                SpeakerSample.is_deleted.is_(False),
            )
            .limit(1)
        )
        job = await self.session.scalar(
            select(SpeakerJob.speaker_job_id)
            .where(
                SpeakerJob.tenant_id == tenant_id,
                SpeakerJob.recording_id == recording_id,
                SpeakerJob.status.in_(["queued", "running"]),
                SpeakerJob.is_deleted.is_(False),
            )
            .limit(1)
        )
        return sample is not None or job is not None

    async def claim(self, now: datetime) -> SpeakerJob | None:
        return (
            await self.session.scalars(
                select(SpeakerJob)
                .where(
                    SpeakerJob.is_deleted.is_(False),
                    or_(
                        SpeakerJob.status == "queued",
                        and_(
                            SpeakerJob.status == "running",
                            SpeakerJob.lease_expires_at <= now,
                        ),
                    ),
                )
                .order_by(SpeakerJob.created_at, SpeakerJob.speaker_job_id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
        ).one_or_none()

    async def fenced_job(self, job_id: int, token: int, now: datetime) -> SpeakerJob | None:
        return (
            await self.session.scalars(
                select(SpeakerJob)
                .where(
                    SpeakerJob.speaker_job_id == job_id,
                    SpeakerJob.claim_token == token,
                    SpeakerJob.status == "running",
                    SpeakerJob.lease_expires_at > now,
                    SpeakerJob.is_deleted.is_(False),
                )
                .with_for_update()
            )
        ).one_or_none()

    async def source_for_job(self, job: SpeakerJob) -> tuple[Recording, str] | None:
        row = (
            await self.session.execute(
                select(Recording, Tenant.public_id)
                .join(Tenant, Tenant.tenant_id == Recording.tenant_id)
                .where(
                    Recording.recording_id == job.recording_id,
                    Recording.tenant_id == job.tenant_id,
                    Recording.is_deleted.is_(False),
                    Tenant.is_deleted.is_(False),
                    Tenant.is_active.is_(True),
                )
            )
        ).first()
        return (row[0], row[1]) if row else None

    async def expired_recordings(self, now: datetime, limit: int = 100) -> list[Recording]:
        active_sample = (
            select(SpeakerSample.speaker_sample_id)
            .where(
                SpeakerSample.tenant_id == Recording.tenant_id,
                SpeakerSample.recording_id == Recording.recording_id,
                SpeakerSample.is_deleted.is_(False),
            )
            .exists()
        )
        active_job = (
            select(SpeakerJob.speaker_job_id)
            .where(
                SpeakerJob.tenant_id == Recording.tenant_id,
                SpeakerJob.recording_id == Recording.recording_id,
                SpeakerJob.is_deleted.is_(False),
                SpeakerJob.status.in_(["queued", "running"]),
            )
            .exists()
        )
        rows = await self.session.scalars(
            select(Recording)
            .where(
                Recording.expires_at <= now,
                Recording.file_removed_at.is_(None),
                ~active_sample,
                ~active_job,
            )
            .order_by(Recording.expires_at)
            .limit(limit)
        )
        return list(rows)

    async def expire_job_results(self, cutoff: datetime) -> int:
        result = await self.session.execute(
            update(SpeakerJob)
            .where(
                SpeakerJob.finished_at <= cutoff,
                SpeakerJob.status.in_(["succeeded", "failed"]),
                SpeakerJob.is_deleted.is_(False),
            )
            .values(
                is_deleted=True,
                deleted_at=datetime.now(UTC),
                result=None,
                error_code=None,
                idempotency_key=None,
                requested_name=case((SpeakerJob.requested_name.is_not(None), ""), else_=None),
            )
        )
        return int(getattr(result, "rowcount", 0))

    async def release_expired_upload_keys(self, now: datetime) -> None:
        await self.session.execute(
            update(Recording)
            .where(Recording.idempotency_expires_at <= now)
            .values(idempotency_key=None)
        )

    async def known_storage_keys(self) -> set[str]:
        return set(await self.session.scalars(select(Recording.storage_key)))
