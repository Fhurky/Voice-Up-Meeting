"""Native exclusions survive actual source chunks, memory fencing and lifecycle."""

import math
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.domain.meeting_native_exclusions import check_exclusion_graph, link_native_peers
from app.domain.models.meeting import Meeting, MeetingChunk, MeetingSpeaker
from app.domain.models.speaker_identity import SpeakerProfile, SpeakerSample
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.services.meeting_chunks import MeetingChunkPersistence
from app.services.meeting_cleanup import MeetingCleanup
from app.services.meeting_memory_ports import MeetingMemoryResult, MemoryContext
from app.services.meeting_ports import MeetingChunkResult, MeetingTracking
from app.services.speaker_ports import SpeakerError
from tests.integration import test_meeting_repository as database_fixtures
from tests.integration import test_meeting_workflow as workflow_fixtures
from tests.integration.test_meeting_centroid import create_meeting, observed, vector
from tests.integration.test_meeting_context_memory import (
    ContextProvider,
    prepare_contexts,
    resolver,
)
from tests.integration.test_meeting_memory import profile_count
from tests.integration.test_meeting_worker import Provider, queued, worker

meeting_db = database_fixtures.meeting_db
migrated_meeting_database = database_fixtures.migrated_meeting_database
meeting_harness = workflow_fixtures.meeting_harness
pytestmark = pytest.mark.integration


def native_pair(*, absent=False, same=False, angles=(0, 56), turns=None):
    body = observed(12, 0).model_dump(mode="json")
    tracks = []
    for index, label in enumerate(["native-a", "native-b"]):
        track = deepcopy(body["tracks"][0])
        ranges = [{"start": index * 6, "end": (index + 1) * 6}]
        if turns is not None:
            ranges = [
                {"start": turn["start"], "end": turn["end"]}
                for turn in turns
                if turn["speaker"] == label
            ]
        seconds = sum(span["end"] - span["start"] for span in ranges)
        track.update(
            speaker=label,
            embedding=vector(0 if index == 0 or same else 65, 192),
            validated_ranges=ranges,
            validated_seconds=seconds,
            used_seconds=seconds,
            windows_count=math.ceil(seconds / 8),
        )
        track["tracking"]["embedding"] = vector(angles[index], 256)
        if index and absent:
            track.update(
                status="inconsistent_audio",
                embedding=None,
                validated_ranges=[],
                validated_seconds=0,
            )
        tracks.append(track)
    body.update(
        tracks=tracks,
        words=[],
        segments=[],
        turns=turns
        or [
            {"start": 0, "end": 6, "speaker": "native-a"},
            {"start": 6, "end": 12, "speaker": "native-b"},
        ],
    )
    body["exclusive_turns"] = body["turns"]
    return MeetingChunkResult.model_validate(body)


async def persist_chunk(db, meeting_id, window, result):
    async with db.sessions() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        await MeetingChunkPersistence(Settings()).persist(
            MeetingRepository(session), meeting, window, result
        )


async def rows(harness, meeting_id):
    async with harness.sessions() as session:
        return list(
            await session.scalars(
                select(MeetingSpeaker)
                .where(MeetingSpeaker.meeting_id == meeting_id)
                .order_by(MeetingSpeaker.ordinal)
            )
        )


@pytest.mark.parametrize(
    ("absent", "same", "count"), [(False, False, 2), (True, False, 1), (False, True, 1)]
)
async def test_only_independent_different_voice_evidence_prevents_native_merge(
    meeting_db, absent, same, count
):
    db = meeting_db
    meeting_id = await create_meeting(db, 12)
    await persist_chunk(db, meeting_id, (0, 0, 0, 12, 12), native_pair(absent=absent, same=same))
    values = await rows(db, meeting_id)
    assert len(values) == count
    if count == 2:
        graph = check_exclusion_graph(
            [(row.meeting_speaker_id, row.props["native_exclusions"]) for row in values], "a" * 64
        )
        for row in values:
            proof = graph[row.meeting_speaker_id].peers[0]
            assert proof.chunk_index == 0 and proof.similarity == pytest.approx(
                math.cos(math.radians(65))
            )
            assert proof.new_threshold == 0.45 and proof.labels == ("native-a", "native-b")
    else:
        assert "native_exclusions" not in values[0].props


