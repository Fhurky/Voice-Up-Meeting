"""Meeting persistence boundaries against migrated disposable PostgreSQL."""

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.request_context import RequestContext
from app.domain.models.meeting import (
    Meeting,
    MeetingChunk,
    MeetingSpeaker,
    MeetingTranscript,
    MeetingUploadPart,
)
from app.domain.models.permission import Permission
from app.domain.models.speaker_identity import SpeakerProfile
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.infrastructure.repositories.meeting_repository import MeetingRepository

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def migrated_meeting_database(postgres_database_url: str) -> Iterator[None]:
    del postgres_database_url
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")
    command.check(config)
    yield


@dataclass
class MeetingDatabase:
    sessions: async_sessionmaker[AsyncSession]
    tenant: Tenant
    other: Tenant
    user: User

    def meeting(self, **changes: object) -> Meeting:
        values: dict[str, object] = {
            "tenant_id": self.tenant.tenant_id,
            "title": "Meeting fixture",
            "format": "WAV",
            "size_bytes": 1024,
            "storage_key": uuid4().hex,
            "idempotency_key": uuid4().hex,
            "fingerprint": "a" * 64,
            "upload_expires_at": datetime.now(UTC) + timedelta(hours=1),
            "source_expires_at": datetime.now(UTC) + timedelta(days=7),
        }
        values.update(changes)
        return Meeting(**values)


@pytest.fixture
async def meeting_db(
    migrated_meeting_database: None, postgres_database_url: str
) -> AsyncIterator[MeetingDatabase]:
    engine = create_async_engine(postgres_database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with sessions() as session, session.begin():
        suffix = uuid4().hex
        tenant = Tenant(code=f"meeting-{suffix}", name="Meeting fixture")
        other = Tenant(code=f"meeting-other-{suffix}", name="Other fixture")
        session.add_all([tenant, other])
        await session.flush()
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=f"meeting-{suffix}",
            email=f"{suffix}@example.invalid",
            display_name="Meeting fixture",
            password_hash="disabled-test-credential",
        )
        session.add(user)
        await session.flush()
    try:
        yield MeetingDatabase(sessions, tenant, other, user)
    finally:
        async with sessions() as session, session.begin():
            await session.execute(
                update(Meeting)
                .where(
                    Meeting.tenant_id.in_([tenant.tenant_id, other.tenant_id]),
                )
                .values(
                    status="cancelled",
                    claim_token=Meeting.claim_token + 1,
                    lease_expires_at=None,
                    finished_at=datetime.now(UTC),
                    source_removed_at=datetime.now(UTC),
                    title="",
                    idempotency_key=None,
                )
            )
        await engine.dispose()


