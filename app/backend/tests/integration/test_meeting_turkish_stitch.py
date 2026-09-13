"""Turkish boundary matching through HTTP uploads and persisted worker restarts."""

from copy import deepcopy

import pytest
from sqlalchemy import select

from app.domain.models.meeting import Meeting, MeetingChunk
from app.services.meeting_ports import MeetingChunkResult
from app.services.speaker_ports import SpeakerError
from tests.integration import test_meeting_workflow as fixtures
from tests.integration.test_meeting_worker import Provider, worker
from tests.integration.test_meeting_workflow import MeetingHarness, create, source_bytes, upload

meeting_harness = fixtures.meeting_harness
pytestmark = pytest.mark.integration


class TurkishBoundaryProvider(Provider):
    def __init__(self, meeting_language: str, languages: tuple[str, str]):
        super().__init__()
        self.meeting_language = meeting_language
        self.languages = languages

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
        assert language == (None if self.meeting_language == "auto" else self.meeting_language)
        payload = await super().analyze(
            audio,
            job_public_id=job_public_id,
            tenant_public_id=tenant_public_id,
            language=language,
            max_speakers=max_speakers,
            num_speakers=num_speakers,
        )
        # The second source window starts at 295 seconds, including five seconds of context.
        first = payload.input_seconds > 300
        values = payload.model_dump()
        values["language"] = self.languages[0 if first else 1]
        values["words"] = [
            {
                "start": 299 if first else 4.1,
                "end": 299.4 if first else 4.5,
                "word": " IŞIK" if first else " ışık",
                "probability": 0.95,
            },
            {
                "start": 299.6 if first else 4.7,
                "end": 300 if first else 5.1,
                "word": " YENİ" if first else " yeni",
                "probability": 0.85,
            },
        ]
        values["segments"] = [
            {
                "start": values["words"][0]["start"],
                "end": values["words"][-1]["end"],
                "text": "IŞIK YENİ" if first else "ışık yeni",
            }
        ]
        return MeetingChunkResult.model_validate(values)


async def queued_in_language(harness: MeetingHarness, language: str) -> str:
    data = source_bytes(330)
    meeting = await create(harness.client, data, language=language, expected_speakers=1)
    for index, offset in enumerate(range(0, len(data), 4194304)):
        response = await upload(harness.client, meeting, data[offset : offset + 4194304], index)
        assert response.status_code == 200
    assert (
        await harness.client.post(f"/meetings/{meeting['public_id']}/complete")
    ).status_code == 202
    return meeting["public_id"]


async def checkpoint(harness: MeetingHarness, public_id: str, legacy: str | None = None) -> dict:
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(
            select(MeetingChunk)
            .join(Meeting, Meeting.meeting_id == MeetingChunk.meeting_id)
            .where(
                Meeting.tenant_id == harness.tenant.tenant_id,
                Meeting.public_id == public_id,
                MeetingChunk.index == 0,
            )
        )
        assert row is not None
        if legacy:
            value = deepcopy(row.result)
            if legacy == "missing_provider":
                value.pop("provider")
            else:
                value["provider"].pop("language")
            row.result = value
        return deepcopy(row.result)


@pytest.mark.parametrize(
    "language,provider_languages,legacy,expected_words",
    [
        ("tr", ("tr", "tr"), None, 2),
        ("tr", ("en", "en"), None, 2),
        ("auto", ("tr", "tr"), None, 2),
        ("auto", ("en", "tr"), None, 4),
        ("auto", ("tr", "en"), None, 4),
        ("en", ("tr", "tr"), None, 4),
        ("auto", ("tr", "tr"), "missing_language", 4),
        ("auto", ("tr", "tr"), "missing_provider", 4),
        ("tr", ("tr", "tr"), "missing_language", 2),
    ],
)
async def test_persisted_language_selects_stitch_without_rewriting_previous_checkpoint(
    meeting_harness: MeetingHarness,
    language: str,
    provider_languages: tuple[str, str],
    legacy: str | None,
    expected_words: int,
) -> None:
    harness = meeting_harness
    provider = TurkishBoundaryProvider(language, provider_languages)
    public_id = await queued_in_language(harness, language)
    assert await worker(harness, provider).process_once()
    path = f"/meetings/{public_id}"
    assert (await harness.client.get(path + "/transcript")).json()["items"] == []
    previous = await checkpoint(harness, public_id, legacy)
    assert await worker(harness, provider).process_once()
    transcript = (await harness.client.get(path + "/transcript")).json()["items"]
    words = " ".join(row["text"] for row in transcript).split()
    assert len(words) == expected_words
    assert all(row["uncertain"] is (expected_words == 4) for row in transcript)
    if expected_words == 2:
        assert words == ["IŞIK", "YENİ"]
        assert [(row["start_seconds"], row["end_seconds"]) for row in transcript] == [(299, 300)]
    else:
        assert words == ["IŞIK", "ışık", "YENİ", "yeni"]
    assert await checkpoint(harness, public_id) == previous
    state = (await harness.client.get(path)).json()
    assert state["completed_chunks"] == 2 and state["processed_seconds"] == 330


async def test_auto_turkish_retry_reuses_checkpoint_and_completed_transcript_stays_unchanged(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    provider = TurkishBoundaryProvider("auto", ("tr", "tr"))
    public_id = await queued_in_language(harness, "auto")
    path = f"/meetings/{public_id}"
    assert await worker(harness, provider).process_once()
    previous = await checkpoint(harness, public_id)
    provider.error = SpeakerError("invalid_audio", 400)
    assert await worker(harness, provider).process_once()
    state = (await harness.client.get(path)).json()
    assert state["status"] == "failed" and state["completed_chunks"] == 1
    assert await checkpoint(harness, public_id) == previous
    assert (await harness.client.post(path + "/retry")).status_code == 202
    provider.error = None
    assert await worker(harness, provider).process_once()
    transcript = (await harness.client.get(path + "/transcript")).json()["items"]
    assert [row["text"] for row in transcript] == ["IŞIK YENİ"]
    assert not transcript[0]["uncertain"]
    for _ in range(3):
        await worker(harness, provider).process_once()
    assert (await harness.client.get(path)).json()["status"] == "succeeded"
    completed = (await harness.client.get(path + "/transcript")).json()["items"]
    # Finalization resolves profile display names, while persisted text and source times stay fixed.
    stable_fields = (
        "public_id",
        "ordinal",
        "speaker_public_id",
        "start_seconds",
        "end_seconds",
        "text",
        "language",
        "overlap",
        "uncertain",
    )
    assert [{key: row[key] for key in stable_fields} for row in completed] == [
        {key: row[key] for key in stable_fields} for row in transcript
    ]
    assert not await worker(harness, provider).process_once()
    assert (await harness.client.get(path + "/transcript")).json()["items"] == completed
    assert await checkpoint(harness, public_id) == previous
