"""PRD 030: one diarization pass over the recording names each voice once for the whole meeting."""

import io
import math

import pytest
import soundfile as sf
from sqlalchemy import select, text

from app.domain.models.meeting import Meeting, MeetingDiarization, MeetingSpeaker
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services import meeting_worker as worker_module
from app.services.meeting_cleanup import MeetingCleanup
from app.services.meeting_ports import MeetingChunkResult, MeetingRecordingResult
from app.services.speaker_ports import SpeakerError
from tests.integration import test_meeting_repository as database_fixtures
from tests.integration import test_meeting_workflow as workflow_fixtures
from tests.integration.test_meeting_worker import Provider, queued, worker
from tests.integration.test_meeting_workflow import MeetingHarness

meeting_db = database_fixtures.meeting_db
migrated_meeting_database = database_fixtures.migrated_meeting_database
meeting_harness = workflow_fixtures.meeting_harness
pytestmark = pytest.mark.integration

TRACKING = {
    "model_id": "pyannote/speaker-diarization-community-1",
    "model_revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
    "component": "embedding",
    "dimensions": 256,
}
IDENTITY = {
    "diarization": {
        "model_id": "pyannote/speaker-diarization-community-1",
        "revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
        "recipe": "community-default-whole-v1",
    },
    "asr": {
        "model_id": "Systran/faster-whisper-large-v3",
        "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
    },
    "embedding": {
        "model_id": "speechbrain/spkrec-ecapa-voxceleb",
        "revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
        "dimensions": 192,
    },
}
# The second model label speaks first, so numbering must follow speech, not label order.
FIRST, SECOND = "SPEAKER_01", "SPEAKER_00"
VOICES = {FIRST: [1.0] + [0.0] * 191, SECOND: [0.0, 1.0] + [0.0] * 190}


