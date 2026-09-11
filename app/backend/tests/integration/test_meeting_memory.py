"""Profile memory transactions use real PostgreSQL/files; fixture vectors are not accuracy evidence."""

import asyncio
import io
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
import soundfile as sf
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.meeting import Meeting, MeetingSpeaker
from app.domain.models.role import UserRole
from app.domain.models.speaker_identity import Recording, SpeakerJob, SpeakerProfile, SpeakerSample
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.schemas.speaker_identity import SpeakerResult
from app.services.meeting_memory import MeetingMemory
from app.services.speaker_ports import EmbeddingResult, SpeakerError
from tests.integration import test_meeting_workflow as fixture_module
from tests.integration.test_meeting_workflow import MeetingHarness, create, source_bytes, upload

meeting_harness = fixture_module.meeting_harness

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("during_inference", [False, True])
async def test_revoked_owner_permission_stops_memory_writes(
    meeting_harness: MeetingHarness, during_inference: bool
) -> None:
    harness = meeting_harness

    async def revoke() -> None:
        async with harness.sessions() as session, session.begin():
            assignment = await session.scalar(
                select(UserRole).where(UserRole.user_id == harness.user.user_id)
            )
            assignment.is_deleted = True

    class RevokingProvider(EvidenceProvider):
        async def embed(
            self, audio: bytes, *, purpose, job_public_id: str, tenant_public_id: str
        ) -> EmbeddingResult:
            result = await super().embed(
                audio,
                purpose=purpose,
                job_public_id=job_public_id,
                tenant_public_id=tenant_public_id,
            )
            if during_inference:
                await revoke()
            return result

    provider = RevokingProvider()
    meeting_id, _ = await prepare(harness, provider, [0])
    if not during_inference:
        await revoke()
    with pytest.raises(SpeakerError, match="forbidden"):
        await memory(harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(harness) == 0


class EvidenceProvider:
    def __init__(self):
        self.vectors: dict[str, list[float]] = {}
        self.error: SpeakerError | None = None
        self.calls = 0

    async def embed(
        self, audio: bytes, *, purpose, job_public_id: str, tenant_public_id: str
    ) -> EmbeddingResult:
        assert audio[:4] == b"RIFF" and purpose in {"identify", "enroll"}
        self.calls += 1
        if self.error:
            raise self.error
        with sf.SoundFile(io.BytesIO(audio)) as source:
            seconds = source.frames / source.samplerate
        return EmbeddingResult(
            self.vectors[job_public_id], min(21.0, seconds), 3, MODEL_ID, MODEL_REVISION, "cpu"
        )


async def prepare(
    harness: MeetingHarness,
    provider: EvidenceProvider,
    identities: list[int],
    seconds: float = 21.0,
) -> tuple[int, list[str]]:
    data = source_bytes(seconds + 1)
    meeting = await create(harness.client, data)
    assert (await upload(harness.client, meeting, data)).status_code == 200
    assert (
        await harness.client.post(f"/meetings/{meeting['public_id']}/complete")
    ).status_code == 202
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        row.status = "finalizing"
        row.claim_token = 1
        row.lease_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        tracks = []
        for ordinal, identity in enumerate(identities):
            vector = [float(index == identity) for index in range(192)]
            track = MeetingSpeaker(
                tenant_id=row.tenant_id,
                meeting_id=row.meeting_id,
                ordinal=ordinal,
                reason="no_profiles",
                speech_seconds=seconds,
                embedding=vector,
                model_id=MODEL_ID,
                model_revision=MODEL_REVISION,
                source_sha256=row.source_sha256,
                clean_ranges=[[0, round(seconds * 16000)]],
            )
            session.add(track)
            await session.flush()
            tracks.append(track.public_id)
            provider.vectors[track.public_id] = vector
        return row.meeting_id, tracks


def memory(harness: MeetingHarness, provider: EvidenceProvider) -> MeetingMemory:
    return MeetingMemory(
        harness.sessions,
        MeetingAudioStorage(harness.settings.audio_storage_path / "meetings"),
        AudioStorage(harness.settings),
        provider,
        harness.settings,
    )


async def profile_count(harness: MeetingHarness) -> int:
    async with harness.sessions() as session:
        return await session.scalar(
            select(func.count())
            .select_from(SpeakerProfile)
            .where(SpeakerProfile.tenant_id == harness.tenant.tenant_id)
        )


async def test_inconsistent_track_keeps_its_reason_when_no_memory_sample_is_eligible(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, EvidenceProvider()
    meeting_id, tracks = await prepare(harness, provider, [0])
    async with harness.sessions() as session, session.begin():
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == tracks[0])
        )
        track.reason = "inconsistent_audio"
        track.embedding = None
        track.clean_ranges = []
        track.speech_seconds = 0
    assert await memory(harness, provider).resolve_next(meeting_id, 1)
    assert provider.calls == 0
    assert await profile_count(harness) == 0
    async with harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.public_id == tracks[0])
        )
        assert track.decision == "profile_pending"
        assert track.reason == "inconsistent_audio"


