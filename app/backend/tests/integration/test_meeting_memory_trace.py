"""Matching traces commit with real memory decisions and follow result retention."""

import math
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.domain.models.meeting import Meeting, MeetingSpeaker
from app.services.meeting_cleanup import MeetingCleanup
from app.services.meeting_memory_ports import MeetingMemoryResult, MemoryContext
from app.services.meeting_ports import MeetingTracking
from app.services.speaker_ports import SpeakerError
from tests.integration import test_meeting_workflow as fixture_module
from tests.integration.test_meeting_context_memory import (
    ContextProvider,
    prepare_contexts,
    resolver,
)
from tests.integration.test_meeting_memory import EvidenceProvider, memory, prepare, profile_count
from tests.integration.test_meeting_workflow import MeetingHarness

meeting_harness = fixture_module.meeting_harness
pytestmark = pytest.mark.integration


async def stored(harness: MeetingHarness, meeting_id: int) -> MeetingSpeaker:
    async with harness.sessions() as session:
        return await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )


@pytest.mark.parametrize("context", [False, True])
async def test_private_trace_commits_with_enrollment_and_is_absent_from_http(
    meeting_harness: MeetingHarness, context: bool
) -> None:
    harness = meeting_harness
    if context:
        provider = ContextProvider()
        meeting_id, _ = await prepare_contexts(harness, [0])
        service = resolver(harness, provider)
    else:
        provider = EvidenceProvider()
        meeting_id, _ = await prepare(harness, provider, [0])
        service = memory(harness, provider)
    evidence = await service.snapshot(meeting_id, 1)
    assert await service.resolve_next(meeting_id, 1)
    row = await stored(harness, meeting_id)
    actual = row.props["memory_match_trace"]
    assert row.decision == "enrolled" and row.reason == "new_profile_created"
    assert actual["evidence_sha256"] == evidence.fingerprint
    assert actual["ecapa192"]["scores"] == []
    assert actual["ecapa192"]["reason"] == "no_profiles"
    assert actual["winner_agreement"] is None
    if context:
        assert actual["community256"]["scores"] == []
    else:
        assert actual["community256"] is None
    async with harness.sessions() as session:
        meeting = await session.get(Meeting, meeting_id)
    response = await harness.client.get(f"/meetings/{meeting.public_id}/speakers")
    assert response.status_code == 200
    public = response.json()["items"][0]
    assert public["decision"] == "enrolled"
    assert not {"props", "memory_match_trace", "ecapa192", "community256"} & public.keys()


class GrayZoneProvider(ContextProvider):
    async def verify(
        self,
        audio: bytes,
        *,
        contexts: list[MemoryContext],
        target: MeetingTracking,
        competitors: list[MeetingTracking],
        job_public_id: str,
        tenant_public_id: str,
    ) -> MeetingMemoryResult:
        value = await super().verify(
            audio,
            contexts=contexts,
            target=target,
            competitors=competitors,
            job_public_id=job_public_id,
            tenant_public_id=tenant_public_id,
        )
        body = value.model_dump()
        body["embedding192"] = [0.51, 0.31, math.sqrt(1 - 0.51**2 - 0.31**2)] + [0.0] * 189
        body["memory_embedding"]["embedding"] = [
            0.1,
            0.2,
            math.sqrt(1 - 0.1**2 - 0.2**2),
        ] + [0.0] * 253
        return MeetingMemoryResult.model_validate(body)