class WholeProvider(Provider):
    def __init__(self, device: str = "gpu", error: SpeakerError | None = None):
        super().__init__()
        self.device, self.recording_error = device, error
        self.recordings: list[tuple[int, int, int, int | None]] = []
        self.attributed: list[dict] = []

    async def processor(self) -> dict:
        return {"device": self.device}

    async def diarize_recording(
        self, blocks, *, sample_rate, size_bytes, job_public_id, tenant_public_id, max_speakers
    ) -> MeetingRecordingResult:
        data = b"".join([block async for block in blocks])
        self.recordings.append((sample_rate, size_bytes, len(data), max_speakers))
        if self.recording_error:
            raise self.recording_error
        seconds = math.ceil(size_bytes // 2 * 16000 / sample_rate) / 16000
        turns = [
            {"start": 0.0, "end": 250.0, "speaker": FIRST},
            {"start": 250.0, "end": 450.0, "speaker": SECOND},
            {"start": 450.0, "end": seconds, "speaker": FIRST},
        ]
        return MeetingRecordingResult.model_validate(
            {
                "input_seconds": seconds,
                "sample_rate": 16000,
                "device": "cuda:0",
                "turns": turns,
                "exclusive_turns": turns,
                "speakers": [
                    {"speaker": FIRST, "tracking": {"embedding": [1.0] + [0.0] * 255, **TRACKING}},
                    {
                        "speaker": SECOND,
                        "tracking": {"embedding": [0.0, 1.0] + [0.0] * 254, **TRACKING},
                    },
                ],
                "model_identity": IDENTITY,
            }
        )

    async def analyze_attributed(
        self, audio, turns, *, job_public_id, tenant_public_id, language
    ) -> MeetingChunkResult:
        self.attributed.append(turns)
        with sf.SoundFile(io.BytesIO(audio)) as source:
            seconds = source.frames / source.samplerate
        labels = sorted({row["speaker"] for row in turns["turns"]})
        middles = [((row["start"] + row["end"]) / 2, row["speaker"]) for row in turns["turns"]]
        tracks = []
        for label in labels:
            ranges = [
                {"start": row["start"], "end": row["end"]}
                for row in turns["exclusive_turns"]
                if row["speaker"] == label
            ]
            spoken = sum(row["end"] - row["start"] for row in ranges)
            tracks.append(
                {
                    "speaker": label,
                    "status": "usable",
                    "embedding": VOICES[label],
                    "dimensions": 192,
                    "validated_ranges": ranges,
                    "validated_seconds": spoken,
                    "used_seconds": min(60, spoken),
                    "windows_count": math.ceil(min(60, spoken) / 8),
                    "min_pair_similarity": 1,
                    "preprocessing_version": "vad-windows-v1",
                    "tracking": None,
                }
            )
        return MeetingChunkResult.model_validate(
            {
                "input_seconds": seconds,
                "sample_rate": 16000,
                "device": "cuda:0",
                "turns": turns["turns"],
                "exclusive_turns": turns["exclusive_turns"],
                "segments": [
                    {"start": at - 0.1, "end": at + 0.1, "text": label} for at, label in middles
                ],
                "words": [
                    {"start": at - 0.1, "end": at + 0.1, "word": f" {label}", "probability": 0.9}
                    for at, label in middles
                ],
                "language": "tr",
                "language_probability": 1,
                "tracks": tracks,
                "model_identity": IDENTITY,
            }
        )


async def run(harness: MeetingHarness, provider: Provider, public_id: str) -> dict:
    for _ in range(16):
        state = (await harness.client.get(f"/meetings/{public_id}")).json()
        if state["status"] in {"succeeded", "failed"}:
            return state
        assert await worker(harness, provider).process_once()
    raise AssertionError("meeting did not finish")


async def stored(harness: MeetingHarness, public_id: str):
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        speakers = list(
            await session.scalars(
                select(MeetingSpeaker)
                .where(
                    MeetingSpeaker.meeting_id == meeting.meeting_id,
                    MeetingSpeaker.is_deleted.is_(False),
                )
                .order_by(MeetingSpeaker.ordinal)
            )
        )
        diarization = await session.scalar(
            select(MeetingDiarization).where(MeetingDiarization.meeting_id == meeting.meeting_id)
        )
        return meeting, speakers, diarization


def flow_events(caplog: pytest.LogCaptureFixture) -> list[dict]:
    return [
        record.structured_fields
        for record in caplog.records
        if record.getMessage() == "meeting_diarization"
    ]


async def test_one_pass_names_each_voice_once_for_the_whole_meeting(
    meeting_harness: MeetingHarness,
    migrated_meeting_database: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    harness, provider = meeting_harness, WholeProvider()
    public_id = await queued(harness)
    with caplog.at_level("INFO", logger="app.meeting_worker"):
        assert await worker(harness, provider).process_once()
    [event] = flow_events(caplog)
    assert event["flow"] == "whole" and event["reason"] is None and event["speakers"] == 2
    assert set(event) == {"flow", "reason", "speakers", "duration_seconds"}
    meeting, speakers, diarization = await stored(harness, public_id)
    assert meeting.props["diarization_flow"] == "whole" and meeting.status == "running"
    assert [row.props["diarization_label"] for row in speakers] == [FIRST, SECOND]
    assert all(row.tracking_embedding is not None for row in speakers)
    assert diarization.speaker_count == 2 and diarization.recipe == "community-default-whole-v1"
    assert diarization.source_sha256 == meeting.source_sha256
    # The participant upper bound reaches the single pass; the whole source is streamed once.
    rate, size, received, bound = provider.recordings[0]
    assert (rate, received, bound) == (16000, size, 5) and size == 601 * 16000 * 2

    final = await run(harness, provider, public_id)
    assert final["status"] == "succeeded"
    assert provider.calls == [], "no chunk separates its own speakers"
    assert provider.attributed[0]["turns"] == [
        {"start": 0.0, "end": 250.0, "speaker": FIRST},
        {"start": 250.0, "end": 305.0, "speaker": SECOND},
    ]
    assert provider.attributed[1]["turns"][0] == {"start": 0.0, "end": 155.0, "speaker": SECOND}
    _, speakers, _ = await stored(harness, public_id)
    assert len(speakers) == 2, "chunks may not open new speakers"
    response = await harness.client.get(f"/meetings/{public_id}/speakers?offset=0&limit=20")
    assert [row["ordinal"] for row in response.json()["items"]] == [0, 1]
    lines = (await harness.client.get(f"/meetings/{public_id}/transcript?offset=0&limit=50")).json()
    names = {speaker.public_id: speaker.props["diarization_label"] for speaker in speakers}
    # One word in the middle of each windowed turn: 125 s, 277.5 s, 372.5 s, 525.5 s, 598 s.
    expected = [FIRST, SECOND, SECOND, FIRST, FIRST]
    assert [names[line["speaker_public_id"]] for line in lines["items"]] == expected
    assert [line["text"] for line in lines["items"]] == expected
    turns = (
        await harness.client.get(f"/meetings/{public_id}/speaker-turns?offset=0&limit=50")
    ).json()
    owners = [(names[turn["speaker_public_id"]], turn["start_seconds"]) for turn in turns["items"]]
    assert {owner for owner, _ in owners} == {FIRST, SECOND}


async def test_cpu_keeps_chunks_without_an_extra_worker_cycle(
    meeting_harness: MeetingHarness,
    migrated_meeting_database: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    harness, provider = meeting_harness, WholeProvider(device="cpu")
    public_id = await queued(harness)
    with caplog.at_level("INFO", logger="app.meeting_worker"):
        for _ in range(3):
            assert await worker(harness, provider).process_once()
    assert flow_events(caplog) == [{"flow": "chunked", "reason": "cpu"}]
    meeting, _, diarization = await stored(harness, public_id)
    assert meeting.status == "finalizing" and diarization is None
    assert meeting.props["diarization_flow"] == "chunked"
    assert meeting.props["diarization_fallback"] == "cpu"
    assert provider.recordings == [] and len(provider.calls) == 3


async def test_a_failed_pass_falls_back_to_chunks_and_the_meeting_succeeds(
    meeting_harness: MeetingHarness,
    migrated_meeting_database: None,
) -> None:
    harness = meeting_harness
    provider = WholeProvider(error=SpeakerError("clipped_audio", 422))
    public_id = await queued(harness)
    assert await worker(harness, provider).process_once()
    meeting, speakers, diarization = await stored(harness, public_id)
    assert meeting.status == "running" and speakers == [] and diarization is None
    assert meeting.props["diarization_fallback"] == "clipped_audio"
    assert (await run(harness, provider, public_id))["status"] == "succeeded"
    assert len(provider.calls) == 3 and provider.attributed == []


async def test_an_unavailable_service_is_retried_before_falling_back(
    meeting_harness: MeetingHarness,
    migrated_meeting_database: None,
) -> None:
    harness = meeting_harness
    provider = WholeProvider(error=SpeakerError("inference_unavailable", 503))
    public_id = await queued(harness)
    assert await worker(harness, provider).process_once()
    meeting, _, _ = await stored(harness, public_id)
    assert "diarization_flow" not in meeting.props and meeting.status == "running"
    assert await worker(harness, provider).process_once()
    meeting, _, _ = await stored(harness, public_id)
    assert meeting.props["diarization_fallback"] == "inference_unavailable"
    assert meeting.attempt_count == 0
    assert len(provider.recordings) == 2


async def test_long_recordings_use_chunks(
    meeting_harness: MeetingHarness,
    migrated_meeting_database: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(worker_module, "WHOLE_RECORDING_MAX_SECONDS", 600)
    harness, provider = meeting_harness, WholeProvider()
    public_id = await queued(harness)
    assert await worker(harness, provider).process_once()
    meeting, _, _ = await stored(harness, public_id)
    assert meeting.props["diarization_fallback"] == "duration"
    assert provider.recordings == [] and len(provider.calls) == 1


async def test_deleting_the_meeting_scrubs_the_stored_turns(
    meeting_harness: MeetingHarness,
    migrated_meeting_database: None,
) -> None:
    harness, provider = meeting_harness, WholeProvider()
    public_id = await queued(harness)
    assert (await run(harness, provider, public_id))["status"] == "succeeded"
    assert (await harness.client.delete(f"/meetings/{public_id}")).status_code == 204
    storage = MeetingAudioStorage(harness.settings.audio_storage_path / "meetings")
    assert await MeetingCleanup(harness.sessions, storage, harness.settings).run() >= 1
    _, _, diarization = await stored(harness, public_id)
    assert diarization.is_deleted and diarization.result == {}


async def test_migrated_table_has_the_lifecycle_columns_and_no_public_identity(
    meeting_harness: MeetingHarness,
    migrated_meeting_database: None,
) -> None:
    async with meeting_harness.sessions() as session:
        columns = set(
            await session.scalars(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'meeting_diarization'"
                )
            )
        )
        comment = await session.scalar(
            text("SELECT obj_description('meeting_diarization'::regclass, 'pg_class')")
        )
    assert {
        "props",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "is_deleted",
        "deleted_at",
        "deleted_by",
        "result",
        "recipe",
    } <= columns
    assert "public_id" not in columns and comment
