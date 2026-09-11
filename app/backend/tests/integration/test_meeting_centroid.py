"""Source resultants survive real PostgreSQL vector storage and worker checkpoints."""

import math

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.domain.models.meeting import Meeting, MeetingChunk, MeetingSpeaker
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.services.meeting_chunks import MeetingChunkPersistence
from app.services.meeting_ports import MeetingChunkResult
from app.services.speaker_ports import SpeakerError
from tests.integration import test_meeting_repository as database_fixtures
from tests.integration import test_meeting_workflow as workflow_fixtures
from tests.integration.test_meeting_repository import MeetingDatabase
from tests.integration.test_meeting_tracking import TRACKING_MODEL, TRACKING_REVISION
from tests.integration.test_meeting_worker import Provider, queued, result, worker
from tests.integration.test_meeting_workflow import MeetingHarness

meeting_db = database_fixtures.meeting_db
migrated_meeting_database = database_fixtures.migrated_meeting_database
meeting_harness = workflow_fixtures.meeting_harness
pytestmark = pytest.mark.integration


def vector(angle, dimensions):
    radians = math.radians(angle)
    return [math.cos(radians), math.sin(radians)] + [0.0] * (dimensions - 2)


def observed(seconds, angle):
    payload = result(seconds).model_dump(mode="json")
    payload["tracks"][0]["embedding"] = vector(angle, 192)
    payload["tracks"][0]["tracking"] = {
        "embedding": vector(angle, 256),
        "model_id": TRACKING_MODEL,
        "model_revision": TRACKING_REVISION,
        "component": "embedding",
        "dimensions": 256,
    }
    return MeetingChunkResult.model_validate(payload)


async def persist(db, meeting_id, index, angle, *, embedding=True):
    async with db.sessions() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        response = observed(10, angle)
        if not embedding:
            payload = response.model_dump(mode="json")
            payload["tracks"][0].update(
                status="inconsistent_audio",
                embedding=None,
                validated_ranges=[],
                validated_seconds=0.0,
            )
            response = MeetingChunkResult.model_validate(payload)
        await MeetingChunkPersistence(Settings()).persist(
            MeetingRepository(session),
            meeting,
            (index, index * 10, index * 10, (index + 1) * 10, (index + 1) * 10),
            response,
        )


async def create_meeting(db: MeetingDatabase, seconds=30):
    async with db.sessions() as session, session.begin():
        meeting = db.meeting(duration_seconds=seconds, sample_rate=16000, source_sha256="a" * 64)
        session.add(meeting)
        await session.flush()
        return meeting.meeting_id


@pytest.mark.parametrize("angles", [(0, 35, 70), (70, 35, 0)])
async def test_reload_between_source_chunks_keeps_true_centroid(meeting_db, angles):
    db = meeting_db
    meeting_id = await create_meeting(db)
    for index, angle in enumerate(angles):
        await persist(db, meeting_id, index, angle)
    async with db.sessions() as session:
        rows = list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
        )
        assert len(rows) == 1
        row = rows[0]
        for column, key, dimensions in [
            (row.embedding, "embedding_resultant", 192),
            (row.tracking_embedding, "tracking_resultant", 256),
        ]:
            assert list(column) == pytest.approx(vector(35, dimensions), abs=2e-7)
            state = row.props[key]
            assert state["version"] == 1 and state["origin"] == "source_resultant"
            assert state["weight"] == 30
            assert state["norm"] == pytest.approx(
                10 * (1 + 2 * math.cos(math.radians(35))), rel=2e-7
            )
        assert row.speech_seconds == row.props["tracking_seconds"] == 30


async def test_legacy_state_is_seeded_once_on_new_owned_speech(meeting_db):
    db, angles = meeting_db, (0, 35, 70)
    meeting_id = await create_meeting(db)
    await persist(db, meeting_id, 0, angles[0])
    async with db.sessions() as session, session.begin():
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        row.props = {
            key: value for key, value in row.props.items() if not key.endswith("_resultant")
        }
    for index in (1, 2):
        await persist(db, meeting_id, index, angles[index])
    async with db.sessions() as session:
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        for key in ("embedding_resultant", "tracking_resultant"):
            assert row.props[key]["origin"] == "legacy_centroid_seed"
            assert row.props[key]["weight"] == 30