async def test_five_return_and_sixth_new_are_idempotent_memory_transactions(
    meeting_harness: MeetingHarness,
) -> None:
    harness, provider = meeting_harness, EvidenceProvider()
    resolver = memory(harness, provider)
    first_ids = []
    for identities, expected_total in [
        ([0, 1, 2, 3, 4], 5),
        ([0, 1, 2, 3, 4], 5),
        ([0, 1, 2, 3, 4, 5], 6),
    ]:
        meeting_id, tracks = await prepare(harness, provider, identities)
        for _ in tracks:
            assert await resolver.resolve_next(meeting_id, 1)
        assert not await resolver.resolve_next(meeting_id, 1)
        assert await profile_count(harness) == expected_total
        async with harness.sessions() as session:
            rows = list(
                await session.scalars(
                    select(MeetingSpeaker)
                    .where(MeetingSpeaker.meeting_id == meeting_id)
                    .order_by(MeetingSpeaker.ordinal)
                )
            )
            ids = [row.profile_id for row in rows]
            assert all(value is not None for value in ids)
            if not first_ids:
                first_ids = ids
            else:
                assert ids[:5] == first_ids
    async with harness.sessions() as session:
        for model in (SpeakerJob, SpeakerSample, Recording):
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.tenant_id == harness.tenant.tenant_id)
                )
                == 6
            )
    assert all(
        path.stat().st_size < 800000 for path in harness.settings.audio_storage_path.glob("*.audio")
    )


@pytest.mark.parametrize("seconds,expected", [(19.999, 0), (20, 0), (20.001, 1)])
async def test_strict_twenty_second_boundary(
    meeting_harness: MeetingHarness, seconds: float, expected: int
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0], seconds)
    assert await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == expected


async def test_quality_failure_and_stale_claim_never_enroll(
    meeting_harness: MeetingHarness,
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0], 30)
    resolver = memory(meeting_harness, provider)
    assert not await resolver.resolve_next(meeting_id, 0)
    assert provider.calls == 0
    provider.error = SpeakerError("inconsistent_audio", 422)
    assert await resolver.resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 0
    async with meeting_harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        assert track.decision == "profile_pending" and track.reason == "inconsistent_audio"