async def test_shared_source_context_cannot_override_independent_native_exclusion(meeting_db):
    db = meeting_db
    meeting_id = await create_meeting(db, 12)
    await persist_chunk(db, meeting_id, (0, 0, 0, 6, 6), observed(6, 0))
    candidate = native_pair(
        turns=[
            {"start": 6, "end": 9, "speaker": "native-a"},
            {"start": 0, "end": 6, "speaker": "native-b"},
            {"start": 9, "end": 12, "speaker": "native-b"},
        ]
    )
    await persist_chunk(db, meeting_id, (1, 0, 6, 12, 12), candidate)
    values = await rows(db, meeting_id)
    assert len(values) == 2 and values[1].props["speech_ranges"] == [[9 * 16000, 12 * 16000]]
    assert all("native_exclusions" in row.props for row in values)


async def test_blocked_winner_does_not_force_a_weaker_eligible_runner_up(meeting_db):
    db = meeting_db
    meeting_id = await create_meeting(db, 24)
    await persist_chunk(db, meeting_id, (0, 0, 0, 12, 12), native_pair(same=True, angles=(0, 74)))
    previous = await rows(db, meeting_id)
    assert len(previous) == 2
    await persist_chunk(db, meeting_id, (1, 12, 12, 24, 24), native_pair(angles=(0, 25)))
    values = await rows(db, meeting_id)
    assert len(values) == 3
    assert values[1].props["speech_ranges"] == previous[1].props["speech_ranges"]
    assert values[2].props["speech_ranges"] == [[18 * 16000, 24 * 16000]]


async def test_repeated_native_proof_keeps_first_checkpoint_and_cross_chunk_identity(meeting_db):
    db = meeting_db
    meeting_id = await create_meeting(db, 24)
    candidate = native_pair(angles=(0, 90))
    await persist_chunk(db, meeting_id, (0, 0, 0, 12, 12), candidate)
    before = await rows(db, meeting_id)
    await persist_chunk(db, meeting_id, (1, 12, 12, 24, 24), candidate)
    after = await rows(db, meeting_id)
    assert len(after) == 2
    for original, current in zip(before, after, strict=True):
        assert original.meeting_speaker_id == current.meeting_speaker_id
        assert original.props["native_exclusions"] == current.props["native_exclusions"]
        assert current.speech_seconds == 12


async def test_mapped_context_only_native_preserves_separation_without_recounting(meeting_db):
    db = meeting_db
    meeting_id = await create_meeting(db, 18)
    await persist_chunk(db, meeting_id, (0, 0, 0, 12, 12), native_pair(same=True, angles=(0, 90)))
    original = await rows(db, meeting_id)
    assert len(original) == 2 and all("native_exclusions" not in row.props for row in original)
    body = native_pair(angles=(0, 90)).model_dump(mode="json")
    body["input_seconds"] = 18
    body["turns"] = body["exclusive_turns"] = [
        {"start": 12, "end": 18, "speaker": "native-a"},
        {"start": 0, "end": 6, "speaker": "native-b"},
    ]
    body["tracks"][0]["validated_ranges"] = [{"start": 12, "end": 18}]
    body["tracks"][1]["validated_ranges"] = [{"start": 0, "end": 6}]
    await persist_chunk(db, meeting_id, (1, 0, 12, 18, 18), MeetingChunkResult.model_validate(body))
    current = await rows(db, meeting_id)
    assert len(current) == 2 and all("native_exclusions" in row.props for row in current)
    assert current[0].speech_seconds == 12
    assert current[1].speech_seconds == original[1].speech_seconds == 6
    for key in ("speech_ranges", "tracking_seconds", "embedding_resultant", "tracking_resultant"):
        assert current[1].props[key] == original[1].props[key]
    assert list(current[1].embedding) == list(original[1].embedding)
    assert list(current[1].tracking_embedding) == list(original[1].tracking_embedding)
    assert current[1].props["native_exclusions"]["peers"][0]["chunk_index"] == 1


