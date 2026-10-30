"""Optional meeting subject and questions are stored with the meeting and reach no speech model."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.domain.models.meeting import Meeting, MeetingQuestion
from app.domain.models.tenant import Tenant
from tests.integration import test_meeting_workflow as workflow_fixtures
from tests.integration.test_meeting_worker import Provider, worker
from tests.integration.test_meeting_workflow import MeetingHarness, create, source_bytes, upload

meeting_client = workflow_fixtures.meeting_client
meeting_harness = workflow_fixtures.meeting_harness
pytestmark = pytest.mark.integration


async def post(client: AsyncClient, key: str | None = None, **fields):
    return await client.post(
        "/meetings",
        json={"title": "Meeting", "format": "WAV", "size_bytes": 100, **fields},
        headers={"Idempotency-Key": key or str(uuid4())},
    )


async def test_meeting_without_details_behaves_as_before(meeting_client: AsyncClient) -> None:
    created = await create(meeting_client, source_bytes())
    assert created["subject"] is None and created["questions"] == []


async def test_subject_and_questions_are_normalized_and_keep_their_order(
    meeting_client: AsyncClient,
) -> None:
    created = await create(
        meeting_client,
        source_bytes(),
        subject="  Bütçe   planı ",
        questions=["  Bütçe  onaylandı mı? ", "Kim sorumlu?"],
    )
    assert created["subject"] == "Bütçe planı"
    assert [row["text"] for row in created["questions"]] == ["Bütçe onaylandı mı?", "Kim sorumlu?"]
    read = (await meeting_client.get(f"/meetings/{created['public_id']}")).json()
    assert read["questions"] == created["questions"]
    listed = (await meeting_client.get("/meetings")).json()["items"]
    assert next(row for row in listed if row["public_id"] == created["public_id"])["subject"] == (
        "Bütçe planı"
    )


async def test_voice_memory_stays_off_unless_requested(meeting_client: AsyncClient) -> None:
    assert (await post(meeting_client)).json()["auto_enroll"] is False
    assert (await post(meeting_client, auto_enroll=True)).json()["auto_enroll"] is True


async def test_blank_subject_is_absent(meeting_client: AsyncClient) -> None:
    assert (await post(meeting_client, subject="   ")).json()["subject"] is None


@pytest.mark.parametrize(
    "fields",
    [
        {"subject": "k" * 501},
        {"questions": ["   "]},
        {"questions": ["q" * 501]},
        {"questions": [f"Soru {number}" for number in range(21)]},
        {"questions": ["Aynı soru", "aynı  SORU"]},
        {"questions": "tek soru"},
    ],
)
async def test_invalid_details_are_rejected(meeting_client: AsyncClient, fields: dict) -> None:
    assert (await post(meeting_client, **fields)).status_code == 422


async def test_twenty_questions_are_accepted(meeting_client: AsyncClient) -> None:
    response = await post(meeting_client, questions=[f"Soru {number}" for number in range(20)])
    assert response.status_code == 201
    assert len(response.json()["questions"]) == 20


async def test_details_belong_to_the_retry_identity(meeting_client: AsyncClient) -> None:
    key = str(uuid4())
    first = await post(meeting_client, key, subject="Konu", questions=["Soru?"])
    assert first.status_code == 201
    repeated = await post(meeting_client, key, subject="Konu", questions=["Soru?"])
    assert repeated.json()["public_id"] == first.json()["public_id"]
    assert repeated.json()["questions"] == first.json()["questions"]
    assert (
        await post(meeting_client, key, subject="Konu", questions=["Başka?"])
    ).status_code == 409
    assert (
        await post(meeting_client, key, subject="Başka", questions=["Soru?"])
    ).status_code == 409


async def test_details_stay_inside_the_tenant(meeting_harness: MeetingHarness) -> None:
    harness = meeting_harness
    created = await create(harness.client, source_bytes(), subject="Gizli", questions=["Gizli?"])
    path = f"/meetings/{created['public_id']}"
    async with harness.sessions() as session, session.begin():
        other = Tenant(code=f"foreign-{uuid4().hex}", name="Other")
        session.add(other)
        await session.flush()
    foreign = {
        "Authorization": "Bearer " + harness.token([], super_admin=True),
        harness.settings.tenant_header: other.public_id,
    }
    assert (await harness.client.get(path, headers=foreign)).status_code == 404
    listed = await harness.client.get("/meetings", headers=foreign)
    assert listed.json()["items"] == []
    async with harness.sessions() as session:
        meeting = await session.scalar(
            select(Meeting).where(Meeting.public_id == created["public_id"])
        )
        rows = list(
            await session.scalars(
                select(MeetingQuestion).where(MeetingQuestion.meeting_id == meeting.meeting_id)
            )
        )
    assert [row.tenant_id for row in rows] == [meeting.tenant_id]


async def test_deleted_meeting_hides_its_details(meeting_client: AsyncClient) -> None:
    created = await create(meeting_client, source_bytes(), subject="Konu", questions=["Soru?"])
    path = f"/meetings/{created['public_id']}"
    assert (await meeting_client.post(path + "/cancel")).status_code in {200, 202}
    assert (await meeting_client.delete(path)).status_code == 204
    assert (await meeting_client.get(path)).status_code == 404


async def test_only_the_maximum_reaches_the_model_and_details_never_do(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, Provider()
    data = source_bytes(60)
    meeting = await create(
        harness.client,
        data,
        participant_count=5,
        expected_speakers=3,
        subject="Konu",
        questions=["Soru?"],
    )
    assert (await upload(harness.client, meeting, data)).status_code == 200
    path = f"/meetings/{meeting['public_id']}"
    assert (await harness.client.post(path + "/complete")).status_code == 202
    assert await worker(harness, provider).process_once()
    assert provider.calls == [(5, None)]


async def test_a_short_meeting_with_only_an_estimate_sends_no_count(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, Provider()
    data = source_bytes(60)
    meeting = await create(harness.client, data, expected_speakers=3)
    assert (await upload(harness.client, meeting, data)).status_code == 200
    assert (
        await harness.client.post(f"/meetings/{meeting['public_id']}/complete")
    ).status_code == 202
    assert await worker(harness, provider).process_once()
    assert provider.calls == [(None, None)]