async def test_meeting_query_tenant_retry_and_soft_delete(
    meeting_db: MeetingDatabase,
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        active = meeting_db.meeting()
        deleted = meeting_db.meeting(is_deleted=True, deleted_at=datetime.now(UTC))
        other = meeting_db.meeting(tenant_id=meeting_db.other.tenant_id)
        session.add_all([active, deleted, other])
        await session.flush()
        repo = MeetingRepository(session)
        context = RequestContext(
            tenant_id=UUID(meeting_db.tenant.public_id),
            subject=UUID(meeting_db.user.public_id),
        )
        assert await repo.actor(context) == (
            meeting_db.tenant.tenant_id,
            meeting_db.user.user_id,
        )
        await repo.lock_tenant(meeting_db.tenant.tenant_id)
        assert await repo.meeting(active.tenant_id, active.public_id) is active
        assert await repo.meeting(active.tenant_id, other.public_id) is None
        assert await repo.meeting(active.tenant_id, deleted.public_id) is None
        assert await repo.meeting(active.tenant_id, deleted.public_id, active=False) is deleted
        assert await repo.by_key(active.tenant_id, active.idempotency_key) is active
        # Deleted keys remain reserved until retention explicitly releases them.
        assert await repo.by_key(active.tenant_id, deleted.idempotency_key) is deleted
        rows, total = await repo.list_meetings(active.tenant_id, 0, 1)
        assert rows == [active] and total == 1
        assert await repo.tenant_public_id(active.tenant_id) == meeting_db.tenant.public_id


async def test_meeting_retry_key_is_physically_unique_per_tenant(
    meeting_db: MeetingDatabase,
) -> None:
    key = uuid4().hex
    async with meeting_db.sessions() as session, session.begin():
        session.add(meeting_db.meeting(idempotency_key=key))
        session.add(meeting_db.meeting(idempotency_key=key, tenant_id=meeting_db.other.tenant_id))
    async with meeting_db.sessions() as session, session.begin():
        session.add(meeting_db.meeting(idempotency_key=key))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.parametrize(
    "changes",
    [
        {"size_bytes": 0},
        {"uploaded_bytes": 1025},
        {"participant_count": 0},
        {"participant_count": 1001},
        {"expected_speakers": 0},
        {"participant_count": 5, "expected_speakers": 6},
        {"duration_seconds": -1},
        {"status": "imaginary"},
        {"format": "MP3"},
        {"language": "xx"},
    ],
)
async def test_meeting_database_rejects_invalid_bounds(
    meeting_db: MeetingDatabase, changes: dict[str, object]
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        session.add(meeting_db.meeting(**changes))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.parametrize("kind", ["upload", "chunk", "speaker", "transcript"])
async def test_meeting_children_cannot_reference_another_tenant(
    meeting_db: MeetingDatabase, kind: str
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting()
        session.add(meeting)
        await session.flush()
        common = {
            "tenant_id": meeting_db.other.tenant_id,
            "meeting_id": meeting.meeting_id,
        }
        if kind == "upload":
            child = MeetingUploadPart(**common, index=0, size_bytes=10, sha256="b" * 64)
        elif kind == "chunk":
            child = MeetingChunk(
                **common,
                index=0,
                context_start=0,
                core_start=0,
                core_end=1,
                context_end=1,
                result={"turns": []},
            )
        elif kind == "speaker":
            child = MeetingSpeaker(**common, ordinal=0)
        else:
            child = MeetingTranscript(**common, ordinal=0, start=0, end=1, text="Hello")
        session.add(child)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_transcript_speaker_must_belong_to_same_meeting(
    meeting_db: MeetingDatabase,
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        first, second = meeting_db.meeting(), meeting_db.meeting()
        session.add_all([first, second])
        await session.flush()
        speaker = MeetingSpeaker(tenant_id=first.tenant_id, meeting_id=first.meeting_id, ordinal=0)
        session.add(speaker)
        await session.flush()
        session.add(
            MeetingTranscript(
                tenant_id=second.tenant_id,
                meeting_id=second.meeting_id,
                meeting_speaker_id=speaker.meeting_speaker_id,
                ordinal=0,
                start=0,
                end=1,
                text="Hello",
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_meeting_profile_reference_cannot_cross_tenant(
    meeting_db: MeetingDatabase,
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting()
        profile = SpeakerProfile(
            tenant_id=meeting_db.other.tenant_id,
            name="Other person",
            sample_count=1,
            model_id="fixture",
            model_revision="revision",
            source_sha256="b" * 64,
            embedding=[1.0] + [0.0] * 191,
        )
        session.add_all([meeting, profile])
        await session.flush()
        session.add(
            MeetingSpeaker(
                tenant_id=meeting.tenant_id,
                meeting_id=meeting.meeting_id,
                ordinal=0,
                profile_id=profile.speaker_profile_id,
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_meeting_pages_parts_chunks_and_retention_budget(
    meeting_db: MeetingDatabase,
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting()
        removed = meeting_db.meeting(source_removed_at=datetime.now(UTC), status="cancelled")
        session.add_all([meeting, removed])
        await session.flush()
        common = {"tenant_id": meeting.tenant_id, "meeting_id": meeting.meeting_id}
        speakers = [MeetingSpeaker(**common, ordinal=i) for i in [2, 0, 1]]
        session.add_all(speakers)
        session.add_all(
            MeetingUploadPart(**common, index=i, size_bytes=10, sha256="b" * 64) for i in [1, 0]
        )
        session.add_all(
            MeetingChunk(
                **common,
                index=i,
                context_start=i,
                core_start=i,
                core_end=i + 1,
                context_end=i + 1,
                result={"turns": []},
            )
            for i in [1, 0]
        )
        session.add_all(
            MeetingTranscript(**common, ordinal=i, start=i, end=i + 1, text=f"Text {i}")
            for i in [1, 0]
        )
        await session.flush()
        repo = MeetingRepository(session)
        tenant_id, meeting_id = meeting.tenant_id, meeting.meeting_id
        assert [p.index for p in await repo.upload_parts(tenant_id, meeting_id)] == [
            0,
            1,
        ]
        assert (await repo.upload_part(tenant_id, meeting_id, 1)).size_bytes == 10
        assert [c.index for c in await repo.chunks(tenant_id, meeting_id)] == [0, 1]
        page, total = await repo.speakers(tenant_id, meeting_id, 1, 1)
        assert [s.ordinal for s in page] == [1] and total == 3
        assert await repo.speaker(tenant_id, meeting_id, speakers[0].public_id) is speakers[0]
        assert (
            await repo.speaker_by_id(tenant_id, meeting_id, speakers[0].meeting_speaker_id)
            is speakers[0]
        )
        texts, total = await repo.transcript(tenant_id, meeting_id, 1, 1)
        assert [t.text for t in texts] == ["Text 1"] and total == 2
        assert await repo.retained_bytes(tenant_id) == 1024
        assert await repo.active_upload_count(tenant_id) == 1
        assert await repo.speakers(meeting_db.other.tenant_id, meeting_id, 0, 10) == (
            [],
            0,
        )


async def test_meeting_claim_skips_locked_and_fences_expired_tokens(
    meeting_db: MeetingDatabase,
) -> None:
    now = datetime.now(UTC)
    async with meeting_db.sessions() as session, session.begin():
        first = meeting_db.meeting(status="queued", created_at=now - timedelta(days=3650))
        second = meeting_db.meeting(
            status="finalizing",
            created_at=now - timedelta(days=3649),
            lease_expires_at=now - timedelta(days=3649),
        )
        session.add_all([first, second])
    async with (
        meeting_db.sessions() as a,
        a.begin(),
        meeting_db.sessions() as b,
        b.begin(),
    ):
        claimed = await MeetingRepository(a).claim(now)
        next_claim = await MeetingRepository(b).claim(now)
        assert claimed.meeting_id == first.meeting_id
        assert next_claim.meeting_id == second.meeting_id
        claimed.status = "running"
        claimed.claim_token = 4
        claimed.lease_expires_at = now + timedelta(minutes=1)
        await a.flush()
        repo = MeetingRepository(a)
        assert await repo.fenced(first.meeting_id, 4, now) is claimed
        assert await repo.fenced(first.meeting_id, 3, now) is None
        assert await repo.fenced(first.meeting_id, 4, now + timedelta(minutes=2)) is None
        claimed.status = "cancelled"
        next_claim.status = "cancelled"


async def test_meeting_permissions_exist_after_migration(
    meeting_db: MeetingDatabase,
) -> None:
    async with meeting_db.sessions() as session:
        rows = await session.scalars(
            select(Permission.code).where(
                Permission.code.in_(["meeting_analysis:read", "meeting_analysis:run"])
            )
        )
        assert set(rows) == {"meeting_analysis:read", "meeting_analysis:run"}


async def test_completed_chunk_yields_to_waiting_meeting(
    meeting_db: MeetingDatabase,
) -> None:
    now = datetime.now(UTC)
    async with meeting_db.sessions() as session, session.begin():
        released = meeting_db.meeting(
            status="running",
            created_at=now - timedelta(days=9000),
            lease_expires_at=now,
            next_chunk_index=1,
        )
        queued = meeting_db.meeting(status="queued", created_at=now - timedelta(days=8000))
        session.add_all([released, queued])
        await session.flush()
        assert (await MeetingRepository(session).claim(now)).meeting_id == queued.meeting_id
        # Keep later queue tests independent in the same disposable database.
        queued.status = "cancelled"
        released.status = "cancelled"


@pytest.mark.parametrize(
    "kind,changes",
    [
        ("upload", {"size_bytes": 4194305}),
        ("upload", {"index": 512}),
        ("chunk", {"context_end": 311}),
        ("chunk", {"core_start": -1}),
        ("chunk", {"status": "running"}),
        ("speaker", {"embedding": [1.0] + [0.0] * 191}),
        ("speaker", {"decision": "known"}),
        ("transcript", {"end": 0}),
    ],
)
async def test_meeting_child_bounds_and_embedding_provenance(
    meeting_db: MeetingDatabase, kind: str, changes: dict[str, object]
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting()
        session.add(meeting)
        await session.flush()
        values: dict[str, object] = {
            "tenant_id": meeting.tenant_id,
            "meeting_id": meeting.meeting_id,
        }
        if kind == "upload":
            values.update(index=0, size_bytes=1, sha256="b" * 64)
            model = MeetingUploadPart
        elif kind == "chunk":
            values.update(
                index=0,
                context_start=0,
                core_start=0,
                core_end=1,
                context_end=1,
                result={},
            )
            model = MeetingChunk
        elif kind == "speaker":
            values.update(ordinal=0)
            model = MeetingSpeaker
        else:
            values.update(ordinal=0, start=0, end=1, text="Hello")
            model = MeetingTranscript
        values.update(changes)
        session.add(model(**values))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_meeting_chunk_accepts_current_maximum_context(
    meeting_db: MeetingDatabase,
) -> None:
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting(duration_seconds=310)
        session.add(meeting)
        await session.flush()
        chunk = MeetingChunk(
            tenant_id=meeting.tenant_id,
            meeting_id=meeting.meeting_id,
            index=0,
            context_start=0,
            core_start=5,
            core_end=305,
            context_end=310,
            result={},
        )
        session.add(chunk)
        await session.flush()
        await session.refresh(chunk)
        assert chunk.context_end - chunk.context_start == 310
