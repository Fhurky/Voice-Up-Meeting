"""Worker checkpoints carry unqualified candidate provenance into the distinct memory port."""

import hashlib
import io
import math
from itertools import pairwise

import pytest
import soundfile as sf
from sqlalchemy import select

from app.domain.models.meeting import Meeting, MeetingChunk, MeetingSpeaker
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.meeting_memory import MeetingMemory
from app.services.meeting_ports import MeetingChunkResult
from app.services.meeting_worker import MeetingWorker
from tests.integration import test_meeting_workflow as fixtures
from tests.integration.test_meeting_context_memory import ContextProvider
from tests.integration.test_meeting_tracking import TRACKING_MODEL, TRACKING_REVISION
from tests.integration.test_meeting_worker import Provider
from tests.integration.test_meeting_workflow import MeetingHarness, create

meeting_harness = fixtures.meeting_harness
pytestmark = pytest.mark.integration


class LegacyTrap:
    async def embed(self, audio: bytes, *, purpose, job_public_id, tenant_public_id):
        raise AssertionError("new candidate evidence must never call the legacy embedding port")


class CandidateProvider(Provider):
    def __init__(self, empty: bool = False, no_tracking: bool = False, many: bool = False):
        super().__init__()
        self.empty = empty
        self.no_tracking = no_tracking
        self.many = many

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
        track = payload["tracks"][0]
        if not self.empty:
            track.update(
                status="inconsistent_audio",
                embedding=None,
                validated_ranges=[],
                validated_seconds=0.0,
                min_pair_similarity=0.4,
            )
        track["tracking"] = {
            "embedding": [1.0] + [0.0] * 255,
            "model_id": TRACKING_MODEL,
            "model_revision": TRACKING_REVISION,
            "component": "embedding",
            "dimensions": 256,
        }
        if self.empty:
            track["candidate_contexts"] = []
        elif len(self.calls) == 1:
            track["candidate_contexts"] = [
                {"start": 0.1001, "end": 8.1001, "voiced_ranges": [{"start": 0.2, "end": 8.0}]},
                {"start": 54.0, "end": 62.0, "voiced_ranges": [{"start": 54.1, "end": 61.9}]},
            ]
        else:
            track["candidate_contexts"] = [
                {"start": 0.0, "end": 8.0, "voiced_ranges": [{"start": 0.1, "end": 7.9}]}
            ]
        if self.many:
            track["candidate_contexts"] = [
                {
                    "start": float(start),
                    "end": float(start + 3),
                    "voiced_ranges": [{"start": float(start), "end": float(start + 3)}],
                }
                for start in range(0, math.floor(payload["input_seconds"]) - 2, 3)
            ]
        if self.no_tracking:
            track["tracking"] = None
        return MeetingChunkResult.model_validate(payload)


class MappedVadProvider(Provider):
    def __init__(self, separate: bool = False, empty_vad: bool = False):
        super().__init__()
        self.separate = separate
        self.empty_vad = empty_vad

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
        payload["model_identity"]["diarization"]["recipe"] = "community-vbx-fa015-v1"
        payload["turns"] = [
            {"start": 0.0, "end": 1.8, "speaker": "native-a"},
            {"start": 1.9, "end": 3.8, "speaker": "native-b"},
        ]
        payload["exclusive_turns"] = payload["turns"]
        payload["tracks"] = []
        for index, label in enumerate(["native-a", "native-b"]):
            payload["tracks"].append(
                {
                    "speaker": label,
                    "status": "inconsistent_audio",
                    "embedding": None,
                    "dimensions": 192,
                    "validated_ranges": [],
                    "validated_seconds": 0.0,
                    "used_seconds": 0.0,
                    "windows_count": 0,
                    "min_pair_similarity": None,
                    "preprocessing_version": "vad-windows-v1",
                    "tracking": {
                        "embedding": (
                            [0.0, 1.0] + [0.0] * 254
                            if self.separate and index
                            else [1.0] + [0.0] * 255
                        ),
                        "model_id": TRACKING_MODEL,
                        "model_revision": TRACKING_REVISION,
                        "component": "embedding",
                        "dimensions": 256,
                    },
                    "candidate_contexts": None,
                }
            )
        payload["vad"] = {
            "model_id": "silero-vad",
            "model_version": "6.2.1",
            "model_sha256": "e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720",
            "ranges": (
                [] if self.empty_vad else [{"start": 0.0, "end": 1.8}, {"start": 1.9, "end": 3.8}]
            ),
        }
        return MeetingChunkResult.model_validate(payload)


async def queue(harness: MeetingHarness, rate: int, seconds: int) -> str:
    stream = io.BytesIO()
    sf.write(stream, [0.1] * (seconds * rate), rate, format="WAV", subtype="PCM_16")
    data = stream.getvalue()
    meeting = await create(harness.client, data)
    for index, offset in enumerate(range(0, len(data), 4194304)):
        part = data[offset : offset + 4194304]
        response = await harness.client.put(
            f"/meetings/{meeting['public_id']}/upload-parts/{index}",
            content=part,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Chunk-SHA256": hashlib.sha256(part).hexdigest(),
            },
        )
        assert response.status_code == 200
    assert (
        await harness.client.post(f"/meetings/{meeting['public_id']}/complete")
    ).status_code == 202
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        row.props = {**row.props, "window_core_seconds": 60}
    return meeting["public_id"]


