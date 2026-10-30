"""Meeting-end reconciliation rebuilds one speaker per voice from durable chunk results."""

import math

import pytest
from sqlalchemy import func, select

from app.domain.models.meeting import Meeting, MeetingChunk, MeetingSpeaker, MeetingTranscript
from app.services.meeting_ports import MeetingChunkResult
from tests.integration import test_meeting_repository as database_fixtures
from tests.integration import test_meeting_workflow as workflow_fixtures
from tests.integration.test_meeting_worker import Provider, queued, worker
from tests.integration.test_meeting_workflow import MeetingHarness

meeting_db = database_fixtures.meeting_db
migrated_meeting_database = database_fixtures.migrated_meeting_database
meeting_harness = workflow_fixtures.meeting_harness
pytestmark = pytest.mark.integration


def voice(angle: float) -> list[float]:
    return [math.cos(angle), math.sin(angle)] + [0.0] * 254


# One person (A, X, Y) and a similar colleague (C) who talks over A in the first chunk. Each later
# chunk resembles both candidates too closely for the live margin rule, which keeps opening speakers.
A, C, X, Y = voice(0.0), voice(0.7), voice(0.28), voice(0.3)


class ChunkProvider(Provider):
    def __init__(self, plan: list[list[list[float]]]):
        super().__init__()
        self.plan = plan

    async def analyze(
        self, audio: bytes, *, job_public_id, tenant_public_id, language, max_speakers, num_speakers
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
        seconds = payload["input_seconds"]
        vectors = self.plan[len(self.calls) - 1]
        template = payload["tracks"][0]
        # Later chunks start after the shared context, so the live rule cannot reconnect by source.
        offset = 5.2 if len(self.calls) > 1 else 0.0
        step = (seconds - offset) / len(vectors)
        # Neighbouring tracks overlap by one second so one chunk proves two different voices.
        spans = [
            (offset + number * step, min(seconds, offset + (number + 1) * step + 1))
            for number in range(len(vectors))
        ]
        labels = [f"local-{number}" for number in range(len(vectors))]
        payload["turns"] = [
            {"start": start, "end": end, "speaker": label}
            for (start, end), label in zip(spans, labels, strict=True)
        ]
        payload["exclusive_turns"] = payload["turns"]
        middles = [(start + end) / 2 for start, end in spans]
        payload["words"] = [
            {"start": at - 0.1, "end": at + 0.1, "word": f" word{number}", "probability": 0.9}
            for number, at in enumerate(middles)
        ]
        payload["segments"] = [
            {"start": at - 0.1, "end": at + 0.1, "text": f"word{number}"}
            for number, at in enumerate(middles)
        ]
        payload["tracks"] = [
            {
                **template,
                "speaker": label,
                "status": "inconsistent_audio",
                "embedding": None,
                "validated_ranges": [],
                "validated_seconds": 0,
                "min_pair_similarity": 0.4,
                "tracking": {
                    "embedding": vector,
                    "model_id": "pyannote/speaker-diarization-community-1",
                    "model_revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
                    "component": "embedding",
                    "dimensions": 256,
                },
            }
            for label, vector in zip(labels, vectors, strict=True)
        ]
        return MeetingChunkResult.model_validate(payload)


def covered(turns: list[dict]) -> float:
    total, reach = 0.0, 0.0
    for turn in sorted(turns, key=lambda item: item["start_seconds"]):
        total += max(0.0, turn["end_seconds"] - max(reach, turn["start_seconds"]))
        reach = max(reach, turn["end_seconds"])
    return total


async def live_rows(harness: MeetingHarness, public_id: str) -> list[MeetingSpeaker]:
    async with harness.sessions() as session:
        return list(
            await session.scalars(
                select(MeetingSpeaker)
                .join(Meeting, Meeting.meeting_id == MeetingSpeaker.meeting_id)
                .where(Meeting.public_id == public_id, MeetingSpeaker.is_deleted.is_(False))
                .order_by(MeetingSpeaker.ordinal)
            )
        )


async def run_chunks(harness: MeetingHarness, provider: ChunkProvider) -> str:
    public_id = await queued(harness)
    for _ in provider.plan:
        assert await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "finalizing"
    return public_id


async def finish(harness: MeetingHarness, provider: ChunkProvider, public_id: str) -> None:
    for _ in range(12):
        if (await harness.client.get(f"/meetings/{public_id}")).json()["status"] == "succeeded":
            return
        assert await worker(harness, provider).process_once()
    raise AssertionError("meeting did not finish")


async def test_duplicates_opened_during_chunks_become_one_speaker_at_meeting_end(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, ChunkProvider([[A, C], [X], [Y]])
    public_id = await run_chunks(harness, provider)
    assert len(await live_rows(harness, public_id)) == 4, "the live margin rule splits this voice"

    await finish(harness, provider, public_id)

    rows = await live_rows(harness, public_id)
    assert [row.ordinal for row in rows] == [0, 1]
    assert [row.reason for row in rows] == ["inconsistent_audio", "inconsistent_audio"]
    assert all(len(row.tracking_embedding) == 256 for row in rows)
    speakers = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()
    assert speakers["total"] == 2
    identifiers = {row["public_id"] for row in speakers["items"]}
    turns = (await harness.client.get(f"/meetings/{public_id}/speaker-turns?limit=100")).json()
    assert {turn["speaker_public_id"] for turn in turns["items"]} == identifiers
    lines = (await harness.client.get(f"/meetings/{public_id}/transcript?limit=100")).json()
    assert lines["provisional"] is False
    assert [line["text"].strip() for line in lines["items"]] == [
        "word0",
        "word1",
        "word0",
        "word0",
    ]
    assert {line["speaker_ordinal"] for line in lines["items"]} == {0, 1}
    assert [line["speaker_ordinal"] for line in lines["items"]] == [0, 1, 0, 0]


async def test_covered_source_time_is_unchanged_by_rebuilding(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, ChunkProvider([[A, C], [X], [Y]])
    public_id = await run_chunks(harness, provider)
    before = await harness.client.get(f"/meetings/{public_id}/speaker-turns?limit=100")
    speech_before = sum(
        end - start
        for row in await live_rows(harness, public_id)
        for start, end in row.props["speech_ranges"]
    )
    await finish(harness, provider, public_id)
    after = await harness.client.get(f"/meetings/{public_id}/speaker-turns?limit=100")
    assert covered(after.json()["items"]) == pytest.approx(covered(before.json()["items"]))
    rows = await live_rows(harness, public_id)
    assert (
        sum(end - start for row in rows for start, end in row.props["speech_ranges"])
        == speech_before
    )


async def test_retired_rows_stay_for_audit_and_rebuild_applies_once(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, ChunkProvider([[A, C], [X], [Y]])
    public_id = await run_chunks(harness, provider)
    await finish(harness, provider, public_id)
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        assert meeting.props["reconciliation_version"] == "meeting-track-reconciliation-v1"
        all_rows = await session.scalar(
            select(func.count())
            .select_from(MeetingSpeaker)
            .where(MeetingSpeaker.meeting_id == meeting.meeting_id)
        )
        retired = list(
            await session.scalars(
                select(MeetingSpeaker).where(
                    MeetingSpeaker.meeting_id == meeting.meeting_id,
                    MeetingSpeaker.is_deleted.is_(True),
                )
            )
        )
        retired_lines = await session.scalar(
            select(func.count())
            .select_from(MeetingTranscript)
            .where(
                MeetingTranscript.meeting_id == meeting.meeting_id,
                MeetingTranscript.is_deleted.is_(True),
            )
        )
        chunks = await session.scalar(
            select(func.count())
            .select_from(MeetingChunk)
            .where(MeetingChunk.meeting_id == meeting.meeting_id)
        )
    assert all_rows == 4 and len(retired) == 2
    assert all(row.deleted_at is not None and row.deleted_by is not None for row in retired)
    assert retired_lines == 4
    assert chunks == 3


async def test_different_voices_are_not_merged_and_ambiguity_does_not_leak_from_chunks(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    # Similarity 0.5: the live rule marks this speaker ambiguous, the final clusters are clear.
    far = voice(math.acos(0.5))
    harness, provider = meeting_harness, ChunkProvider([[A], [far], [A]])
    public_id = await run_chunks(harness, provider)
    await finish(harness, provider, public_id)
    rows = await live_rows(harness, public_id)
    assert [row.ordinal for row in rows] == [0, 1]
    assert all(not row.props["reconciliation_ambiguous"] for row in rows)


async def test_meeting_without_tracking_vectors_keeps_its_live_result(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, Provider()
    public_id = await queued(harness)
    for _ in range(3):
        assert await worker(harness, provider).process_once()
    before = [row.public_id for row in await live_rows(harness, public_id)]
    for _ in range(4):
        await worker(harness, provider).process_once()
    assert [row.public_id for row in await live_rows(harness, public_id)] == before
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        assert meeting.status == "succeeded"
        assert meeting.props["reconciliation_version"] == "meeting-track-reconciliation-v1"


async def test_invalid_stored_chunk_fails_the_meeting_and_leaves_every_row_untouched(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, ChunkProvider([[A, C], [X], [Y]])
    public_id = await run_chunks(harness, provider)
    async with harness.sessions() as session, session.begin():
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        chunk = await session.scalar(
            select(MeetingChunk).where(
                MeetingChunk.meeting_id == meeting.meeting_id, MeetingChunk.index == 1
            )
        )
        chunk.result = {**chunk.result, "provider": {"input_seconds": -1}}
    before = [(row.public_id, row.speech_seconds) for row in await live_rows(harness, public_id)]
    assert await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "failed" and state["error_code"] == "model_mismatch"
    assert [(r.public_id, r.speech_seconds) for r in await live_rows(harness, public_id)] == before


async def test_speakers_cannot_be_renamed_until_the_result_is_final(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, ChunkProvider([[A, C], [X], [Y]])
    public_id = await run_chunks(harness, provider)
    speaker = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"][0]
    body = {"name": "Early name", "version": speaker["version"]}
    path = f"/meetings/{public_id}/speakers/{speaker['public_id']}"
    rejected = await harness.client.patch(path, json=body)
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "meeting_not_ready"
    await finish(harness, provider, public_id)
    speaker = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"][0]
    renamed = await harness.client.patch(
        f"/meetings/{public_id}/speakers/{speaker['public_id']}",
        json={"name": "Final name", "version": speaker["version"]},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["display_name"] == "Final name"


async def test_other_meetings_are_not_touched(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, ChunkProvider([[A, C], [X], [Y]])
    first = await run_chunks(harness, provider)
    await finish(harness, provider, first)
    kept = [row.public_id for row in await live_rows(harness, first)]
    other_provider = ChunkProvider([[A, C], [X], [Y]])
    other = await run_chunks(harness, other_provider)
    assert len(await live_rows(harness, other)) == 4
    await finish(harness, other_provider, other)
    assert len(await live_rows(harness, other)) == 2
    assert [row.public_id for row in await live_rows(harness, first)] == kept
