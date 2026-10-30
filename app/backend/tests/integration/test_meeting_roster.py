"""Participant lists narrow persistent identity search without forcing unlisted voices."""

import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domain.models.meeting import Meeting, MeetingSpeaker
from app.domain.models.speaker_identity import SpeakerProfile
from app.domain.models.tenant import Tenant
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from tests.integration import test_meeting_workflow as fixtures
from tests.integration.test_meeting_memory import (
    EvidenceProvider,
    memory,
    prepare,
    profile_count,
)
from tests.integration.test_meeting_workflow import (
    PERMISSIONS,
    MeetingHarness,
    source_bytes,
    upload,
)

meeting_harness = fixtures.meeting_harness
pytestmark = pytest.mark.integration


async def create(harness: MeetingHarness, data: bytes, key: str | None = None, **body) -> dict:
    """Create as an ordinary reader-runner who may list saved profiles."""
    response = await harness.client.post(
        "/meetings",
        json={"title": "Fixture", "format": "WAV", "size_bytes": len(data), **body},
        headers={
            "Authorization": "Bearer " + harness.token([*PERMISSIONS, "speaker_profiles:read"]),
            "Idempotency-Key": key or str(uuid4()),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def mixed(weights: dict[int, float]) -> list[float]:
    vector = [weights.get(index, 0.0) for index in range(192)]
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector]


async def saved_profiles(harness: MeetingHarness, identities: list[int]) -> list[str]:
    """Enroll one profile per one-hot identity through the real memory transaction."""
    provider = EvidenceProvider()
    meeting_id, tracks = await prepare(harness, provider, identities)
    resolver = memory(harness, provider)
    for _ in tracks:
        assert await resolver.resolve_next(meeting_id, 1)
    async with harness.sessions() as session:
        rows = await session.scalars(
            select(MeetingSpeaker)
            .where(MeetingSpeaker.meeting_id == meeting_id)
            .order_by(MeetingSpeaker.ordinal)
        )
        profile_ids = [row.profile_id for row in rows]
        profiles = {
            profile.speaker_profile_id: profile.public_id
            for profile in await session.scalars(
                select(SpeakerProfile).where(SpeakerProfile.speaker_profile_id.in_(profile_ids))
            )
        }
    return [profiles[value] for value in profile_ids]


async def decide_listed(
    harness: MeetingHarness, vector: list[float], roster: list[str]
) -> tuple[MeetingSpeaker, int]:
    data = source_bytes(22.0)
    meeting = await create(harness, data, participant_profile_ids=roster)
    assert (await upload(harness.client, meeting, data)).status_code == 200
    assert (
        await harness.client.post(f"/meetings/{meeting['public_id']}/complete")
    ).status_code == 202
    provider = EvidenceProvider()
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        row.status = "finalizing"
        row.claim_token = 1
        row.lease_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        track = MeetingSpeaker(
            tenant_id=row.tenant_id,
            meeting_id=row.meeting_id,
            ordinal=0,
            reason="no_profiles",
            speech_seconds=21.0,
            embedding=vector,
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            source_sha256=row.source_sha256,
            clean_ranges=[[0, 21 * 16000]],
        )
        session.add(track)
        await session.flush()
        provider.vectors[track.public_id] = vector
        meeting_id = row.meeting_id
    before = await profile_count(harness)
    assert await memory(harness, provider).resolve_next(meeting_id, 1)
    async with harness.sessions() as session:
        decided = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
    return decided, await profile_count(harness) - before


async def profile_public_id(harness: MeetingHarness, profile_id: int | None) -> str | None:
    if profile_id is None:
        return None
    async with harness.sessions() as session:
        return (await session.get(SpeakerProfile, profile_id)).public_id


async def test_listed_participants_are_returned_without_becoming_a_count_hint(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    first, second, _ = await saved_profiles(harness, [0, 1, 2])
    data, key = source_bytes(), str(uuid4())
    created = await create(harness, data, key, participant_profile_ids=[second, first])
    assert {item["profile_public_id"] for item in created["participants"]} == {first, second}
    assert all(item["name"] for item in created["participants"])
    # Saved-only lists omit new attendees, so they never become a diarization bound.
    assert created["participant_count"] is None and created["expected_speakers"] is None
    replay = await create(harness, data, key, participant_profile_ids=[first, second])
    assert replay["public_id"] == created["public_id"]
    conflict = await harness.client.post(
        "/meetings",
        json={
            "title": "Fixture",
            "format": "WAV",
            "size_bytes": len(data),
            "participant_profile_ids": [first],
        },
        headers={
            "Authorization": "Bearer " + harness.token([*PERMISSIONS, "speaker_profiles:read"]),
            "Idempotency-Key": key,
        },
    )
    assert conflict.status_code == 409


@pytest.mark.parametrize(
    ("change", "status", "code"),
    [
        (lambda ids: {"participant_profile_ids": [str(uuid4())]}, 404, "participant_not_found"),
        (lambda ids: {"participant_profile_ids": [ids[0], ids[0]]}, 422, "validation_error"),
        (
            lambda ids: {"participant_profile_ids": ids, "participant_count": 1},
            422,
            "validation_error",
        ),
        (
            lambda ids: {"participant_profile_ids": [str(uuid4()) for _ in range(51)]},
            422,
            "validation_error",
        ),
    ],
)
async def test_invalid_participant_lists_are_rejected_without_creating_a_meeting(
    meeting_harness: MeetingHarness, change, status: int, code: str
) -> None:
    harness = meeting_harness
    ids = await saved_profiles(harness, [0, 1])
    data = source_bytes()
    response = await harness.client.post(
        "/meetings",
        json={"title": "Fixture", "format": "WAV", "size_bytes": len(data), **change(ids)},
        headers={
            "Authorization": "Bearer " + harness.token([*PERMISSIONS, "speaker_profiles:read"]),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert (await harness.client.get("/meetings")).json()["total"] == 1


async def test_listing_requires_profile_read_and_rejects_foreign_profiles(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    (listed,) = await saved_profiles(harness, [0])
    data = source_bytes()
    body = {
        "title": "Fixture",
        "format": "WAV",
        "size_bytes": len(data),
        "auto_enroll": False,
        "participant_profile_ids": [listed],
    }
    no_read = {
        "Authorization": "Bearer " + harness.token(["meeting_analysis:run"]),
        "Idempotency-Key": str(uuid4()),
    }
    assert (await harness.client.post("/meetings", json=body, headers=no_read)).status_code == 403
    async with harness.sessions() as session, session.begin():
        other = Tenant(code=f"foreign-{uuid4().hex}", name="Other")
        session.add(other)
        await session.flush()
        foreign = SpeakerProfile(
            tenant_id=other.tenant_id,
            name="Foreign",
            sample_count=1,
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            embedding=mixed({0: 1.0}),
            source_sha256="f" * 64,
        )
        session.add(foreign)
        await session.flush()
        foreign_id = foreign.public_id
    response = await harness.client.post(
        "/meetings",
        json={**body, "participant_profile_ids": [foreign_id]},
        headers={
            "Authorization": "Bearer " + harness.token([*PERMISSIONS, "speaker_profiles:read"]),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "participant_not_found"


async def test_list_resolves_similar_unlisted_people_but_never_overrides_a_better_one(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    first, second, _ = await saved_profiles(harness, [0, 1, 2])
    close_pair = mixed({0: 0.62, 2: 0.58, 3: 0.5284})
    unlisted, _ = await decide_listed(harness, close_pair, [])
    assert (unlisted.decision, unlisted.reason) == ("ambiguous", "insufficient_margin")
    listed, created = await decide_listed(harness, close_pair, [first])
    assert listed.decision == "recognized" and created == 0
    assert await profile_public_id(harness, listed.profile_id) == first
    better_outside, created = await decide_listed(harness, mixed({0: 0.6, 1: 0.8}), [first])
    assert (better_outside.decision, better_outside.reason) == ("ambiguous", "outside_roster")
    assert better_outside.profile_id is None and created == 0
    del second


async def test_unlisted_saved_guest_is_recognized_not_duplicated(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    first, second = await saved_profiles(harness, [0, 1])
    guest, created = await decide_listed(harness, mixed({1: 1.0}), [first])
    assert guest.decision == "recognized" and created == 0
    assert await profile_public_id(harness, guest.profile_id) == second