async def test_population_without_vectors_never_uses_the_other_population_weight(meeting_db):
    db = meeting_db
    meeting_id = await create_meeting(db)
    await persist(db, meeting_id, 0, 0, embedding=False)
    await persist(db, meeting_id, 1, 35)
    await persist(db, meeting_id, 2, 70, embedding=False)
    async with db.sessions() as session:
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        assert row.speech_seconds == row.props["embedding_resultant"]["weight"] == 10
        assert row.props["embedding_resultant"]["norm"] == 10
        assert row.props["embedding_resultant"]["origin"] == "source_resultant"
        assert row.props["tracking_seconds"] == row.props["tracking_resultant"]["weight"] == 30
        assert list(row.embedding) == pytest.approx(vector(35, 192), abs=2e-7)


async def test_context_only_revisit_does_not_change_vectors_or_resultant_state(meeting_db):
    db = meeting_db
    meeting_id = await create_meeting(db, 20)
    await persist(db, meeting_id, 0, 0)
    async with db.sessions() as session:
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        before = (list(row.embedding), list(row.tracking_embedding), row.props)
    response = observed(10, 20).model_copy(update={"input_seconds": 20.0})
    async with db.sessions() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        await MeetingChunkPersistence(Settings()).persist(
            MeetingRepository(session),
            meeting,
            (1, 0, 10, 20, 20),
            response,
        )
    async with db.sessions() as session:
        rows = list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
        )
        assert len(rows) == 1
        assert (list(rows[0].embedding), list(rows[0].tracking_embedding), rows[0].props) == before


@pytest.mark.parametrize("key", ["embedding_resultant", "tracking_resultant"])
@pytest.mark.parametrize(
    "malformed",
    [
        None,
        {"version": 2},
        {
            "version": 1,
            "weight": 11,
            "norm": 10,
            "origin": "source_resultant",
        },
    ],
)
async def test_invalid_present_state_rolls_back_the_whole_chunk(meeting_db, key, malformed):
    db = meeting_db
    meeting_id = await create_meeting(db)
    await persist(db, meeting_id, 0, 0)
    async with db.sessions() as session, session.begin():
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        row.props = {**row.props, key: malformed}
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await persist(db, meeting_id, 1, 35)
    async with db.sessions() as session:
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        assert row.speech_seconds == row.props["tracking_seconds"] == 10
        assert list(row.embedding) == vector(0, 192)
        assert list(row.tracking_embedding) == vector(0, 256)
        assert row.props[key] == malformed
        chunks = list(
            await session.scalars(select(MeetingChunk).where(MeetingChunk.meeting_id == meeting_id))
        )
        assert len(chunks) == 1


class AngledProvider(Provider):
    async def analyze(
        self, audio, *, job_public_id, tenant_public_id, language, max_speakers, num_speakers
    ):
        sample = await super().analyze(
            audio,
            job_public_id=job_public_id,
            tenant_public_id=tenant_public_id,
            language=language,
            max_speakers=max_speakers,
            num_speakers=num_speakers,
        )
        return observed(sample.input_seconds, (0, 35, 70)[len(self.calls) - 1])


async def test_actual_worker_counts_owned_core_once_across_restart_and_context(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
):
    harness, provider = meeting_harness, AngledProvider()
    public_id = await queued(harness)
    for _ in range(3):
        assert await worker(harness, provider).process_once()
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting.meeting_id)
        )
        expected = [
            sum(
                weight * vector(angle, 192)[index]
                for angle, weight in [(0, 300), (35, 300), (70, 1)]
            )
            for index in range(192)
        ]
        norm = math.sqrt(sum(value * value for value in expected))
        assert list(row.embedding) == pytest.approx([value / norm for value in expected], abs=2e-7)
        for key in ("embedding_resultant", "tracking_resultant"):
            assert row.props[key]["weight"] == 601
            assert row.props[key]["norm"] == pytest.approx(norm, rel=2e-7)
        assert row.speech_seconds == row.props["tracking_seconds"] == 601
