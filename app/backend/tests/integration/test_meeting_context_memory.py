"""Real HTTP/upload/files/PostgreSQL memory boundaries; fixture vectors are not model accuracy."""

import hashlib
import io
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import numpy as np
import pytest
import soundfile as sf
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.models.meeting import Meeting, MeetingSpeaker
from app.domain.models.speaker_identity import Recording, SpeakerJob, SpeakerProfile
from app.domain.models.tenant import Tenant
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.repositories.speaker_repository import SpeakerRepository
from app.services.meeting_memory import MeetingMemory
from app.services.meeting_memory_ports import (
    MEMORY_MODEL_ID,
    MEMORY_MODEL_REVISION,
    MeetingMemoryResult,
    MemoryContext,
)
from app.services.meeting_ports import MeetingTracking
from app.services.speaker_ports import SpeakerError
from tests.integration import test_meeting_workflow as fixture_module
from tests.integration.test_meeting_memory import EvidenceProvider, profile_count
from tests.integration.test_meeting_workflow import MeetingHarness, create, upload

meeting_harness = fixture_module.meeting_harness
pytestmark = pytest.mark.integration


def vector(identity: int, dimensions: int) -> list[float]:
    return [float(index == identity) for index in range(dimensions)]


class ContextProvider:
    def __init__(self) -> None:
        self.status = "usable"
        self.tamper = ""
        self.calls = 0

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
        self.calls += 1
        info = sf.info(io.BytesIO(audio))
        identity = target.embedding.index(1.0)
        usable = self.status == "usable"
        ranges = [span.model_dump() for context in contexts for span in context.voiced_ranges]
        with sf.SoundFile(io.BytesIO(audio)) as source:
            pieces = []
            for span in ranges:
                source.seek(span["start"])
                pieces.append(source.read(span["end"] - span["start"], dtype="int16"))
        retained = io.BytesIO()
        sf.write(retained, np.concatenate(pieces), info.samplerate, format="WAV", subtype="PCM_16")
        body = {
            "ecapa_model_id": MODEL_ID,
            "ecapa_model_revision": MODEL_REVISION,
            "input_sha256": hashlib.sha256(audio).hexdigest(),
            "retained_sha256": hashlib.sha256(retained.getvalue()).hexdigest() if usable else None,
            "input_frames": info.frames,
            "sample_rate": info.samplerate,
            "quality_version": "meeting-natural-context-v1",
            "status": self.status,
            "accepted_context_indices": list(range(len(contexts))) if usable else [],
            "validated_ranges": ranges if usable else [],
            "validated_seconds": (
                sum(span["end"] - span["start"] for span in ranges) / info.samplerate
                if usable
                else 0.0
            ),
            "windows_count": len(contexts) if usable else 0,
            "device": "cpu",
            "embedding192": vector(identity, 192) if usable else None,
            "memory_embedding": target.model_dump() if usable else None,
        }
        if self.tamper == "retained_hash":
            body["retained_sha256"] = "0" * 64
        if self.tamper == "input_hash":
            body["input_sha256"] = "0" * 64
        if self.tamper == "outside_voice":
            body["validated_ranges"][0]["start"] = 0
            body["validated_seconds"] += 1.0
        return MeetingMemoryResult.model_validate(body)


