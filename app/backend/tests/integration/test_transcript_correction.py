"""Correction previews exercise real JWT, tenant queries, transactions and source immutability."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.api.meetings.router import get_transcript_correction_service
from app.core.config import get_settings
from app.core.security import create_access_token
from app.domain.models.meeting import Meeting, MeetingTranscript
from app.domain.models.role import UserRole
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.domain.transcript_correction import ProposedEdit
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.main import app
from app.services.transcript_correction import TranscriptCorrectionService
from app.services.transcript_correction_ports import (
    OllamaCorrectionResult,
    TranscriptCorrectionPort,
)
from tests.integration import test_meeting_audio_preview as preview
from tests.integration import test_meeting_workflow as workflow

meeting_harness = workflow.meeting_harness
pytestmark = pytest.mark.integration
DIGEST = "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"


async def prepared(harness, *, text="Yeni sürüyü sunucuya yükledik."):
    meeting = await workflow.create(harness.client, workflow.source_bytes(), auto_enroll=False)
    await workflow.seed_named_track(harness, meeting["public_id"], persistent=True)
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        row.status = "succeeded"
        row.source_expires_at = datetime.now(UTC) - timedelta(days=1)
        row.source_removed_at = datetime.now(UTC)
        target = await session.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == row.meeting_id)
        )
        target.text, target.language = text, "tr"
        target_id = target.public_id
    return (
        meeting["public_id"],
        target_id,
        f"/meetings/{meeting['public_id']}/transcript/{target_id}/correction-preview",
    )


class ObservedAdapter(TranscriptCorrectionPort):
    def __init__(self, session, during=None):
        self.session, self.during = session, during
        self.contexts = []

    async def review(self, context):
        assert not self.session.in_transaction()
        self.contexts.append(context)
        if self.during:
            await self.during()
        return OllamaCorrectionResult((ProposedEdit("sürüyü", "sürümü"),), "qwen3.5:27b", DIGEST)


def wire(harness, *, during=None):
    adapters = []

    async def dependency():
        async with harness.sessions() as session:
            adapter = ObservedAdapter(session, during)
            adapters.append(adapter)
            yield TranscriptCorrectionService(MeetingRepository(session), adapter)

    app.dependency_overrides[get_transcript_correction_service] = dependency
    return adapters


async def test_preview_is_transient_repeatable_and_does_not_require_retained_audio(meeting_harness):
    harness = meeting_harness
    _, target_id, url = await prepared(harness)
    adapters = wire(harness)
    before = await preview.snapshot(harness)
    response = await harness.client.post(url)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {
        "transcript_public_id",
        "source_text_sha256",
        "original_text",
        "suggested_text",
        "status",
        "edits",
        "rejected_count",
        "model_name",
        "model_digest",
        "policy_version",
    }
    assert body["transcript_public_id"] == target_id and body["status"] == "suggested"
    assert body["original_text"] == "Yeni sürüyü sunucuya yükledik."
    assert body["suggested_text"] == "Yeni sürümü sunucuya yükledik."
    assert body["edits"] == [
        {"start_char": 5, "end_char": 11, "original": "sürüyü", "replacement": "sürümü"}
    ]
    assert body["policy_version"] == "tr-context-words-v1"
    assert (await harness.client.post(url)).json() == body
    assert await preview.snapshot(harness) == before
    assert adapters[0].contexts[0].target_text == body["original_text"]


async def test_permissions_and_foreign_tenant_never_invoke_model(meeting_harness):
    harness = meeting_harness
    _, _, url = await prepared(harness)
    adapters = wire(harness)
    assert (await harness.client.post(url, headers={"Authorization": ""})).status_code == 401
    for permissions in [[], ["meeting_analysis:read"], ["meeting_analysis:run"]]:
        assert (
            await harness.client.post(
                url, headers={"Authorization": "Bearer " + harness.token(permissions)}
            )
        ).status_code == 403
    async with harness.sessions() as session, session.begin():
        other = Tenant(code=f"correction-{uuid4().hex}", name="Other")
        session.add(other)
        await session.flush()
    assert (
        await harness.client.post(
            url,
            headers={
                "Authorization": "Bearer " + harness.token([], super_admin=True),
                harness.settings.tenant_header: other.public_id,
            },
        )
    ).status_code == 404
    assert not any(adapter.contexts for adapter in adapters)


async def test_other_ordinary_account_cannot_review_a_foreign_transcript(meeting_harness):
    harness = meeting_harness
    _, _, url = await prepared(harness)
    adapters = wire(harness)
    async with harness.sessions() as session, session.begin():
        suffix = uuid4().hex
        tenant = Tenant(code=f"review-other-{suffix}", name="Other")
        session.add(tenant)
        await session.flush()
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=f"review-other-{suffix}",
            email=f"{suffix}@example.invalid",
            display_name="Other",
            password_hash="disabled-test-credential",
        )
        session.add(user)
        await session.flush()
    token = create_access_token(
        subject=UUID(user.public_id),
        username=user.username,
        tenant_id=UUID(tenant.public_id),
        roles=[],
        permissions=["meeting_analysis:read", "meeting_analysis:run"],
        is_super_admin=False,
    )
    response = await harness.client.post(
        url,
        headers={
            "Authorization": "Bearer " + token,
            harness.settings.tenant_header: tenant.public_id,
        },
    )
    assert response.status_code == 404, response.text
    assert not any(adapter.contexts for adapter in adapters)


@pytest.mark.parametrize(
    "change",
    ["text", "language", "speaker", "context", "delete_target", "delete_meeting", "status"],
)
async def test_concurrent_changes_discard_model_output(meeting_harness, change):
    harness = meeting_harness
    meeting_id, target_id, url = await prepared(harness)

    async def mutate():
        async with harness.sessions() as session, session.begin():
            meeting = await session.scalar(select(Meeting).where(Meeting.public_id == meeting_id))
            target = await session.scalar(
                select(MeetingTranscript).where(MeetingTranscript.public_id == target_id)
            )
            if change == "text":
                target.text = "Başka bir konuşma."
            elif change == "language":
                target.language = "en"
            elif change == "speaker":
                target.meeting_speaker_id = None
            elif change == "context":
                session.add(
                    MeetingTranscript(
                        tenant_id=meeting.tenant_id,
                        meeting_id=meeting.meeting_id,
                        ordinal=1,
                        start=3,
                        end=4,
                        text="Değişen bağlam.",
                        language="tr",
                    )
                )
            elif change == "delete_target":
                target.is_deleted = True
            elif change == "delete_meeting":
                meeting.is_deleted = True
            else:
                meeting.status = "failed"

    wire(harness, during=mutate)
    response = await harness.client.post(url)
    expected = 404 if change.startswith("delete") else 409
    assert response.status_code == expected, response.text
    assert response.json()["detail"]["code"] == (
        "not_found" if expected == 404 else "transcript_changed"
    )


@pytest.mark.parametrize("case", ["long", "unfinished", "missing_target", "foreign_meeting"])
async def test_invalid_target_is_rejected_before_inference(meeting_harness, case):
    harness = meeting_harness
    meeting_id, _, url = await prepared(
        harness, text="x" * 1025 if case == "long" else "Yeni sürüyü yükledik."
    )
    adapters = wire(harness)
    if case == "unfinished":
        async with harness.sessions() as session, session.begin():
            meeting = await session.scalar(select(Meeting).where(Meeting.public_id == meeting_id))
            meeting.status = "running"
    elif case == "missing_target":
        url = f"/meetings/{meeting_id}/transcript/{uuid4()}/correction-preview"
    elif case == "foreign_meeting":
        other = await workflow.create(harness.client, workflow.source_bytes(), auto_enroll=False)
        url = url.replace(meeting_id, other["public_id"])
    response = await harness.client.post(url)
    expected = {"long": 422, "unfinished": 409, "missing_target": 404, "foreign_meeting": 404}[case]
    assert response.status_code == expected, response.text
    assert not any(adapter.contexts for adapter in adapters)


async def test_context_budget_uses_nearest_whole_rows_in_source_order(meeting_harness):
    harness = meeting_harness
    meeting_id, target_id, url = await prepared(harness)
    async with harness.sessions() as session, session.begin():
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == meeting_id))
        target = await session.scalar(
            select(MeetingTranscript).where(MeetingTranscript.public_id == target_id)
        )
        target.ordinal = 10
        for ordinal in [5, 6, 7, 8, 9, 11, 12, 13, 14, 15]:
            session.add(
                MeetingTranscript(
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.meeting_id,
                    ordinal=ordinal,
                    start=ordinal,
                    end=ordinal + 1,
                    text=f"{ordinal}: " + "a" * 1000,
                    language="tr",
                )
            )
    adapters = wire(harness)
    response = await harness.client.post(url)
    assert response.status_code == 200, response.text
    context = adapters[0].contexts[0]
    assert [text.split(":", 1)[0] for text in context.before] == ["8", "9"]
    assert [text.split(":", 1)[0] for text in context.after] == ["11"]
    assert len(context.target_text) + sum(map(len, context.before + context.after)) <= 4000


@pytest.mark.parametrize("change", ["revoked", "user", "tenant"])
async def test_current_authorization_is_replayed_after_inference(meeting_harness, change):
    harness = meeting_harness
    _, _, url = await prepared(harness)

    async def mutate():
        async with harness.sessions() as session, session.begin():
            if change == "revoked":
                for role in await session.scalars(
                    select(UserRole).where(UserRole.user_id == harness.user.user_id)
                ):
                    role.is_deleted = True
            elif change == "user":
                user = await session.get(User, harness.user.user_id)
                user.is_active = False
            else:
                tenant = await session.get(Tenant, harness.tenant.tenant_id)
                tenant.is_active = False

    wire(harness, during=mutate)
    response = await harness.client.post(url)
    assert response.status_code == (403 if change == "revoked" else 404), response.text
    assert set(response.json()) == {"detail"}


async def test_request_body_cannot_replace_server_owned_context(meeting_harness):
    harness = meeting_harness
    _, _, url = await prepared(harness)
    adapters = wire(harness)
    response = await harness.client.post(
        url, json={"text": "untrusted replacement", "model": "remote", "url": "http://elsewhere"}
    )
    assert response.status_code == 200, response.text
    assert adapters[0].contexts[0].target_text == "Yeni sürüyü sunucuya yükledik."
    assert response.json()["model_name"] == "qwen3.5:27b"


async def test_real_di_wires_disabled_provider_without_network_or_source_mutation(meeting_harness):
    harness = meeting_harness
    _, _, url = await prepared(harness)
    before = await preview.snapshot(harness)
    app.dependency_overrides[get_settings] = lambda: harness.settings.model_copy(
        update={"text_review_enabled": False}
    )
    response = await harness.client.post(url)
    assert response.status_code == 503, response.text
    assert response.json()["detail"]["code"] == "text_review_unavailable"
    assert await preview.snapshot(harness) == before