async def test_inference_outage_is_retryable_not_a_completed_pending_person(
    meeting_harness: MeetingHarness,
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    provider.error = SpeakerError("inference_unavailable", 503)
    with pytest.raises(SpeakerError, match="inference_unavailable"):
        await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 0
    provider.error = None
    assert await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 1


async def test_enrollment_job_has_valid_public_success_trace(
    meeting_harness: MeetingHarness,
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    assert await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    async with meeting_harness.sessions() as session:
        job = await session.scalar(
            select(SpeakerJob).where(SpeakerJob.tenant_id == meeting_harness.tenant.tenant_id)
        )
        result = SpeakerResult.model_validate(job.result)
        assert result.decision == "enrolled" and result.profile_public_id
        assert result.model_id == MODEL_ID and result.model_revision == MODEL_REVISION
        assert result.speech_seconds == 21 and result.windows_count == 3
        assert not {"embedding", "storage_key", "tenant_id"} & job.result.keys()


@pytest.mark.parametrize("same_meeting", [True, False])
async def test_concurrent_same_voice_enrolls_exactly_one_profile(
    meeting_harness: MeetingHarness, same_meeting: bool
) -> None:
    provider = EvidenceProvider()
    first, _ = await prepare(meeting_harness, provider, [0])
    second = first if same_meeting else (await prepare(meeting_harness, provider, [0]))[0]
    resolver = memory(meeting_harness, provider)
    outcomes = await asyncio.gather(
        resolver.resolve_next(first, 1), resolver.resolve_next(second, 1)
    )
    assert any(outcomes)
    assert await profile_count(meeting_harness) == 1
    async with meeting_harness.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(SpeakerSample)
                .where(SpeakerSample.tenant_id == meeting_harness.tenant.tenant_id)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(SpeakerJob)
                .where(SpeakerJob.tenant_id == meeting_harness.tenant.tenant_id)
            )
            == 1
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"speech_seconds": float("nan")},
        {"speech_seconds": 60.0},
        {"windows_count": 0},
        {"windows_count": True},
        {"windows_count": 1.5},
        {"model_revision": "wrong-revision"},
        {"embedding": [float("nan")] * 192},
        {"embedding": [1e308] * 192},
        {"embedding": [0.0] * 192},
    ],
)
async def test_invalid_provider_result_never_completes_memory(
    meeting_harness: MeetingHarness, monkeypatch: pytest.MonkeyPatch, changes: dict
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    original = provider.embed

    async def invalid(
        audio: bytes, *, purpose, job_public_id: str, tenant_public_id: str
    ) -> EmbeddingResult:
        return replace(
            await original(
                audio,
                purpose=purpose,
                job_public_id=job_public_id,
                tenant_public_id=tenant_public_id,
            ),
            **changes,
        )

    monkeypatch.setattr(provider, "embed", invalid)
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 0
    async with meeting_harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        assert not track.props.get("memory_completed")


async def test_enrollment_quality_is_not_inferred_from_identify_duration(
    meeting_harness: MeetingHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    original = provider.embed
    purposes = []

    async def checked(
        audio: bytes, *, purpose, job_public_id: str, tenant_public_id: str
    ) -> EmbeddingResult:
        purposes.append(purpose)
        if purpose == "enroll":
            raise SpeakerError("inconsistent_audio", 422)
        return await original(
            audio, purpose=purpose, job_public_id=job_public_id, tenant_public_id=tenant_public_id
        )

    monkeypatch.setattr(provider, "embed", checked)
    assert await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert purposes == ["identify", "enroll"]
    assert await profile_count(meeting_harness) == 0


@pytest.mark.parametrize("field,value", [("model_revision", "wrong"), ("source_sha256", "0" * 64)])
async def test_snapshot_rejects_wrong_acoustic_evidence_provenance(
    meeting_harness: MeetingHarness, field: str, value: str
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    async with meeting_harness.sessions() as session, session.begin():
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        setattr(track, field, value)
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert provider.calls == 0 and await profile_count(meeting_harness) == 0


async def test_changed_clean_evidence_cannot_commit_old_inference(
    meeting_harness: MeetingHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    original = provider.embed

    async def changed(
        audio: bytes, *, purpose, job_public_id: str, tenant_public_id: str
    ) -> EmbeddingResult:
        result = await original(
            audio, purpose=purpose, job_public_id=job_public_id, tenant_public_id=tenant_public_id
        )
        async with meeting_harness.sessions() as session, session.begin():
            track = await session.scalar(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
            track.clean_ranges = [[0, 10 * 16000]]
        return result

    monkeypatch.setattr(provider, "embed", changed)
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 0


async def test_running_meeting_never_starts_final_memory(meeting_harness: MeetingHarness) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    async with meeting_harness.sessions() as session, session.begin():
        row = await session.get(Meeting, meeting_id)
        row.status = "running"
    assert not await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert provider.calls == 0 and await profile_count(meeting_harness) == 0


async def test_original_acoustic_cluster_and_sample_must_agree(
    meeting_harness: MeetingHarness,
) -> None:
    provider = EvidenceProvider()
    meeting_id, tracks = await prepare(meeting_harness, provider, [0])
    provider.vectors[tracks[0]] = [0.0, 1.0] + [0.0] * 190
    assert await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 0
    async with meeting_harness.sessions() as session:
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        assert track.decision == "profile_pending" and track.reason == "inconsistent_audio"


async def test_overlapping_tracks_cannot_claim_the_same_persistent_identity(
    meeting_harness: MeetingHarness,
) -> None:
    provider = EvidenceProvider()
    resolver = memory(meeting_harness, provider)
    previous, _ = await prepare(meeting_harness, provider, [0])
    assert await resolver.resolve_next(previous, 1)
    meeting_id, _ = await prepare(meeting_harness, provider, [0, 0])
    async with meeting_harness.sessions() as session, session.begin():
        rows = list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
        )
        for row in rows:
            row.props = {"speech_ranges": [[0, 20 * 16000]]}
    assert await resolver.resolve_next(meeting_id, 1)
    assert await resolver.resolve_next(meeting_id, 1)
    async with meeting_harness.sessions() as session:
        rows = list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
        )
        assert all(row.profile_id is None and row.decision == "ambiguous" for row in rows)
    assert await profile_count(meeting_harness) == 1


async def test_manual_name_during_inference_is_used_for_new_profile(
    meeting_harness: MeetingHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    original = provider.embed

    async def renamed(
        audio: bytes, *, purpose, job_public_id: str, tenant_public_id: str
    ) -> EmbeddingResult:
        async with meeting_harness.sessions() as session, session.begin():
            row = await session.scalar(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
            )
            row.display_name = "Named during inference"
            row.version += 1
        return await original(
            audio, purpose=purpose, job_public_id=job_public_id, tenant_public_id=tenant_public_id
        )

    monkeypatch.setattr(provider, "embed", renamed)
    assert await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    async with meeting_harness.sessions() as session:
        profile = await session.scalar(
            select(SpeakerProfile).where(
                SpeakerProfile.tenant_id == meeting_harness.tenant.tenant_id
            )
        )
        assert profile.name == "Named during inference"


@pytest.mark.parametrize("committed", [False, True])
async def test_commit_failure_only_removes_an_unreferenced_new_sample(
    meeting_harness: MeetingHarness, monkeypatch: pytest.MonkeyPatch, committed: bool
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    original = AsyncSession.commit

    async def uncertain_commit(session: AsyncSession) -> None:
        if committed:
            await original(session)
        raise RuntimeError(
            "Simulated lost commit acknowledgement" if committed else "Simulated commit rejection"
        )

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", uncertain_commit)
        with pytest.raises(RuntimeError, match="Simulated"):
            await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == int(committed)
    samples = list(meeting_harness.settings.audio_storage_path.glob("*.audio"))
    assert len(samples) == int(committed)
    if committed:
        assert not await memory(meeting_harness, provider).resolve_next(meeting_id, 1)


async def test_expired_lease_during_sample_write_cannot_commit_profile(
    meeting_harness: MeetingHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import meeting_memory as memory_module

    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0])
    resolver = memory(meeting_harness, provider)
    now = datetime.now(UTC)

    class Clock:
        @staticmethod
        def now(zone) -> datetime:
            assert zone == UTC
            return now

    original = resolver.sample_storage.receive

    async def slow_storage(source, filename):
        nonlocal now
        result = await original(source, filename)
        now += timedelta(minutes=20)
        return result

    monkeypatch.setattr(memory_module, "datetime", Clock)
    monkeypatch.setattr(resolver.sample_storage, "receive", slow_storage)
    with pytest.raises(SpeakerError, match="job_timeout"):
        await resolver.resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 0
    assert not list(meeting_harness.settings.audio_storage_path.glob("*.audio"))


async def test_known_short_speech_and_enrollment_quality_failure_keep_identity(
    meeting_harness: MeetingHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = EvidenceProvider()
    resolver = memory(meeting_harness, provider)
    initial, _ = await prepare(meeting_harness, provider, [0])
    assert await resolver.resolve_next(initial, 1)
    short, _ = await prepare(meeting_harness, provider, [0], 3.1)
    assert await resolver.resolve_next(short, 1)
    long, _ = await prepare(meeting_harness, provider, [0], 25)
    original = provider.embed

    async def reject_enroll(
        audio: bytes, *, purpose, job_public_id: str, tenant_public_id: str
    ) -> EmbeddingResult:
        if purpose == "enroll":
            raise SpeakerError("inconsistent_audio", 422)
        return await original(
            audio, purpose=purpose, job_public_id=job_public_id, tenant_public_id=tenant_public_id
        )

    monkeypatch.setattr(provider, "embed", reject_enroll)
    assert await resolver.resolve_next(long, 1)
    async with meeting_harness.sessions() as session:
        rows = list(
            await session.scalars(
                select(MeetingSpeaker).where(MeetingSpeaker.meeting_id.in_([short, long]))
            )
        )
        assert all(row.decision == "recognized" and row.profile_id is not None for row in rows)
    assert await profile_count(meeting_harness) == 1


@pytest.mark.parametrize("ambiguous,disabled", [(True, False), (False, True)])
async def test_uncertain_or_disabled_memory_cannot_enroll_long_unknown_speech(
    meeting_harness: MeetingHarness, ambiguous: bool, disabled: bool
) -> None:
    provider = EvidenceProvider()
    meeting_id, _ = await prepare(meeting_harness, provider, [0], 30)
    async with meeting_harness.sessions() as session, session.begin():
        row = await session.get(Meeting, meeting_id)
        row.auto_enroll = not disabled
        track = await session.scalar(
            select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id)
        )
        track.props = {"reconciliation_ambiguous": ambiguous}
    assert await memory(meeting_harness, provider).resolve_next(meeting_id, 1)
    assert await profile_count(meeting_harness) == 0