async def prepare_contexts(
    harness: MeetingHarness,
    identities: list[int],
    *,
    seconds: int = 24,
    replay: bool = False,
    auto_enroll: bool = True,
    gap: bool = False,
    rate: int = 16000,
) -> tuple[int, list[str]]:
    sizes = (
        [8, 8, seconds - 16]
        if seconds >= 19
        else ([seconds // 2, seconds - seconds // 2] if seconds > 8 else [seconds])
    )
    values = []
    contexts = []
    cursor = 0
    for number, size in enumerate(sizes):
        values.append(np.full(size * rate, 1000 if replay else (number + 1) * 1000, dtype=np.int16))
        contexts.append(
            {
                "start": cursor,
                "end": cursor + size * rate,
                "voiced_ranges": [[cursor + (rate if gap else 0), cursor + size * rate]],
            }
        )
        cursor += size * rate
    stream = io.BytesIO()
    sf.write(stream, np.concatenate(values), rate, format="WAV", subtype="PCM_16")
    data = stream.getvalue()
    meeting = await create(harness.client, data, auto_enroll=auto_enroll)
    assert (await upload(harness.client, meeting, data)).status_code == 200
    assert (
        await harness.client.post(f"/meetings/{meeting['public_id']}/complete")
    ).status_code == 202
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        row.status, row.claim_token = "finalizing", 1
        row.lease_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        tracks = []
        for ordinal, identity in enumerate(identities):
            track = MeetingSpeaker(
                tenant_id=row.tenant_id,
                meeting_id=row.meeting_id,
                ordinal=ordinal,
                reason="inconsistent_audio",
                speech_seconds=0,
                clean_ranges=[],
                source_sha256=row.source_sha256,
                tracking_embedding=vector(identity, 256),
                tracking_model_id=MEMORY_MODEL_ID,
                tracking_model_revision=MEMORY_MODEL_REVISION,
                props={
                    "candidate_contexts": contexts,
                    "candidate_version": "meeting-natural-context-v1",
                    "speech_ranges": [[0, cursor]],
                },
            )
            session.add(track)
            await session.flush()
            tracks.append(track.public_id)
        return row.meeting_id, tracks


def resolver(harness: MeetingHarness, provider: ContextProvider) -> MeetingMemory:
    return MeetingMemory(
        harness.sessions,
        MeetingAudioStorage(harness.settings.audio_storage_path / "meetings"),
        AudioStorage(harness.settings),
        EvidenceProvider(),
        harness.settings,
        provider,
    )


async def test_context_memory_five_return_short_sixth_and_new_sixth(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    memory = resolver(harness, provider)
    first_ids = []
    for identities, seconds, total in [
        ([0, 1, 2, 3, 4], 24, 5),
        ([0, 1, 2, 3, 4], 12, 5),
        ([5], 20, 5),
        ([5], 24, 6),
    ]:
        meeting_id, tracks = await prepare_contexts(harness, identities, seconds=seconds)
        for _ in tracks:
            assert await memory.resolve_next(meeting_id, 1)
        assert not await memory.resolve_next(meeting_id, 1)
        assert await profile_count(harness) == total
        async with harness.sessions() as session:
            rows = list(
                await session.scalars(
                    select(MeetingSpeaker)
                    .where(MeetingSpeaker.meeting_id == meeting_id)
                    .order_by(MeetingSpeaker.ordinal)
                )
            )
            ids = [row.profile_id for row in rows]
            if not first_ids:
                first_ids = ids
            elif len(ids) == 5:
                assert ids == first_ids
            elif seconds == 20:
                assert ids == [None]
            profiles = list(
                await session.scalars(
                    select(SpeakerProfile).where(
                        SpeakerProfile.tenant_id == harness.tenant.tenant_id
                    )
                )
            )
            assert all(
                profile.sample_count == 1 and profile.meeting_embedding is not None
                for profile in profiles
            )
            for profile in profiles:
                recording = await session.get(Recording, profile.meeting_recording_id)
                assert recording.sha256 == profile.meeting_source_sha256
            jobs = list(
                await session.scalars(
                    select(SpeakerJob).where(SpeakerJob.tenant_id == harness.tenant.tenant_id)
                )
            )
            assert all(
                job.result["preprocessing_version"] == "meeting-natural-context-v1" for job in jobs
            )


@pytest.mark.parametrize("kind", ["replay", "disabled", "rejected", "two_contexts"])
async def test_context_quality_cannot_bypass_enrollment_gates(
    meeting_harness: MeetingHarness, kind: str
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(
        harness, [0], replay=kind == "replay", auto_enroll=kind != "disabled"
    )
    if kind == "rejected":
        provider.status = "inconsistent_audio"
    if kind == "two_contexts":
        async with harness.sessions() as session, session.begin():
            track = await session.scalar(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
            track.props = {
                **track.props,
                "candidate_contexts": track.props["candidate_contexts"][:2],
            }
    assert await resolver(harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(harness) == 0


@pytest.mark.parametrize("rate", [8000, 44100])
async def test_native_context_frame_mapping_and_retained_hash(
    meeting_harness: MeetingHarness, rate: int
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, tracks = await prepare_contexts(harness, [0], rate=rate)
    assert await resolver(harness, provider).resolve_next(meeting_id, 1)
    async with harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == tracks[0])
        )
        assert track.clean_ranges == [[0, 24 * rate]] and track.speech_seconds == 24
        profile = await session.get(SpeakerProfile, track.profile_id)
        recording = await session.get(Recording, profile.meeting_recording_id)
        with sf.SoundFile(harness.settings.audio_storage_path / recording.storage_key) as stored:
            assert stored.samplerate == rate and stored.frames == 24 * rate


@pytest.mark.parametrize("tamper", ["retained_hash", "input_hash", "outside_voice"])
async def test_context_provider_source_tampering_writes_nothing(
    meeting_harness: MeetingHarness, tamper: str
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(harness, [0], gap=tamper == "outside_voice")
    provider.tamper = tamper
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await resolver(harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(harness) == 0


async def test_profile_meeting_population_requires_complete_metadata(
    meeting_harness: MeetingHarness,
) -> None:
    harness = meeting_harness
    async with harness.sessions() as session, session.begin():
        session.add(
            SpeakerProfile(
                tenant_id=harness.tenant.tenant_id,
                name="Invalid partial population",
                sample_count=1,
                model_id=MODEL_ID,
                model_revision=MODEL_REVISION,
                embedding=vector(0, 192),
                source_sha256="a" * 64,
                meeting_embedding=vector(0, 256),
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.parametrize("version", [None, "unsupported-context-v2"])
async def test_candidate_checkpoint_version_is_not_silently_reinterpreted(
    meeting_harness: MeetingHarness, version: str | None
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(harness, [0])
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        row.props = {**row.props, "candidate_version": version}
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await resolver(harness, provider).resolve_next(meeting_id, 1)
    assert provider.calls == 0 and await profile_count(harness) == 0


async def test_legacy_profile_is_recognized_without_backfill(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    async with harness.sessions() as session, session.begin():
        profile = SpeakerProfile(
            tenant_id=harness.tenant.tenant_id,
            name="Existing person",
            sample_count=1,
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            embedding=vector(0, 192),
            source_sha256="a" * 64,
        )
        session.add(profile)
        await session.flush()
        profile_id = profile.speaker_profile_id
    meeting_id, tracks = await prepare_contexts(harness, [0], seconds=12)
    assert await resolver(harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(harness) == 1
    async with harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == tracks[0])
        )
        assert track.decision == "recognized" and track.profile_id == profile_id
        profile = await session.get(SpeakerProfile, profile_id)
        assert profile.meeting_embedding is None and profile.sample_count == 1


async def test_context_rejection_clears_unaccepted_legacy_clean_count(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, tracks = await prepare_contexts(harness, [0])
    async with harness.sessions() as session, session.begin():
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == tracks[0])
        )
        track.clean_ranges, track.speech_seconds = [[0, 24 * 16000]], 24
    provider.status = "inconsistent_audio"
    assert await resolver(harness, provider).resolve_next(meeting_id, 1)
    async with harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == tracks[0])
        )
        assert track.speech_seconds == 0 and track.clean_ranges == []
        assert track.reason == "inconsistent_audio" and track.profile_id is None


async def test_conflicting_populations_abstain_without_duplicate(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    first, _ = await prepare_contexts(harness, [0, 1])
    memory = resolver(harness, provider)
    assert await memory.resolve_next(first, 1)
    assert await memory.resolve_next(first, 1)

    class ConflictingProvider(ContextProvider):
        async def verify(
            self, audio: bytes, *, contexts, target, competitors, job_public_id, tenant_public_id
        ):
            result = await super().verify(
                audio,
                contexts=contexts,
                target=target,
                competitors=competitors,
                job_public_id=job_public_id,
                tenant_public_id=tenant_public_id,
            )
            return result.model_copy(update={"embedding192": vector(1, 192)})

    second, tracks = await prepare_contexts(harness, [0])
    assert await resolver(harness, ConflictingProvider()).resolve_next(second, 1)
    assert await profile_count(harness) == 2
    async with harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == tracks[0])
        )
        assert track.decision == "ambiguous" and track.profile_id is None


async def test_meeting_population_ranking_is_tenant_lifecycle_and_model_scoped(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(harness, [0])
    assert await resolver(harness, provider).resolve_next(meeting_id, 1)
    async with harness.sessions() as session, session.begin():
        profile = await session.scalar(
            select(SpeakerProfile).where(SpeakerProfile.tenant_id == harness.tenant.tenant_id)
        )
        repository = SpeakerRepository(session)
        assert [
            row.speaker_profile_id
            for row, _ in await repository.ranked_meeting(harness.tenant.tenant_id, vector(0, 256))
        ] == [profile.speaker_profile_id]
        other = Tenant(code=f"context-other-{uuid4().hex}", name="Other tenant")
        session.add(other)
        await session.flush()
        assert await repository.ranked_meeting(other.tenant_id, vector(0, 256)) == []
        profile.is_deleted = True
        await session.flush()
        assert await repository.ranked_meeting(harness.tenant.tenant_id, vector(0, 256)) == []
        profile.is_deleted = False
        profile.meeting_model_revision = "different-revision"
        await session.flush()
        assert await repository.ranked_meeting(harness.tenant.tenant_id, vector(0, 256)) == []
        profile.meeting_model_revision = MEMORY_MODEL_REVISION
        profile.meeting_source_sha256 = "f" * 64
        await session.flush()
        assert await repository.ranked_meeting(harness.tenant.tenant_id, vector(0, 256)) == []


async def test_meeting_population_recording_reference_cannot_cross_tenant(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, ContextProvider()
    meeting_id, _ = await prepare_contexts(harness, [0])
    assert await resolver(harness, provider).resolve_next(meeting_id, 1)
    async with harness.sessions() as session, session.begin():
        first = await session.scalar(
            select(SpeakerProfile).where(SpeakerProfile.tenant_id == harness.tenant.tenant_id)
        )
        other = Tenant(code=f"context-fk-{uuid4().hex}", name="Other tenant")
        session.add(other)
        await session.flush()
        session.add(
            SpeakerProfile(
                tenant_id=other.tenant_id,
                name="Invalid foreign source",
                sample_count=1,
                model_id=MODEL_ID,
                model_revision=MODEL_REVISION,
                embedding=vector(1, 192),
                source_sha256="a" * 64,
                meeting_embedding=vector(1, 256),
                meeting_model_id=MEMORY_MODEL_ID,
                meeting_model_revision=MEMORY_MODEL_REVISION,
                meeting_preprocessing_version="meeting-natural-context-v1",
                meeting_source_sha256=first.meeting_source_sha256,
                meeting_recording_id=first.meeting_recording_id,
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.parametrize("mutation", ["lease", "candidates", "permission"])
async def test_context_evidence_rechecks_live_fence_and_owner(
    meeting_harness: MeetingHarness, mutation: str
) -> None:
    harness = meeting_harness
    meeting_id, _ = await prepare_contexts(harness, [0])

    class MutatingProvider(ContextProvider):
        async def verify(
            self, audio: bytes, *, contexts, target, competitors, job_public_id, tenant_public_id
        ):
            result = await super().verify(
                audio,
                contexts=contexts,
                target=target,
                competitors=competitors,
                job_public_id=job_public_id,
                tenant_public_id=tenant_public_id,
            )
            async with harness.sessions() as session, session.begin():
                meeting = await session.get(Meeting, meeting_id)
                if mutation == "lease":
                    meeting.claim_token += 1
                elif mutation == "permission":
                    from app.domain.models.role import UserRole

                    assignment = await session.scalar(
                        select(UserRole).where(UserRole.user_id == harness.user.user_id)
                    )
                    assignment.is_deleted = True
                else:
                    track = await session.scalar(
                        select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
                    )
                    track.props = {**track.props, "candidate_contexts": []}
            return result

    if mutation == "lease":
        assert not await resolver(harness, MutatingProvider()).resolve_next(meeting_id, 1)
    else:
        with pytest.raises(
            SpeakerError, match="forbidden" if mutation == "permission" else "model_mismatch"
        ):
            await resolver(harness, MutatingProvider()).resolve_next(meeting_id, 1)
    assert await profile_count(harness) == 0
