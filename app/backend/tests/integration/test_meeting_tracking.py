"""Meeting tracking is a separate private vector population, never enrollment evidence."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.models.meeting import MeetingSpeaker
from app.infrastructure.repositories.meeting_cleanup_repository import (
    MeetingCleanupRepository,
)
from app.services.meeting_ports import MeetingChunkResult
from tests.integration import test_meeting_repository as fixtures
from tests.integration import test_meeting_workflow as workflow_fixtures
from tests.integration.test_meeting_repository import MeetingDatabase
from tests.integration.test_meeting_worker import Provider, queued, worker
from tests.integration.test_meeting_workflow import MeetingHarness

meeting_db = fixtures.meeting_db
migrated_meeting_database = fixtures.migrated_meeting_database
meeting_harness = workflow_fixtures.meeting_harness
pytestmark = pytest.mark.integration

TRACKING_MODEL = "pyannote/speaker-diarization-community-1"
TRACKING_REVISION = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"


class TrackingProvider(Provider):
    def __init__(self, different: bool = False):
        super().__init__()
        self.different = different

    async def analyze(
        self,
        audio: bytes,
        *,
        job_public_id,
        tenant_public_id,
        language,
        max_speakers,
        num_speakers,
    ) -> MeetingChunkResult:
        observed = await super().analyze(
            audio,
            job_public_id=job_public_id,
            tenant_public_id=tenant_public_id,
            language=language,
            max_speakers=max_speakers,
            num_speakers=num_speakers,
        )
        payload = observed.model_dump(mode="json")
        current = payload["tracks"][0]
        current.update(
            status="inconsistent_audio",
            embedding=None,
            validated_ranges=[],
            validated_seconds=0,
            min_pair_similarity=0.4,
            tracking={
                "embedding": (
                    [0.0, 1.0] + [0.0] * 254
                    if self.different and len(self.calls) > 1
                    else [1.0] + [0.0] * 255
                ),
                "model_id": TRACKING_MODEL,
                "model_revision": TRACKING_REVISION,
                "component": "embedding",
                "dimensions": 256,
            },
        )
        return MeetingChunkResult.model_validate(payload)


async def test_short_acoustic_tracking_survives_chunks_without_authorizing_voice_memory(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, TrackingProvider()
    public_id = await queued(harness)
    for _ in range(5):
        await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded" and state["observed_speakers"] == 1
    response = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()
    speaker = response["items"][0]
    assert speaker["decision"] == "profile_pending"
    assert speaker["reason"] == "inconsistent_audio"
    assert speaker["profile_public_id"] is None and speaker["speech_seconds"] == 0
    assert all("tracking" not in key and "embedding" not in key for key in speaker)
    async with harness.sessions() as session:
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == speaker["public_id"])
        )
        assert len(row.tracking_embedding) == 256 and row.embedding is None
        assert sum(end - start for start, end in row.props["speech_ranges"]) == 601 * 16000


async def test_different_tracking_voice_does_not_merge_to_meet_the_input_count(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, TrackingProvider(different=True)
    public_id = await queued(harness)
    assert await worker(harness, provider).process_once()
    assert await worker(harness, provider).process_once()
    response = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()
    assert response["total"] == 2
    assert all(row["profile_public_id"] is None for row in response["items"])
    for _ in range(3):
        assert await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded"
    assert state["count_mismatch"] and state["expected_speakers"] == 1


async def test_private_tracking_population_and_retention_are_independent_of_profile_evidence(
    meeting_db: MeetingDatabase,
) -> None:
    db = meeting_db
    async with db.sessions() as session, session.begin():
        meeting = db.meeting()
        session.add(meeting)
        await session.flush()
        speaker = MeetingSpeaker(
            tenant_id=db.tenant.tenant_id,
            meeting_id=meeting.meeting_id,
            ordinal=0,
            tracking_embedding=[1.0] + [0.0] * 255,
            tracking_model_id=TRACKING_MODEL,
            tracking_model_revision=TRACKING_REVISION,
        )
        session.add(speaker)
        await session.flush()
        speaker_id = speaker.meeting_speaker_id
        assert speaker.embedding is None and speaker.profile_id is None
        assert speaker.speech_seconds == 0 and speaker.clean_ranges == []
    async with db.sessions() as session, session.begin():
        speaker = await session.get(MeetingSpeaker, speaker_id)
        assert len(speaker.tracking_embedding) == 256
        meeting = await session.get(type(meeting), meeting.meeting_id)
        await MeetingCleanupRepository(session).scrub_results(meeting, datetime.now(UTC))
    async with db.sessions() as session:
        speaker = await session.get(MeetingSpeaker, speaker_id)
        assert speaker.is_deleted
        assert speaker.tracking_embedding is None
        assert speaker.tracking_model_id is None
        assert speaker.tracking_model_revision is None


@pytest.mark.parametrize("missing", ["tracking_model_id", "tracking_model_revision"])
async def test_tracking_vector_requires_its_own_population_identity(
    meeting_db: MeetingDatabase, missing: str
) -> None:
    db = meeting_db
    async with db.sessions() as session, session.begin():
        meeting = db.meeting()
        session.add(meeting)
        await session.flush()
        meeting_id = meeting.meeting_id
    fields = {
        "tracking_embedding": [1.0] + [0.0] * 255,
        "tracking_model_id": TRACKING_MODEL,
        "tracking_model_revision": TRACKING_REVISION,
    }
    fields[missing] = None
    with pytest.raises(IntegrityError):
        async with db.sessions() as session, session.begin():
            session.add(
                MeetingSpeaker(
                    tenant_id=db.tenant.tenant_id,
                    meeting_id=meeting_id,
                    ordinal=0,
                    **fields,
                )
            )
            await session.flush()
    async with db.sessions() as session:
        assert not list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
        )
