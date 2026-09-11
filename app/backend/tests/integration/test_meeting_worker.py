"""Real persisted chunk ownership, restart fencing, cancellation and finalization."""

import asyncio
import hashlib
import io
import math
from datetime import UTC, datetime, timedelta

import pytest
import soundfile as sf
from sqlalchemy import select

from app.domain.models.meeting import (
    Meeting,
    MeetingChunk,
    MeetingSpeaker,
    MeetingTranscript,
)
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.meeting_memory import MeetingMemory
from app.services.meeting_ports import MeetingChunkResult
from app.services.meeting_worker import MeetingWorker
from app.services.speaker_ports import EmbeddingResult, SpeakerError
from tests.integration import test_meeting_workflow as fixtures
from tests.integration.test_meeting_workflow import MeetingHarness, create, source_bytes

meeting_harness = fixtures.meeting_harness
pytestmark = pytest.mark.integration


class Provider:
    def __init__(self):
        self.calls = []
        self.error = None

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
        self.calls.append((max_speakers, num_speakers))
        if self.error:
            raise self.error
        with sf.SoundFile(io.BytesIO(audio)) as source:
            seconds = source.frames / source.samplerate
        return result(seconds)


def result(seconds: float) -> MeetingChunkResult:
    return MeetingChunkResult.model_validate(
        {
            "input_seconds": seconds,
            "sample_rate": 16000,
            "device": "cuda:0",
            "turns": [{"start": 0, "end": seconds, "speaker": "local-a"}],
            "exclusive_turns": [{"start": 0, "end": seconds, "speaker": "local-a"}],
            "segments": [{"start": 1, "end": 2, "text": "hello"}],
            "words": [{"start": 1, "end": 2, "word": " hello", "probability": 0.9}],
            "language": "en",
            "language_probability": 1,
            "tracks": [
                {
                    "speaker": "local-a",
                    "status": "usable",
                    "embedding": [1.0] + [0.0] * 191,
                    "dimensions": 192,
                    "validated_ranges": [{"start": 0, "end": seconds}],
                    "validated_seconds": seconds,
                    "used_seconds": min(60, seconds),
                    "windows_count": math.ceil(min(60, seconds) / 8),
                    "min_pair_similarity": 1,
                    "preprocessing_version": "vad-windows-v1",
                }
            ],
            "model_identity": {
                "diarization": {
                    "model_id": "pyannote/speaker-diarization-community-1",
                    "revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
                },
                "asr": {
                    "model_id": "Systran/faster-whisper-large-v3",
                    "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
                },
                "embedding": {
                    "model_id": MODEL_ID,
                    "revision": MODEL_REVISION,
                    "dimensions": 192,
                },
            },
        }
    )


class MemoryProvider:
    async def embed(
        self, audio: bytes, *, purpose, job_public_id, tenant_public_id
    ) -> EmbeddingResult:
        with sf.SoundFile(io.BytesIO(audio)) as source:
            seconds = source.frames / source.samplerate
        return EmbeddingResult([1.0] + [0.0] * 191, seconds, 2, MODEL_ID, MODEL_REVISION, "cpu")


def worker(harness: MeetingHarness, provider: Provider) -> MeetingWorker:
    storage = MeetingAudioStorage(harness.settings.audio_storage_path / "meetings")
    memory = MeetingMemory(
        harness.sessions,
        storage,
        AudioStorage(harness.settings),
        MemoryProvider(),
        harness.settings,
    )
    return MeetingWorker(harness.sessions, storage, provider, memory, harness.settings)


async def queued(harness: MeetingHarness, seconds: float = 601) -> str:
    data = source_bytes(seconds)
    meeting = await create(harness.client, data, participant_count=5, expected_speakers=1)
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
    return meeting["public_id"]


