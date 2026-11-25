"""PRD 037: each channel of a two-channel capture is diarized and transcribed on its own."""

import hashlib

import numpy as np
import pytest
from sqlalchemy import select

from app.domain.models.meeting import Meeting, MeetingDiarization, MeetingSpeaker
from app.services.meeting_ports import MeetingRecordingResult
from tests.integration import test_meeting_repository as database_fixtures
from tests.integration import test_meeting_workflow as workflow_fixtures
from tests.integration.test_meeting_whole_recording import IDENTITY, TRACKING, WholeProvider, run
from tests.integration.test_meeting_worker import worker
from tests.integration.test_meeting_workflow import MeetingHarness

migrated_meeting_database = database_fixtures.migrated_meeting_database
meeting_harness = workflow_fixtures.meeting_harness
pytestmark = pytest.mark.integration

RATE = 16000
SECONDS = 330
MICROPHONE_LEVEL, SYSTEM_LEVEL = 0.1, 0.3
# Both channels use the label SPEAKER_00: labels only name speakers within one channel.
CHANNEL_TURNS = {
    "microphone": [(5.0, 60.0, "SPEAKER_00"), (200.0, 250.0, "SPEAKER_00")],
    "system": [(0.0, 100.0, "SPEAKER_00"), (100.0, float(SECONDS), "SPEAKER_01")],
}


class ChannelProvider(WholeProvider):
    """Recognises the channel by its level and answers with that channel's speakers."""

    def __init__(self) -> None:
        super().__init__()
        self.levels: list[float] = []

    async def diarize_recording(
        self, blocks, *, sample_rate, size_bytes, job_public_id, tenant_public_id, max_speakers
    ) -> MeetingRecordingResult:
        data = b"".join([block async for block in blocks])
        self.recordings.append((sample_rate, size_bytes, len(data), max_speakers))
        level = float(np.abs(np.frombuffer(data, dtype="<i2")).mean() / 32768)
        self.levels.append(round(level, 2))
        channel = "microphone" if level < (MICROPHONE_LEVEL + SYSTEM_LEVEL) / 2 else "system"
        turns = [
            {"start": start, "end": end, "speaker": label}
            for start, end, label in CHANNEL_TURNS[channel]
        ]
        labels = sorted({row["speaker"] for row in turns})
        return MeetingRecordingResult.model_validate(
            {
                "input_seconds": len(data) // 2 / sample_rate,
                "sample_rate": 16000,
                "device": "cuda:0",
                "turns": turns,
                "exclusive_turns": turns,
                "speakers": [
                    {
                        "speaker": label,
                        "tracking": {
                            "embedding": [0.0] * index + [1.0] + [0.0] * (255 - index),
                            **TRACKING,
                        },
                    }
                    for index, label in enumerate(labels)
                ],
                "model_identity": IDENTITY,
            }
        )


async def captured(harness: MeetingHarness) -> str:
    frames = SECONDS * RATE
    samples = np.empty((frames, 2), dtype="<i2")
    samples[:, 0] = round(MICROPHONE_LEVEL * 32767)
    samples[:, 1] = round(SYSTEM_LEVEL * 32767)
    pcm = samples.tobytes()
    created = await harness.client.post(
        "/meetings/captures",
        json={"title": "Teams", "sample_rate": RATE, "participant_count": 5},
        headers={"Idempotency-Key": hashlib.sha256(pcm[:64]).hexdigest()[:32]},
    )
    assert created.status_code == 201, created.text
    public_id = created.json()["public_id"]
    chain, step = bytes(32), 4 * RATE * 4
    for offset in range(0, len(pcm), step):
        part = pcm[offset : offset + step]
        response = await harness.client.put(
            f"/meetings/{public_id}/capture-frames/{offset // 4}",
            content=part,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Chunk-SHA256": hashlib.sha256(part).hexdigest(),
            },
        )
        assert response.status_code == 200, response.text
        chain = hashlib.sha256(chain + hashlib.sha256(part).digest()).digest()
    completed = await harness.client.post(
        f"/meetings/{public_id}/capture/complete",
        json={"frames": frames, "chain_sha256": chain.hex()},
    )
    assert completed.status_code == 202, completed.text
    return public_id


async def test_each_channel_is_diarized_and_read_on_its_own(
    meeting_harness: MeetingHarness, migrated_meeting_database: None
) -> None:
    harness, provider = meeting_harness, ChannelProvider()
    public_id = await captured(harness)
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["total_chunks"] == 4, "two windows, each read once per channel"

    # One pass per claim: the microphone first, then the system audio.
    assert await worker(harness, provider).process_once()
    async with harness.sessions() as session:
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        assert meeting.props.get("diarization_flow") is None
    assert await worker(harness, provider).process_once()
    assert provider.levels == [MICROPHONE_LEVEL, SYSTEM_LEVEL]
    assert all(
        size == received == SECONDS * RATE * 2 for _, size, received, _ in provider.recordings
    )

    final = await run(harness, provider, public_id)
    assert final["status"] == "succeeded"
    assert provider.calls == [], "no chunk separates its own speakers"
    # Each chunk received its own channel's turns: windows alternate microphone, system.
    # The microphone is silent in the last window, so that chunk gets no turns at all.
    assert [sorted({turn["speaker"] for turn in row["turns"]}) for row in provider.attributed] == [
        ["SPEAKER_00"],
        ["SPEAKER_00", "SPEAKER_01"],
        [],
        ["SPEAKER_01"],
    ]
    assert provider.attributed[0]["turns"][0] == {
        "start": 5.0,
        "end": 60.0,
        "speaker": "SPEAKER_00",
    }
    assert provider.attributed[1]["turns"][0] == {
        "start": 0.0,
        "end": 100.0,
        "speaker": "SPEAKER_00",
    }

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
        diarizations = list(
            await session.scalars(
                select(MeetingDiarization)
                .where(MeetingDiarization.meeting_id == meeting.meeting_id)
                .order_by(MeetingDiarization.channel)
            )
        )
    assert [(row.channel, row.speaker_count) for row in diarizations] == [(0, 1), (1, 2)]
    # Numbered by first speech across both channels: system 0 s, microphone 5 s, system 100 s.
    assert [(row.channel, row.props["diarization_label"]) for row in speakers] == [
        (1, "SPEAKER_00"),
        (0, "SPEAKER_00"),
        (1, "SPEAKER_01"),
    ]
    listed = (await harness.client.get(f"/meetings/{public_id}/speakers?offset=0&limit=20")).json()
    assert [(row["ordinal"], row["channel"]) for row in listed["items"]] == [
        (0, "system"),
        (1, "microphone"),
        (2, "system"),
    ]
    lines = (
        await harness.client.get(f"/meetings/{public_id}/transcript?offset=0&limit=50")
    ).json()["items"]
    channel_of = {row.public_id: row.channel for row in speakers}
    starts = [line["start_seconds"] for line in lines]
    assert starts == sorted(starts), "lines from both channels read in time order"
    assert {channel_of[line["speaker_public_id"]] for line in lines} == {0, 1}
    microphone_lines = [line for line in lines if channel_of[line["speaker_public_id"]] == 0]
    # The microphone voice owns only its own turns, even while the system channel speaks.
    assert microphone_lines and all(
        5.0 <= line["start_seconds"] < 60.0 or 200.0 <= line["start_seconds"] < 250.0
        for line in microphone_lines
    )