async def test_worker_fenced_checkpoint_retry_preserves_native_proof_and_public_privacy(
    meeting_harness,
):
    harness = meeting_harness
    public_id = await queued(harness, 12)
    provider = Provider()
    service = worker(harness, provider)
    claim = await service.claim()
    assert claim is not None
    assert await service.save_chunk(claim, native_pair())
    before = await rows(harness, claim.meeting_id)
    assert len(before) == 2
    assert not await service.save_chunk(claim, native_pair())
    after = await rows(harness, claim.meeting_id)
    assert [row.props for row in before] == [row.props for row in after]
    for _ in range(3):
        await worker(harness, provider).process_once()
    assert (await harness.client.get(f"/meetings/{public_id}")).json()["status"] == "succeeded"
    response = await harness.client.get(f"/meetings/{public_id}/speakers")
    assert response.status_code == 200 and len(response.json()["items"]) == 2
    assert "native_exclusions" not in response.text and "native-a" not in response.text
    assert await profile_count(harness) == 0


@pytest.mark.parametrize("damage", ["source", "null", "deleted", "foreign_tenant"])
async def test_chunk_reconciliation_rejects_invalid_peer_state_without_checkpoint(
    meeting_db, damage
):
    db = meeting_db
    meeting_id = await create_meeting(db, 24)
    await persist_chunk(db, meeting_id, (0, 0, 0, 12, 12), native_pair())
    async with db.sessions() as session, session.begin():
        values = list(
            await session.scalars(
                select(MeetingSpeaker)
                .where(MeetingSpeaker.meeting_id == meeting_id)
                .order_by(MeetingSpeaker.ordinal)
            )
        )
        record = deepcopy(values[0].props["native_exclusions"])
        if damage == "source":
            record["source_sha256"] = "f" * 64
        elif damage == "null":
            record = None
        elif damage == "deleted":
            values[1].is_deleted = True
            values[1].deleted_at = datetime.now(UTC)
        else:
            other_meeting = db.meeting(tenant_id=db.other.tenant_id)
            session.add(other_meeting)
            await session.flush()
            foreign = MeetingSpeaker(
                tenant_id=db.other.tenant_id,
                meeting_id=other_meeting.meeting_id,
                ordinal=0,
                speech_seconds=0,
                clean_ranges=[],
                props=deepcopy(values[1].props),
            )
            session.add(foreign)
            await session.flush()
            record["peers"][0]["meeting_speaker_id"] = foreign.meeting_speaker_id
            values[1].props = {
                key: value for key, value in values[1].props.items() if key != "native_exclusions"
            }
            # Both proof shapes are valid and reciprocal. Only owning scope excludes this peer.
            check_exclusion_graph(
                [
                    (values[0].meeting_speaker_id, record),
                    (foreign.meeting_speaker_id, foreign.props["native_exclusions"]),
                ],
                "a" * 64,
            )
        values[0].props = {**values[0].props, "native_exclusions": record}
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await persist_chunk(db, meeting_id, (1, 12, 12, 24, 24), observed(12, 0))
    async with db.sessions() as session:
        checkpoints = list(
            await session.scalars(select(MeetingChunk).where(MeetingChunk.meeting_id == meeting_id))
        )
        assert [checkpoint.index for checkpoint in checkpoints] == [0]


async def linked_contexts(harness):
    meeting_id, _ = await prepare_contexts(harness, [0, 1])
    async with harness.sessions() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        values = list(
            await session.scalars(
                select(MeetingSpeaker)
                .where(MeetingSpeaker.meeting_id == meeting_id)
                .order_by(MeetingSpeaker.ordinal)
            )
        )
        graph = {row.meeting_speaker_id: None for row in values}
        link_native_peers(
            graph,
            *graph,
            source_sha256=meeting.source_sha256,
            chunk_index=0,
            labels=("native-a", "native-b"),
            recipe=None,
            similarity=0.4,
            new_threshold=0.45,
        )
        for index, row in enumerate(values):
            row.props = {
                **row.props,
                "speech_ranges": [[index * 12 * 16000, (index + 1) * 12 * 16000]],
                "native_exclusions": graph[row.meeting_speaker_id].to_record(),
            }
    return meeting_id


class SameProfileProvider(ContextProvider):
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
        body["embedding192"] = vector(0, 192)
        body["memory_embedding"]["embedding"] = vector(0, 256)
        return MeetingMemoryResult.model_validate(body)


