"""Saved corrections preserve source and enforce authorization at real PostgreSQL/HTTP boundaries."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.api.meetings.router import get_transcript_suggestion_service
from app.core.security import create_access_token
from app.domain.models.meeting import Meeting, MeetingTranscript
from app.domain.models.role import UserRole
from app.domain.models.speaker_identity import SpeakerProfile
from app.domain.models.tenant import Tenant
from app.domain.models.transcript_revision import MeetingTranscriptRevision
from app.domain.models.user import User
from app.infrastructure.correction_receipts import CorrectionReceiptSigner
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.infrastructure.repositories.transcript_revision_repository import (
    TranscriptRevisionRepository,
)
from app.main import app
from app.services.meeting_cleanup import MeetingCleanup
from app.services.transcript_correction_ports import (
    InstalledReviewModel,
    ModelSuggestionResult,
    TranscriptSuggestionPort,
)
from app.services.transcript_suggestions import TranscriptSuggestionService
from tests.integration import test_meeting_audio_preview as preview
from tests.integration import test_transcript_correction as legacy

meeting_harness = legacy.meeting_harness
pytestmark = pytest.mark.integration
DIGEST = "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
SELECTION = {"model_name": "qwen3.5:27b", "model_digest": DIGEST}


class LocalSuggestions(TranscriptSuggestionPort):
    def __init__(self, session, *, edits=None, raw=None, during=None):
        self.session, self.during = session, during
        self.raw = (
            raw
            if raw is not None
            else json.dumps(
                {
                    "edits": (
                        edits
                        if edits is not None
                        else [{"original": "sürüyü", "replacement": "sürümü"}]
                    )
                },
                ensure_ascii=False,
            )
        )
        self.calls = 0

    async def list_models(self):
        assert not self.session.in_transaction()
        return (InstalledReviewModel(SELECTION["model_name"], DIGEST, 100, True, None, True),)

    async def suggest(self, context, selection):
        assert not self.session.in_transaction()
        self.calls += 1
        if self.during:
            await self.during()
        return ModelSuggestionResult(self.raw, False, selection.name, selection.digest)


def wire(harness, **options):
    providers = []

    async def dependency():
        async with harness.sessions() as session:
            provider = LocalSuggestions(session, **options)
            providers.append(provider)
            try:
                yield TranscriptSuggestionService(
                    MeetingRepository(session),
                    TranscriptRevisionRepository(session),
                    provider,
                    CorrectionReceiptSigner(harness.settings),
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_transcript_suggestion_service] = dependency
    return providers


async def source(harness):
    meeting_id, target_id, _ = await legacy.prepared(harness)
    return meeting_id, target_id, f"/meetings/{meeting_id}/transcript/{target_id}"


async def suggest(harness, path):
    response = await harness.client.post(path + "/correction-suggestion", json=SELECTION)
    assert response.status_code == 200, response.text
    return response.json()


async def test_selected_suggestion_is_transient_and_explicit_save_survives_reload(meeting_harness):
    harness = meeting_harness
    meeting_id, _, path = await source(harness)
    wire(harness)
    original = await preview.snapshot(harness)
    proposal = await suggest(harness, path)
    assert proposal["status"] == "suggested" and proposal["save_token"]
    assert proposal["expected_revision"] == 0
    assert await preview.snapshot(harness) == original
    async with harness.sessions() as session:
        assert not list(
            await session.scalars(
                select(MeetingTranscriptRevision).where(
                    MeetingTranscriptRevision.tenant_id == harness.tenant.tenant_id
                )
            )
        )
    saved = await harness.client.post(
        path + "/corrections", json={"save_token": proposal["save_token"]}
    )
    assert saved.status_code == 200, saved.text
    result = saved.json()
    assert result["revision"] == 1 and result["corrected_text"] == "Yeni sürümü sunucuya yükledik."
    assert saved.headers["cache-control"] == "no-store"
    assert await preview.snapshot(harness) == original
    transcript = (await harness.client.get(f"/meetings/{meeting_id}/transcript")).json()["items"][0]
    assert transcript["text"] == "Yeni sürüyü sunucuya yükledik."
    assert transcript["correction"] == result
    repeated = await harness.client.post(
        path + "/corrections", json={"save_token": proposal["save_token"]}
    )
    assert repeated.json() == result


async def test_all_semantic_proposals_are_visible_and_user_can_save_them(meeting_harness):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(harness, edits=[{"original": "Yeni", "replacement": "Eski"}])
    proposal = await suggest(harness, path)
    assert proposal["proposals"][0]["assessment"] == "review_required"
    assert proposal["save_token"] is not None
    saved = await harness.client.post(
        path + "/corrections", json={"save_token": proposal["save_token"]}
    )
    assert saved.status_code == 200 and saved.json()["corrected_text"].startswith("Eski ")


async def test_unmapped_and_non_json_model_outputs_remain_visible_without_save_token(
    meeting_harness,
):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(harness, edits=[{"original": "missing", "replacement": "new"}])
    proposal = await suggest(harness, path)
    assert proposal["status"] == "unmapped" and proposal["save_token"] is None
    assert proposal["proposals"][0]["replacement"] == "new"
    wire(harness, raw="A plain model response with <b>markup</b>.")
    proposal = await suggest(harness, path)
    assert proposal["status"] == "invalid_output" and proposal["save_token"] is None
    assert proposal["model_output"] == "A plain model response with <b>markup</b>."


async def test_reverse_ordered_model_edits_save_and_reload_in_source_order(meeting_harness):
    harness = meeting_harness
    meeting_id, _, path = await source(harness)
    wire(
        harness,
        edits=[
            {"original": "yükledik", "replacement": "yükledim"},
            {"original": "sürüyü", "replacement": "sürümü"},
        ],
    )
    proposal = await suggest(harness, path)
    response = await harness.client.post(
        path + "/corrections", json={"save_token": proposal["save_token"]}
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert [edit["start_char"] for edit in saved["edits"]] == sorted(
        edit["start_char"] for edit in saved["edits"]
    )
    text, cursor = "", 0
    for edit in saved["edits"]:
        text += proposal["original_text"][cursor : edit["start_char"]] + edit["replacement"]
        cursor = edit["end_char"]
    text += proposal["original_text"][cursor:]
    assert text == saved["corrected_text"] == "Yeni sürümü sunucuya yükledim."
    row = (await harness.client.get(f"/meetings/{meeting_id}/transcript")).json()["items"][0]
    assert row["correction"] == saved


async def revisions(harness):
    async with harness.sessions() as session:
        return list(
            await session.scalars(
                select(MeetingTranscriptRevision)
                .where(MeetingTranscriptRevision.tenant_id == harness.tenant.tenant_id)
                .order_by(MeetingTranscriptRevision.revision)
            )
        )


async def test_stale_approval_conflicts_but_retry_returns_its_exact_prior_revision(meeting_harness):
    harness = meeting_harness
    meeting_id, _, path = await source(harness)
    wire(harness)
    first, competing = await suggest(harness, path), await suggest(harness, path)
    saved1 = (
        await harness.client.post(path + "/corrections", json={"save_token": first["save_token"]})
    ).json()
    stale = await harness.client.post(
        path + "/corrections", json={"save_token": competing["save_token"]}
    )
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "correction_conflict"
    second = await suggest(harness, path)
    assert second["expected_revision"] == 1 and second["original_text"] == first["original_text"]
    saved2 = (
        await harness.client.post(path + "/corrections", json={"save_token": second["save_token"]})
    ).json()
    assert saved2["revision"] == 2 and saved2["public_id"] != saved1["public_id"]
    repeated = await harness.client.post(
        path + "/corrections", json={"save_token": first["save_token"]}
    )
    assert repeated.json() == saved1
    current = (await harness.client.get(f"/meetings/{meeting_id}/transcript")).json()["items"][0]
    assert current["correction"] == saved2
    assert [row.revision for row in await revisions(harness)] == [1, 2]


@pytest.mark.parametrize("same_token", [False, True])
async def test_parallel_approvals_are_serialized_and_idempotent(meeting_harness, same_token):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(harness)
    first = await suggest(harness, path)
    second = first if same_token else await suggest(harness, path)
    responses = await asyncio.gather(
        *(
            harness.client.post(path + "/corrections", json={"save_token": value["save_token"]})
            for value in (first, second)
        )
    )
    assert sorted(response.status_code for response in responses) == (
        [200, 200] if same_token else [200, 409]
    )
    assert len(await revisions(harness)) == 1
    if same_token:
        assert responses[0].json() == responses[1].json()


async def test_model_list_and_mutations_require_both_permissions_but_saved_text_needs_only_read(
    meeting_harness,
):
    harness = meeting_harness
    meeting_id, _, path = await source(harness)
    providers = wire(harness)
    catalog = await harness.client.get("/meetings/review-models")
    assert catalog.status_code == 200 and catalog.headers["cache-control"] == "no-store"
    assert set(catalog.json()["items"][0]) == {
        "name",
        "digest",
        "size_bytes",
        "selectable",
        "unavailable_reason",
        "is_default",
    }
    proposal = await suggest(harness, path)
    assert (
        await harness.client.post(
            path + "/corrections", json={"save_token": proposal["save_token"]}
        )
    ).status_code == 200
    for permissions in [[], ["meeting_analysis:read"], ["meeting_analysis:run"]]:
        headers = {"Authorization": "Bearer " + harness.token(permissions)}
        assert (
            await harness.client.get("/meetings/review-models", headers=headers)
        ).status_code == 403
        assert (
            await harness.client.post(
                path + "/correction-suggestion", json=SELECTION, headers=headers
            )
        ).status_code == 403
        assert (
            await harness.client.post(
                path + "/corrections", json={"save_token": proposal["save_token"]}, headers=headers
            )
        ).status_code == 403
    reader = {"Authorization": "Bearer " + harness.token(["meeting_analysis:read"])}
    assert (await harness.client.get(f"/meetings/{meeting_id}/transcript", headers=reader)).json()[
        "items"
    ][0]["correction"]["revision"] == 1
    assert (
        await harness.client.get("/meetings/review-models", headers={"Authorization": ""})
    ).status_code == 401
    assert (
        await harness.client.get(
            "/meetings/review-models", headers={"Authorization": "Bearer " + proposal["save_token"]}
        )
    ).status_code == 401
    assert sum(provider.calls for provider in providers) == 1


@pytest.mark.parametrize("change", ["tamper", "expired", "foreign_source", "foreign_actor"])
async def test_invalid_approval_evidence_does_not_save(meeting_harness, change):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(harness)
    proposal = await suggest(harness, path)
    token = proposal["save_token"]
    if change == "tamper":
        token = token[:-1] + ("a" if token[-1] != "a" else "b")
    elif change == "expired":
        signer = CorrectionReceiptSigner(harness.settings)
        proof = signer.verify(token, now=datetime.now(UTC))
        token = signer.sign(
            proof.model_copy(
                update={"issued_at": proof.issued_at - 901, "expires_at": proof.expires_at - 901}
            )
        )
    elif change == "foreign_source":
        path = path.rsplit("/", 1)[0] + "/" + str(uuid4())
    else:
        signer = CorrectionReceiptSigner(harness.settings)
        proof = signer.verify(token, now=datetime.now(UTC))
        token = signer.sign(proof.model_copy(update={"actor_public_id": uuid4()}))
    response = await harness.client.post(path + "/corrections", json={"save_token": token})
    assert (
        response.status_code == 422
        and response.json()["detail"]["code"] == "invalid_correction_token"
    )
    assert await revisions(harness) == []


@pytest.mark.parametrize("change", ["text", "context", "delete", "permission"])
async def test_save_rechecks_source_lifecycle_context_and_current_permissions(
    meeting_harness, change
):
    harness = meeting_harness
    meeting_id, target_id, path = await source(harness)
    wire(harness)
    proposal = await suggest(harness, path)
    async with harness.sessions() as session, session.begin():
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == meeting_id))
        row = await session.scalar(
            select(MeetingTranscript).where(MeetingTranscript.public_id == target_id)
        )
        if change == "text":
            row.text = "A changed source."
        elif change == "context":
            session.add(
                MeetingTranscript(
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.meeting_id,
                    ordinal=1,
                    start=4,
                    end=5,
                    text="A new context.",
                    language="tr",
                )
            )
        elif change == "delete":
            meeting.is_deleted = True
            meeting.deleted_at, meeting.deleted_by = datetime.now(UTC), harness.user.user_id
        else:
            for role in await session.scalars(
                select(UserRole).where(UserRole.user_id == harness.user.user_id)
            ):
                role.is_deleted = True
    response = await harness.client.post(
        path + "/corrections", json={"save_token": proposal["save_token"]}
    )
    assert (
        response.status_code
        == {"text": 409, "context": 409, "delete": 404, "permission": 403}[change]
    )
    assert await revisions(harness) == []


async def test_other_ordinary_tenant_cannot_review_save_or_read_revision(meeting_harness):
    harness = meeting_harness
    meeting_id, _, path = await source(harness)
    wire(harness)
    proposal = await suggest(harness, path)
    assert (
        await harness.client.post(
            path + "/corrections", json={"save_token": proposal["save_token"]}
        )
    ).status_code == 200
    async with harness.sessions() as session, session.begin():
        suffix = uuid4().hex
        tenant = Tenant(code=f"revision-other-{suffix}", name="Other")
        session.add(tenant)
        await session.flush()
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=f"revision-other-{suffix}",
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
    headers = {"Authorization": "Bearer " + token, harness.settings.tenant_header: tenant.public_id}
    assert (
        await harness.client.post(path + "/correction-suggestion", json=SELECTION, headers=headers)
    ).status_code == 404
    assert (
        await harness.client.post(
            path + "/corrections", json={"save_token": proposal["save_token"]}, headers=headers
        )
    ).status_code == 422
    assert (
        await harness.client.get(f"/meetings/{meeting_id}/transcript", headers=headers)
    ).status_code == 404


@pytest.mark.parametrize("deletion", [False, True])
async def test_retention_scrubs_saved_payloads_with_source_without_touching_profiles(
    meeting_harness, deletion
):
    harness = meeting_harness
    meeting_id, _, path = await source(harness)
    wire(harness)
    proposal = await suggest(harness, path)
    assert (
        await harness.client.post(
            path + "/corrections", json={"save_token": proposal["save_token"]}
        )
    ).status_code == 200
    if deletion:
        assert (await harness.client.delete(f"/meetings/{meeting_id}")).status_code == 204
    else:
        async with harness.sessions() as session, session.begin():
            meeting = await session.scalar(select(Meeting).where(Meeting.public_id == meeting_id))
            meeting.finished_at = datetime.now(UTC) - timedelta(days=31)
    cleanup = MeetingCleanup(
        harness.sessions,
        MeetingAudioStorage(harness.settings.audio_storage_path / "meetings"),
        harness.settings,
    )
    assert await cleanup.run() >= 1
    saved = (await revisions(harness))[0]
    assert saved.is_deleted and saved.deleted_at is not None
    assert saved.deleted_by == (harness.user.user_id if deletion else None)
    assert saved.corrected_text == "" and saved.edits == [] and saved.props == {}
    assert saved.source_text_sha256 == saved.context_sha256 == ""
    assert (await harness.client.get(f"/meetings/{meeting_id}/transcript")).status_code == 404
    async with harness.sessions() as session:
        profiles = list(
            await session.scalars(
                select(SpeakerProfile).where(SpeakerProfile.tenant_id == harness.tenant.tenant_id)
            )
        )
    assert len(profiles) == 1 and not profiles[0].is_deleted


async def test_migrated_revision_table_has_lifecycle_descriptions_and_compound_integrity(
    meeting_harness,
):
    harness = meeting_harness
    async with harness.sessions() as session:
        connection = await session.connection()

        def schema(connection):
            inspector = inspect(connection)
            name = "meeting_transcript_revision"
            return (
                inspector.get_columns(name),
                inspector.get_table_comment(name),
                inspector.get_foreign_keys(name),
                inspector.get_indexes(name),
            )

        columns, comment, foreign_keys, indexes = await connection.run_sync(schema)
    assert {
        "props",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "is_deleted",
        "deleted_at",
        "deleted_by",
        "public_id",
    }.issubset({column["name"] for column in columns})
    assert comment["text"] and all(
        column["comment"]
        for column in columns
        if column["name"]
        in {"corrected_text", "edits", "source_text_sha256", "context_sha256", "policy_version"}
    )
    assert any(
        key["constrained_columns"] == ["tenant_id", "meeting_id", "meeting_transcript_id"]
        and key["referred_table"] == "meeting_transcript"
        for key in foreign_keys
    )
    assert any(
        index["name"] == "ix_transcript_revision_active_source"
        and "is_deleted" in str(index["dialect_options"]["postgresql_where"])
        for index in indexes
    )


@pytest.mark.parametrize(
    "invalid", ["foreign_source", "revision", "duplicate_preview", "text_limit", "edits_shape"]
)
async def test_real_database_rejects_invalid_revision_rows(meeting_harness, invalid):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(harness)
    proposal = await suggest(harness, path)
    assert (
        await harness.client.post(
            path + "/corrections", json={"save_token": proposal["save_token"]}
        )
    ).status_code == 200
    saved = (await revisions(harness))[0]
    values = {
        "tenant_id": saved.tenant_id,
        "meeting_id": saved.meeting_id,
        "meeting_transcript_id": saved.meeting_transcript_id,
        "revision": 2,
        "preview_id": str(uuid4()),
        "source_text_sha256": saved.source_text_sha256,
        "context_sha256": saved.context_sha256,
        "corrected_text": saved.corrected_text,
        "edits": saved.edits,
        "model_name": saved.model_name,
        "model_digest": saved.model_digest,
        "policy_version": saved.policy_version,
    }
    if invalid == "foreign_source":
        values["meeting_transcript_id"] = 9223372036854775807
    elif invalid == "revision":
        values["revision"] = 0
    elif invalid == "duplicate_preview":
        values["preview_id"] = saved.preview_id
    elif invalid == "text_limit":
        values["corrected_text"] = "x" * 1217
    else:
        values["edits"] = {}
    async with harness.sessions() as session:
        session.add(MeetingTranscriptRevision(**values))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()
    assert len(await revisions(harness)) == 1


@pytest.mark.parametrize("change", ["text", "deleted", "permission"])
async def test_source_and_permission_changes_during_model_call_discard_proposal(
    meeting_harness, change
):
    harness = meeting_harness
    meeting_id, target_id, path = await source(harness)

    async def mutate():
        async with harness.sessions() as session, session.begin():
            if change == "text":
                target = await session.scalar(
                    select(MeetingTranscript).where(MeetingTranscript.public_id == target_id)
                )
                target.text = "Changed source text."
            elif change == "deleted":
                meeting = await session.scalar(
                    select(Meeting).where(Meeting.public_id == meeting_id)
                )
                meeting.is_deleted, meeting.deleted_at, meeting.deleted_by = (
                    True,
                    datetime.now(UTC),
                    harness.user.user_id,
                )
            else:
                for role in await session.scalars(
                    select(UserRole).where(UserRole.user_id == harness.user.user_id)
                ):
                    role.is_deleted = True

    wire(harness, during=mutate)
    response = await harness.client.post(path + "/correction-suggestion", json=SELECTION)
    assert response.status_code == {"text": 409, "deleted": 404, "permission": 403}[change]
    assert set(response.json()) == {"detail"} and await revisions(harness) == []


async def test_approval_during_another_model_call_keeps_original_revision_bound(meeting_harness):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(harness)
    prior = await suggest(harness, path)

    async def save_prior():
        response = await harness.client.post(
            path + "/corrections", json={"save_token": prior["save_token"]}
        )
        assert response.status_code == 200

    wire(harness, during=save_prior)
    proposal = await suggest(harness, path)
    assert proposal["expected_revision"] == 0 and proposal["save_token"]
    response = await harness.client.post(
        path + "/corrections", json={"save_token": proposal["save_token"]}
    )
    assert (
        response.status_code == 409 and response.json()["detail"]["code"] == "correction_conflict"
    )


@pytest.mark.parametrize("count", [1, 64])
async def test_malformed_unicode_model_proposal_is_visible_as_escaped_text(meeting_harness, count):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(
        harness,
        raw=json.dumps({"edits": [{"original": "sürüyü", "replacement": "\ud800" * count}]}),
    )
    proposal = await suggest(harness, path)
    assert proposal["status"] == "unmapped" and proposal["save_token"] is None
    assert proposal["proposals"][0]["replacement"] == ("\\ud800" * count)[:64]
    assert "\\ud800" in proposal["model_output"]


async def test_invalid_raw_unicode_model_text_is_bounded_and_visible(meeting_harness):
    harness = meeting_harness
    _, _, path = await source(harness)
    wire(harness, raw="\ud800" * 2000)
    proposal = await suggest(harness, path)
    assert proposal["status"] == "invalid_output" and proposal["save_token"] is None
    assert proposal["model_output"] == ("\\ud800" * 2000)[:8192]
    assert proposal["model_output_truncated"] is True