def candidate_worker(
    harness: MeetingHarness, provider: Provider, quality: ContextProvider
) -> MeetingWorker:
    storage = MeetingAudioStorage(harness.settings.audio_storage_path / "meetings")
    memory = MeetingMemory(
        harness.sessions,
        storage,
        AudioStorage(harness.settings),
        LegacyTrap(),
        harness.settings,
        quality,
    )
    return MeetingWorker(harness.sessions, storage, provider, memory, harness.settings)


@pytest.mark.parametrize("rate", [8000, 44100])
async def test_worker_candidates_are_source_bound_core_owned_and_unqualified(
    meeting_harness: MeetingHarness, rate: int
) -> None:
    harness, provider, quality = meeting_harness, CandidateProvider(), ContextProvider()
    quality.status = "inconsistent_audio"
    public_id = await queue(harness, rate, 65)
    worker = candidate_worker(harness, provider, quality)
    assert await worker.process_once()
    assert await worker.process_once()
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting.meeting_id)
        )
        assert track.source_sha256 == meeting.source_sha256
        assert track.props["candidate_version"] == "meeting-natural-context-v1"
        assert [(item["start"], item["end"]) for item in track.props["candidate_contexts"]] == [
            (math.ceil(0.1001 * rate), math.floor(8.1001 * rate)),
            (54 * rate, 60 * rate),
            (60 * rate, 63 * rate),
        ]
        assert track.props["candidate_contexts"][1]["voiced_ranges"] == [
            [math.ceil(54.1 * rate), 60 * rate]
        ]
        assert track.props["candidate_contexts"][2]["voiced_ranges"] == [
            [60 * rate, math.floor(62.9 * rate)]
        ]
        assert track.speech_seconds == 0 and track.clean_ranges == [] and track.profile_id is None
        assert (
            len(
                list(
                    await session.scalars(
                        select(MeetingChunk).where(MeetingChunk.meeting_id == meeting.meeting_id)
                    )
                )
            )
            == 2
        )
    assert quality.calls == 0
    assert await worker.process_once()
    assert quality.calls == 1
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded"
    speakers = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"]
    assert speakers[0]["speech_seconds"] == 0 and speakers[0]["profile_public_id"] is None


async def test_empty_new_candidates_cannot_fall_back_to_legacy_enrollment(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider, quality = meeting_harness, CandidateProvider(empty=True), ContextProvider()
    public_id = await queue(harness, 16000, 24)
    worker = candidate_worker(harness, provider, quality)
    assert await worker.process_once()
    assert await worker.process_once()
    assert quality.calls == 0
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded"
    speakers = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"]
    assert speakers[0]["speech_seconds"] == 0 and speakers[0]["profile_public_id"] is None


async def test_missing_native_tracking_keeps_pending_without_failing_meeting(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider, quality = (
        meeting_harness,
        CandidateProvider(no_tracking=True),
        ContextProvider(),
    )
    public_id = await queue(harness, 8000, 65)
    worker = candidate_worker(harness, provider, quality)
    for _ in range(5):
        await worker.process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded"
    assert quality.calls == 0
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        rows = list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting.meeting_id)
            )
        )
        assert rows and all(row.props["candidate_contexts"] == [] for row in rows)
        assert all(row.speech_seconds == 0 and row.profile_id is None for row in rows)


async def test_long_candidate_checkpoint_manifest_is_bounded(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider, quality = meeting_harness, CandidateProvider(many=True), ContextProvider()
    public_id = await queue(harness, 8000, 900)
    async with harness.sessions() as session, session.begin():
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        meeting.props = {**meeting.props, "window_core_seconds": 300}
    worker = candidate_worker(harness, provider, quality)
    for _ in range(3):
        assert await worker.process_once()
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting.meeting_id)
        )
        contexts = row.props["candidate_contexts"]
        assert len(contexts) == 256
        assert contexts[0]["start"] == 0
        assert all(left["end"] <= right["start"] for left, right in pairwise(contexts))
        assert contexts[-1]["end"] <= 900 * 8000
        assert row.source_sha256 == meeting.source_sha256
        assert row.speech_seconds == 0 and row.clean_ranges == []


@pytest.mark.parametrize(
    "separate,empty_vad,expected", [(False, False, 1), (True, False, 0), (False, True, 0)]
)
@pytest.mark.parametrize("rate", [8000, 44100])
async def test_worker_builds_candidates_only_after_acoustic_mapping(
    meeting_harness: MeetingHarness, separate: bool, empty_vad: bool, expected: int, rate: int
) -> None:
    harness, provider, quality = (
        meeting_harness,
        MappedVadProvider(separate, empty_vad),
        ContextProvider(),
    )
    quality.status = "inconsistent_audio"
    public_id = await queue(harness, rate, 4)
    worker = candidate_worker(harness, provider, quality)
    assert await worker.process_once()
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        rows = list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting.meeting_id)
            )
        )
        assert len(rows) == (2 if separate else 1)
        assert all(
            row.props.get("candidate_version") == "meeting-natural-context-v1" for row in rows
        )
        assert sum(len(row.props.get("candidate_contexts", [])) for row in rows) == expected
        assert all(
            row.source_sha256 == meeting.source_sha256 and row.speech_seconds == 0 for row in rows
        )
        if expected:
            assert rows[0].props["candidate_contexts"] == [
                {
                    "start": 0,
                    "end": math.floor(3.8 * rate),
                    "voiced_ranges": [
                        [0, math.floor(1.8 * rate)],
                        [math.ceil(1.9 * rate), math.floor(3.8 * rate) - math.ceil(rate / 4)],
                    ],
                }
            ]
    for _ in range(2):
        await worker.process_once()
    assert quality.calls == expected
    assert (await harness.client.get(f"/meetings/{public_id}")).json()["status"] == "succeeded"
