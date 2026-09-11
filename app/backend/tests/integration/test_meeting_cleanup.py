"""Meeting retention uses real database state and owned source files."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.domain.models.meeting import (
    Meeting,
    MeetingChunk,
    MeetingSpeaker,
    MeetingTranscript,
    MeetingUploadPart,
)
from app.domain.models.speaker_identity import Recording, SpeakerJob, SpeakerProfile, SpeakerSample
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.meeting_cleanup import MeetingCleanup
from tests.integration import test_meeting_repository as fixture_module
from tests.integration.test_meeting_repository import (
    MeetingDatabase,
)

pytestmark = pytest.mark.integration
meeting_db = fixture_module.meeting_db
migrated_meeting_database = fixture_module.migrated_meeting_database


def source(storage: MeetingAudioStorage) -> str:
    key = f"{uuid4().hex}.meeting"
    data = b"retention fixture, not real voice"
    storage.append(key, 0, data, hashlib.sha256(data).hexdigest())
    return key


async def test_cleanup_filters_active_sources_before_bounded_selection(
    meeting_db: MeetingDatabase, tmp_path: Path
) -> None:
    storage = MeetingAudioStorage(tmp_path / "meetings")
    settings = get_settings()
    now = datetime.now(UTC)
    active_keys = [source(storage) for _ in range(101)]
    expired_key = source(storage)
    async with meeting_db.sessions() as session, session.begin():
        session.add_all(
            meeting_db.meeting(
                storage_key=key,
                status=["queued", "running", "finalizing"][index % 3],
                source_expires_at=now - timedelta(days=10),
            )
            for index, key in enumerate(active_keys)
        )
        expired = meeting_db.meeting(
            storage_key=expired_key,
            status="succeeded",
            finished_at=now - timedelta(days=8),
            source_expires_at=now - timedelta(days=1),
        )
        session.add(expired)
    assert await MeetingCleanup(meeting_db.sessions, storage, settings).run() >= 1
    assert not storage.path(expired_key).exists()
    assert all(storage.path(key).exists() for key in active_keys)
    async with meeting_db.sessions() as session:
        retained = await session.get(Meeting, expired.meeting_id)
        assert retained.source_removed_at is not None and not retained.is_deleted


async def test_cleanup_expires_abandoned_upload_without_touching_recent_upload(
    meeting_db: MeetingDatabase, tmp_path: Path
) -> None:
    storage = MeetingAudioStorage(tmp_path / "meetings")
    now = datetime.now(UTC)
    expired_key, recent_key = source(storage), source(storage)
    async with meeting_db.sessions() as session, session.begin():
        expired = meeting_db.meeting(
            storage_key=expired_key, upload_expires_at=now - timedelta(seconds=1)
        )
        recent = meeting_db.meeting(storage_key=recent_key)
        session.add_all([expired, recent])
    cleanup = MeetingCleanup(meeting_db.sessions, storage, get_settings())
    assert await cleanup.run() == 1
    assert not storage.path(expired_key).exists() and storage.path(recent_key).exists()
    async with meeting_db.sessions() as session:
        row = await session.get(Meeting, expired.meeting_id)
        assert row.status == "failed" and row.error_code == "upload_expired"
        assert row.finished_at is not None and row.source_removed_at is not None
    assert await cleanup.run() == 0


async def test_cleanup_scrubs_expired_results_and_keeps_independent_profile_sample(
    meeting_db: MeetingDatabase, tmp_path: Path
) -> None:
    storage = MeetingAudioStorage(tmp_path / "meetings")
    now = datetime.now(UTC)
    key = source(storage)
    sample_path = tmp_path / "retained-profile.audio"
    sample_path.write_bytes(b"separate clean enrollment sample")
    vector = [1.0] + [0.0] * 191
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting(
            storage_key=key,
            status="succeeded",
            finished_at=now - timedelta(days=31),
            source_expires_at=now - timedelta(days=24),
        )
        recording = Recording(
            tenant_id=meeting.tenant_id,
            storage_key=uuid4().hex,
            sha256="b" * 64,
            size_bytes=100,
            format="WAV",
            duration_seconds=25,
            expires_at=now - timedelta(days=1),
            idempotency_expires_at=now,
        )
        profile = SpeakerProfile(
            tenant_id=meeting.tenant_id,
            name="Persistent Person",
            sample_count=1,
            model_id="fixture",
            model_revision="v1",
            source_sha256="b" * 64,
            embedding=vector,
        )
        session.add_all([meeting, recording, profile])
        await session.flush()
        job = SpeakerJob(
            tenant_id=meeting.tenant_id,
            recording_id=recording.recording_id,
            purpose="enroll",
            requested_name="Persistent Person",
            status="succeeded",
            model_id="fixture",
            model_revision="v1",
            fingerprint="b" * 64,
        )
        session.add(job)
        await session.flush()
        sample = SpeakerSample(
            tenant_id=meeting.tenant_id,
            speaker_profile_id=profile.speaker_profile_id,
            recording_id=recording.recording_id,
            speaker_job_id=job.speaker_job_id,
            embedding=vector,
            model_id="fixture",
            model_revision="v1",
            source_sha256="b" * 64,
            speech_seconds=25,
            windows_count=5,
        )
        common = {"tenant_id": meeting.tenant_id, "meeting_id": meeting.meeting_id}
        speaker = MeetingSpeaker(
            **common,
            ordinal=0,
            display_name="Persistent Person",
            profile_id=profile.speaker_profile_id,
            enrollment_job_id=job.speaker_job_id,
            decision="enrolled",
            embedding=vector,
            model_id="fixture",
            model_revision="v1",
            source_sha256="b" * 64,
            clean_ranges=[[0, 400000]],
        )
        session.add_all([sample, speaker])
        await session.flush()
        session.add(
            MeetingTranscript(
                **common,
                ordinal=0,
                start=0,
                end=1,
                text="Private transcript",
                meeting_speaker_id=speaker.meeting_speaker_id,
            )
        )
        session.add(
            MeetingChunk(
                **common,
                index=0,
                context_start=0,
                core_start=0,
                core_end=1,
                context_end=1,
                result={"private": "payload"},
            )
        )
        session.add(MeetingUploadPart(**common, index=0, size_bytes=100, sha256="c" * 64))
    cleanup = MeetingCleanup(meeting_db.sessions, storage, get_settings())
    assert await cleanup.run() == 1
    assert not storage.path(key).exists() and sample_path.exists()
    async with meeting_db.sessions() as session:
        row = await session.get(Meeting, meeting.meeting_id)
        assert row.is_deleted and row.title == "" and row.idempotency_key is None
        track = await session.get(MeetingSpeaker, speaker.meeting_speaker_id)
        assert track.is_deleted and track.display_name is None and track.embedding is None
        assert (
            track.clean_ranges == []
            and track.profile_id is None
            and track.enrollment_job_id is None
        )
        transcript = await session.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.meeting_id)
        )
        chunk = await session.scalar(
            select(MeetingChunk).where(MeetingChunk.meeting_id == meeting.meeting_id)
        )
        assert transcript.text == "" and transcript.is_deleted
        assert chunk.result == {} and chunk.is_deleted
        assert not (await session.get(SpeakerProfile, profile.speaker_profile_id)).is_deleted
        assert (
            await session.get(SpeakerProfile, profile.speaker_profile_id)
        ).name == "Persistent Person"
        assert not (await session.get(SpeakerSample, sample.speaker_sample_id)).is_deleted
        assert (await session.get(Recording, recording.recording_id)).file_removed_at is None
    assert await cleanup.run() == 0


async def test_cleanup_rechecks_state_after_candidate_selection(
    meeting_db: MeetingDatabase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.infrastructure.repositories.meeting_cleanup_repository import MeetingCleanupRepository

    storage = MeetingAudioStorage(tmp_path / "meetings")
    key = source(storage)
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting(
            storage_key=key,
            status="uploading",
            upload_expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        session.add(meeting)
    original = MeetingCleanupRepository.candidates

    async def candidates_after_completion(
        self: MeetingCleanupRepository, now: datetime, cutoff: datetime
    ) -> list[tuple[int, int]]:
        candidates = await original(self, now, cutoff)
        async with meeting_db.sessions() as session, session.begin():
            row = await session.get(Meeting, meeting.meeting_id)
            row.status = "queued"
        return candidates

    monkeypatch.setattr(MeetingCleanupRepository, "candidates", candidates_after_completion)
    assert await MeetingCleanup(meeting_db.sessions, storage, get_settings()).run() == 0
    assert storage.path(key).exists()


async def test_deleted_meeting_is_scrubbed_without_waiting_thirty_days(
    meeting_db: MeetingDatabase, tmp_path: Path
) -> None:
    storage = MeetingAudioStorage(tmp_path / "meetings")
    now = datetime.now(UTC)
    key = source(storage)
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting(
            storage_key=key,
            status="cancelled",
            is_deleted=True,
            deleted_at=now,
            deleted_by=meeting_db.user.user_id,
            finished_at=now,
            source_expires_at=now,
        )
        session.add(meeting)
        await session.flush()
        session.add(
            MeetingTranscript(
                tenant_id=meeting.tenant_id,
                meeting_id=meeting.meeting_id,
                ordinal=0,
                start=0,
                end=1,
                text="Deleted private text",
            )
        )
    cleanup = MeetingCleanup(meeting_db.sessions, storage, get_settings())
    assert await cleanup.run() == 1
    async with meeting_db.sessions() as session:
        row = await session.get(Meeting, meeting.meeting_id)
        assert row.title == "" and row.idempotency_key is None
        assert row.deleted_by == meeting_db.user.user_id
        transcript = await session.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.meeting_id)
        )
        assert transcript.text == "" and transcript.is_deleted
    assert not storage.path(key).exists()
    assert await cleanup.run() == 0


async def test_cleanup_handles_missing_file_and_concurrent_retry_once(
    meeting_db: MeetingDatabase, tmp_path: Path
) -> None:
    storage = MeetingAudioStorage(tmp_path / "meetings")
    now = datetime.now(UTC)
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting(
            storage_key=f"{uuid4().hex}.meeting",
            status="succeeded",
            finished_at=now - timedelta(days=8),
            source_expires_at=now - timedelta(days=1),
        )
        session.add(meeting)
    cleanup = MeetingCleanup(meeting_db.sessions, storage, get_settings())
    outcomes = await asyncio.gather(cleanup.run(), cleanup.run())
    assert sum(outcomes) == 1
    async with meeting_db.sessions() as session:
        assert (await session.get(Meeting, meeting.meeting_id)).source_removed_at is not None


async def test_cleanup_storage_failure_rolls_back_metadata_for_retry(
    meeting_db: MeetingDatabase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = MeetingAudioStorage(tmp_path / "meetings")
    now = datetime.now(UTC)
    key = source(storage)
    async with meeting_db.sessions() as session, session.begin():
        meeting = meeting_db.meeting(
            storage_key=key,
            status="succeeded",
            finished_at=now - timedelta(days=8),
            source_expires_at=now - timedelta(days=1),
        )
        session.add(meeting)

    def unavailable(self: MeetingAudioStorage, key: str) -> None:
        raise OSError("Simulated storage failure")

    with monkeypatch.context() as patch:
        patch.setattr(MeetingAudioStorage, "remove", unavailable)
        with pytest.raises(OSError, match="Simulated storage failure"):
            await MeetingCleanup(meeting_db.sessions, storage, get_settings()).run()
    async with meeting_db.sessions() as session:
        assert (await session.get(Meeting, meeting.meeting_id)).source_removed_at is None
    assert storage.path(key).exists()
    assert await MeetingCleanup(meeting_db.sessions, storage, get_settings()).run() == 1
    assert not storage.path(key).exists()