@pytest.mark.parametrize("overlap", [False, True])
async def test_same_profile_native_conflict_clears_both_links_and_keeps_sample_immutable(
    meeting_harness,
    overlap,
):
    harness = meeting_harness
    meeting_id = await linked_contexts(harness)
    if overlap:
        async with harness.sessions() as session, session.begin():
            for row in await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            ):
                row.props = {**row.props, "speech_ranges": [[0, 24 * 16000]]}
    service = resolver(harness, SameProfileProvider())
    assert await service.resolve_next(meeting_id, 1)
    async with harness.sessions() as session:
        sample = await session.scalar(
            select(SpeakerSample).where(SpeakerSample.tenant_id == harness.tenant.tenant_id)
        )
        before = (sample.source_sha256, list(sample.embedding))
    assert await service.resolve_next(meeting_id, 1)
    values = await rows(harness, meeting_id)
    assert all(
        row.profile_id is None
        and row.decision == "ambiguous"
        and row.reason == ("overlapping_identity_conflict" if overlap else "inconsistent_audio")
        for row in values
    )
    assert await profile_count(harness) == 1
    assert not await service.resolve_next(meeting_id, 1)
    assert await profile_count(harness) == 1
    async with harness.sessions() as session:
        after = await session.get(SpeakerSample, sample.speaker_sample_id)
        assert before == (after.source_sha256, list(after.embedding)) and not after.is_deleted
        profile = await session.get(SpeakerProfile, after.speaker_profile_id)
        assert not profile.is_deleted and profile.sample_count == 1
        meeting = await session.get(Meeting, meeting_id)
    response = await harness.client.get(f"/meetings/{meeting.public_id}/speakers")
    assert response.status_code == 200
    assert all(
        "native_exclusions" not in item and "props" not in item for item in response.json()["items"]
    )


@pytest.mark.parametrize("damage", ["dangling", "asymmetric", "null", "source", "deleted"])
async def test_invalid_or_cross_tenant_peer_provenance_fails_before_inference(
    meeting_harness, damage
):
    harness = meeting_harness
    meeting_id = await linked_contexts(harness)
    async with harness.sessions() as session, session.begin():
        values = list(
            await session.scalars(
                select(MeetingSpeaker)
                .where(MeetingSpeaker.meeting_id == meeting_id)
                .order_by(MeetingSpeaker.ordinal)
            )
        )
        record = deepcopy(values[0].props["native_exclusions"])
        if damage == "dangling":
            record["peers"][0]["meeting_speaker_id"] = 2**62
        if damage == "asymmetric":
            record["peers"][0]["similarity"] = 0.2
        if damage == "null":
            record = None
        if damage == "source":
            record["source_sha256"] = "f" * 64
        if damage == "deleted":
            values[1].is_deleted = True
            values[1].deleted_at = datetime.now(UTC)
        values[0].props = {**values[0].props, "native_exclusions": record}
    provider = SameProfileProvider()
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await resolver(harness, provider).resolve_next(meeting_id, 1)
    assert provider.calls == 0 and await profile_count(harness) == 0


async def test_changed_valid_peer_proof_during_inference_is_fenced_by_fingerprint(meeting_harness):
    harness = meeting_harness
    meeting_id = await linked_contexts(harness)

    class ChangedProof(SameProfileProvider):
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
            result = await super().verify(
                audio,
                contexts=contexts,
                target=target,
                competitors=competitors,
                job_public_id=job_public_id,
                tenant_public_id=tenant_public_id,
            )
            async with harness.sessions() as session, session.begin():
                for row in await session.scalars(
                    select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
                ):
                    record = deepcopy(row.props["native_exclusions"])
                    record["peers"][0]["similarity"] = 0.2
                    row.props = {**row.props, "native_exclusions": record}
            return result

    with pytest.raises(SpeakerError, match="model_mismatch"):
        await resolver(harness, ChangedProof()).resolve_next(meeting_id, 1)
    assert await profile_count(harness) == 0
    assert all(not row.props.get("memory_completed") for row in await rows(harness, meeting_id))


async def test_cleanup_removes_private_peer_graph_together(meeting_harness):
    harness = meeting_harness
    meeting_id = await linked_contexts(harness)
    service = resolver(harness, SameProfileProvider())
    async with harness.sessions() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        meeting.status = "succeeded"
        meeting.finished_at = datetime.now(UTC) - timedelta(days=31)
        meeting.source_expires_at = datetime.now(UTC) - timedelta(days=24)
        meeting.lease_expires_at = None
    assert await MeetingCleanup(harness.sessions, service.storage, harness.settings).run() == 1
    assert all(row.props == {} and row.is_deleted for row in await rows(harness, meeting_id))