async def test_gray_zone_retains_original_model_reasons_without_changing_fusion(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    for identity in [0, 1]:
        meeting_id, _ = await prepare_contexts(harness, [identity])
        assert await resolver(harness, ContextProvider()).resolve_next(meeting_id, 1)
    meeting_id, _ = await prepare_contexts(harness, [2])
    assert await resolver(harness, GrayZoneProvider()).resolve_next(meeting_id, 1)
    row = await stored(harness, meeting_id)
    assert row.decision == "ambiguous" and row.reason == "insufficient_margin"
    actual = row.props["memory_match_trace"]
    assert actual["ecapa192"]["scores"] == pytest.approx([0.51, 0.31], abs=1e-6)
    assert actual["ecapa192"]["reason"] == "below_match_threshold"
    assert actual["community256"]["scores"] == pytest.approx([0.2, 0.1], abs=1e-6)
    assert actual["community256"]["reason"] == "below_new_threshold"
    assert actual["winner_agreement"] is False
    assert await profile_count(harness) == 2


async def test_completed_trace_is_immutable_and_missing_history_is_not_backfilled(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(harness, [0])
    service = resolver(harness, provider)
    evidence = await service.snapshot(meeting_id, 1)
    assert await service.resolve_next(meeting_id, 1)
    original = (await stored(harness, meeting_id)).props["memory_match_trace"]
    assert await service.persist(evidence, 1, None, None, False, "insufficient_speech")
    assert (await stored(harness, meeting_id)).props["memory_match_trace"] == original
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        row.props = {key: value for key, value in row.props.items() if key != "memory_match_trace"}
    assert await service.persist(evidence, 1, None, None, False, "insufficient_speech")
    assert "memory_match_trace" not in (await stored(harness, meeting_id)).props
    assert await profile_count(harness) == 1


async def test_recognized_return_records_agreeing_real_gallery_winners(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    first, _ = await prepare_contexts(harness, [0])
    assert await resolver(harness, provider).resolve_next(first, 1)
    second, _ = await prepare_contexts(harness, [0], seconds=12)
    assert await resolver(harness, provider).resolve_next(second, 1)
    row = await stored(harness, second)
    assert row.decision == "recognized" and row.reason == "matched"
    actual = row.props["memory_match_trace"]
    assert actual["winner_agreement"] is True
    for name in ["ecapa192", "community256"]:
        assert actual[name]["scores"] == pytest.approx([1.0])
        assert actual[name]["decision"] == "recognized" and actual[name]["reason"] == "matched"
    assert await profile_count(harness) == 1


async def test_quality_rejection_does_not_fabricate_matching_scores(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    provider.status = "inconsistent_audio"
    meeting_id, _ = await prepare_contexts(harness, [0])
    assert await resolver(harness, provider).resolve_next(meeting_id, 1)
    row = await stored(harness, meeting_id)
    assert row.decision == "profile_pending" and row.reason == "inconsistent_audio"
    assert "memory_match_trace" not in row.props


@pytest.mark.parametrize("changed", ["claim", "source"])
async def test_stale_source_or_claim_cannot_commit_a_trace(
    meeting_harness: MeetingHarness, changed: str
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(harness, [0])
    service = resolver(harness, provider)
    evidence = await service.snapshot(meeting_id, 1)
    async with harness.sessions() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        if changed == "claim":
            meeting.claim_token = 2
        else:
            meeting.source_sha256 = "b" * 64
    if changed == "claim":
        assert not await service.persist(evidence, 1, None, None, False, "insufficient_speech")
    else:
        with pytest.raises(SpeakerError, match="model_mismatch"):
            await service.persist(evidence, 1, None, None, False, "insufficient_speech")
    row = await stored(harness, meeting_id)
    assert "memory_match_trace" not in row.props and not row.props.get("memory_completed")


async def test_result_cleanup_scrubs_real_trace_and_keeps_profile(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(harness, [0])
    service = resolver(harness, provider)
    assert await service.resolve_next(meeting_id, 1)
    assert "memory_match_trace" in (await stored(harness, meeting_id)).props
    async with harness.sessions() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        meeting.status = "succeeded"
        meeting.finished_at = datetime.now(UTC) - timedelta(days=31)
        meeting.source_expires_at = datetime.now(UTC) - timedelta(days=24)
        meeting.lease_expires_at = None
    assert await MeetingCleanup(harness.sessions, service.storage, harness.settings).run() == 1
    row = await stored(harness, meeting_id)
    assert row.props == {} and row.is_deleted
    assert await profile_count(harness) == 1
