"""Persisted speaker turns cover each chunk's committed source time exactly once."""

from itertools import pairwise

import pytest
from sqlalchemy import select

from app.domain.models.meeting import Meeting, MeetingChunk
from tests.integration import test_meeting_workflow as fixtures
from tests.integration.test_meeting_worker import Provider, queued, worker
from tests.integration.test_meeting_workflow import MeetingHarness

meeting_harness = fixtures.meeting_harness
pytestmark = pytest.mark.integration


async def processed(harness: MeetingHarness, seconds: float = 601) -> str:
    public_id = await queued(harness, seconds)
    for _ in range(8):
        await worker(harness, Provider()).process_once()
    state = (await harness.client.get(f"/meetings/{public_id}")).json()
    assert state["status"] == "succeeded"
    return public_id


async def all_turns(harness: MeetingHarness, public_id: str) -> list[dict]:
    items, offset = [], 0
    while True:
        response = await harness.client.get(
            f"/meetings/{public_id}/speaker-turns", params={"offset": offset, "limit": 100}
        )
        assert response.status_code == 200
        page = response.json()
        assert page["provisional"] is False
        items.extend(page["items"])
        offset += page["limit"]
        if offset >= page["total"]:
            return items


async def test_turns_cover_multi_chunk_meeting_once_with_public_speaker_ids(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    public_id = await processed(harness)
    turns = await all_turns(harness, public_id)
    speakers = (await harness.client.get(f"/meetings/{public_id}/speakers")).json()["items"]
    assert {turn["speaker_public_id"] for turn in turns} == {speakers[0]["public_id"]}
    assert turns == sorted(turns, key=lambda turn: (turn["start_seconds"], turn["end_seconds"]))
    assert turns[0]["start_seconds"] == 0 and turns[-1]["end_seconds"] == 601
    for previous, current in pairwise(turns):
        assert current["start_seconds"] >= previous["end_seconds"]
    assert sum(turn["end_seconds"] - turn["start_seconds"] for turn in turns) == pytest.approx(601)
    async with harness.sessions() as session:
        meeting = (
            await session.scalars(select(Meeting).where(Meeting.public_id == public_id))
        ).one()
        chunks = (
            await session.scalars(
                select(MeetingChunk).where(MeetingChunk.meeting_id == meeting.meeting_id)
            )
        ).all()
    assert len(chunks) == 3 and all("speaker_turns" in chunk.result for chunk in chunks)


async def test_pages_are_bounded_and_beyond_range_is_empty(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    public_id = await processed(harness)
    first = (
        await harness.client.get(f"/meetings/{public_id}/speaker-turns", params={"limit": 1})
    ).json()
    assert len(first["items"]) == 1 and first["total"] >= 1 and first["limit"] == 1
    beyond = (
        await harness.client.get(
            f"/meetings/{public_id}/speaker-turns", params={"offset": first["total"]}
        )
    ).json()
    assert beyond["items"] == [] and beyond["total"] == first["total"]
    invalid = await harness.client.get(
        f"/meetings/{public_id}/speaker-turns", params={"limit": 101}
    )
    assert invalid.status_code == 422


async def test_checkpoint_without_turns_reports_unavailable_instead_of_partial_timeline(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    public_id = await processed(harness)
    async with harness.sessions() as session, session.begin():
        meeting = (
            await session.scalars(select(Meeting).where(Meeting.public_id == public_id))
        ).one()
        chunk = (
            await session.scalars(
                select(MeetingChunk)
                .where(MeetingChunk.meeting_id == meeting.meeting_id)
                .order_by(MeetingChunk.index)
                .limit(1)
            )
        ).one()
        chunk.result = {key: value for key, value in chunk.result.items() if key != "speaker_turns"}
    response = await harness.client.get(f"/meetings/{public_id}/speaker-turns")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "speaker_turns_unavailable"