@pytest.mark.parametrize(
    ("rate", "provider_start", "provider_end", "source_start", "source_end"),
    [
        (8000, 1601, 400003, 801, 200001),
        (24000, 1603, 400001, 2405, 600001),
        (44100, 1603, 400001, 4419, 1102502),
    ],
)
async def test_validated_evidence_never_expands_beyond_provider_source_bounds(
    meeting_harness: MeetingHarness,
    rate: int,
    provider_start: int,
    provider_end: int,
    source_start: int,
    source_end: int,
) -> None:
    harness = meeting_harness
    audio = io.BytesIO()
    sf.write(audio, [0.1] * (30 * rate), rate, format="WAV")
    data = audio.getvalue()
    meeting = await create(harness.client, data)
    assert (await fixtures.upload(harness.client, meeting, data)).status_code == 200
    assert (
        await harness.client.post(f"/meetings/{meeting['public_id']}/complete")
    ).status_code == 202
    service = worker(harness, Provider())
    claim = await service.claim()
    assert claim is not None
    start, end = provider_start / 16000, provider_end / 16000
    ranges = [{"start": start, "end": end}]
    if rate == 8000:
        # This half-source-frame interval contains no complete source sample.
        ranges.append({"start": 27 + 1 / 16000, "end": 27 + 2 / 16000})
    payload = result(30).model_dump()
    payload["tracks"][0].update(
        validated_ranges=ranges,
        validated_seconds=sum(span["end"] - span["start"] for span in ranges),
        used_seconds=16,
        windows_count=2,
    )
    assert await service.save_chunk(claim, MeetingChunkResult.model_validate(payload))
    async with harness.sessions() as session:
        stored = await session.scalar(
            select(Meeting).where(Meeting.public_id == meeting["public_id"])
        )
        assert stored.sample_rate == rate
        speaker = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == stored.meeting_id)
        )
        assert speaker.clean_ranges == [[source_start, source_end]]
        assert speaker.clean_ranges[0][0] / rate >= start
        assert speaker.clean_ranges[0][1] / rate <= end
        assert speaker.speech_seconds == pytest.approx((source_end - source_start) / rate)


async def test_incremental_chunks_resume_without_duplicate_evidence_or_forced_count(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, Provider()
    public_id = await queued(harness)
    assert await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["completed_chunks"] == 1 and state["processed_seconds"] == 300
    for _ in range(5):
        await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded" and state["processed_seconds"] == 601
    assert state["completed_chunks"] == 3
    assert provider.calls == [(1, None)] * 3
    speakers = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"]
    assert len(speakers) == 1 and speakers[0]["speech_seconds"] == 601
    assert speakers[0]["decision"] == "enrolled"
    assert not await worker(harness, provider).process_once()


async def test_cancel_and_expired_lease_fence_previous_chunk_results(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, Provider()
    public_id = await queued(harness, 30)
    service = worker(harness, provider)
    first = await service.claim()
    assert first is not None
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    second = await service.claim()
    assert second is not None and second.token > first.token
    assert not await service.save_chunk(first, result(30))
    assert (await harness.client.post(f"/meetings/{public_id}/cancel")).status_code == 200
    assert not await service.save_chunk(second, result(30))
    async with harness.sessions() as session:
        for model in (MeetingChunk, MeetingSpeaker, MeetingTranscript):
            assert not list(
                await session.scalars(
                    select(model).where(model.tenant_id == harness.tenant.tenant_id)
                )
            )


async def test_legacy_checkpoint_keeps_original_cores_after_upgrade_and_restart(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, Provider()
    public_id = await queued(harness, 121)
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        assert row.props["window_core_seconds"] == 300
        # Pre-upgrade meetings have no saved policy and used sixty-second cores.
        row.props = {}
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["total_chunks"] == 3
    assert await worker(harness, provider).process_once()
    async with harness.sessions() as session:
        row = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        chunk = await session.scalar(
            select(MeetingChunk).where(MeetingChunk.meeting_id == row.meeting_id)
        )
        assert (
            chunk.index,
            chunk.context_start,
            chunk.core_start,
            chunk.core_end,
            chunk.context_end,
        ) == (0, 0, 0, 60, 65)
    for _ in range(5):
        await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert (
        state["status"] == "succeeded" and state["total_chunks"] == state["completed_chunks"] == 3
    )
    assert state["processed_seconds"] == 121 and provider.calls == [(1, None)] * 3
    speakers = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"]
    assert len(speakers) == 1 and speakers[0]["speech_seconds"] == 121


async def test_failed_chunk_retry_keeps_completed_checkpoint(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, Provider()
    public_id = await queued(harness)
    service = worker(harness, provider)
    assert await service.process_once()
    provider.error = SpeakerError("invalid_audio", 400)
    assert await service.process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "failed" and state["completed_chunks"] == 1
    provider.error = None
    assert (await harness.client.post(f"/meetings/{public_id}/retry")).status_code == 202
    assert await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["completed_chunks"] == 2 and state["processed_seconds"] == 600


async def test_lease_expiring_during_persistence_rolls_back_the_entire_core(
    meeting_harness: MeetingHarness, monkeypatch
) -> None:
    harness, provider = meeting_harness, Provider()
    public_id = await queued(harness, 30)
    service = worker(harness, provider)
    claim = await service.claim()
    assert claim is not None
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        row.lease_expires_at = datetime.now(UTC) + timedelta(seconds=2)
    persist = service.chunks.persist

    async def delayed(repository, meeting, window, payload):
        await persist(repository, meeting, window, payload)
        await asyncio.sleep(2.1)

    monkeypatch.setattr(service.chunks, "persist", delayed)
    with pytest.raises(SpeakerError, match="job_timeout"):
        await service.save_chunk(claim, result(30))
    async with harness.sessions() as session:
        for model in (MeetingChunk, MeetingSpeaker, MeetingTranscript):
            assert not list(
                await session.scalars(
                    select(model).where(model.tenant_id == harness.tenant.tenant_id)
                )
            )
        row = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        assert row.next_chunk_index == 0


async def test_checkpointed_boundary_reconciliation_owns_jittered_words_once(
    meeting_harness: MeetingHarness,
) -> None:
    class JitterProvider(Provider):
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
            payload = await super().analyze(
                audio,
                job_public_id=job_public_id,
                tenant_public_id=tenant_public_id,
                language=language,
                max_speakers=max_speakers,
                num_speakers=num_speakers,
            )
            words = (
                [
                    (298.0, 298.5, " anchor"),
                    (299.7, 300.1, " boundary"),
                    (300.3, 300.7, " after."),
                ]
                if len(self.calls) == 1
                else [
                    (3.0, 3.5, " anchor"),
                    (4.8, 5.2, " boundary"),
                    (5.4, 5.8, " after."),
                ]
            )
            values = payload.model_dump()
            values["words"] = [
                {"start": start, "end": end, "word": text, "probability": 0.9}
                for start, end, text in words
            ]
            return MeetingChunkResult.model_validate(values)

    harness, provider = meeting_harness, JitterProvider()
    public_id = await queued(harness, 330)
    assert await worker(harness, provider).process_once()
    assert (await harness.client.get(f"/meetings/{public_id}/transcript")).json()["items"] == []
    assert await worker(harness, provider).process_once()
    transcript = (await harness.client.get(f"/meetings/{public_id}/transcript")).json()["items"]
    text = " ".join(row["text"] for row in transcript)
    assert (
        text.split().count("anchor")
        == text.split().count("boundary")
        == text.split().count("after.")
        == 1
    )
    assert all(not row["uncertain"] for row in transcript)


async def test_short_unknown_keeps_text_without_creating_a_profile(
    meeting_harness: MeetingHarness,
) -> None:
    class ShortProvider(Provider):
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
            payload = await super().analyze(
                audio,
                job_public_id=job_public_id,
                tenant_public_id=tenant_public_id,
                language=language,
                max_speakers=max_speakers,
                num_speakers=num_speakers,
            )
            values = payload.model_dump()
            values["turns"] = values["exclusive_turns"] = [
                {"start": 0, "end": 21, "speaker": "local-a"},
                {"start": 23, "end": 24, "speaker": "short-b"},
            ]
            values["tracks"][0].update(
                validated_ranges=[{"start": 0, "end": 21}],
                validated_seconds=21,
                used_seconds=21,
                windows_count=3,
            )
            values["tracks"].append(
                {
                    "speaker": "short-b",
                    "status": "insufficient_speech",
                    "embedding": None,
                    "dimensions": 192,
                    "validated_ranges": [],
                    "validated_seconds": 0,
                    "used_seconds": 0,
                    "windows_count": 0,
                    "min_pair_similarity": None,
                    "preprocessing_version": "vad-windows-v1",
                }
            )
            values["words"] = [
                {"start": 1, "end": 2, "word": " Alpha", "probability": 0.9},
                {"start": 23, "end": 24, "word": " Hi", "probability": 0.9},
            ]
            return MeetingChunkResult.model_validate(values)

    harness, provider = meeting_harness, ShortProvider()
    public_id = await queued(harness, 30)
    for _ in range(4):
        await worker(harness, provider).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded" and state["count_mismatch"]
    speakers = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"]
    assert [row["decision"] for row in speakers] == ["enrolled", "profile_pending"]
    transcript = (await harness.client.get(f"/meetings/{public_id}/transcript")).json()["items"]
    assert (
        transcript[-1]["text"] == "Hi"
        and transcript[-1]["speaker_public_id"] == speakers[1]["public_id"]
    )
