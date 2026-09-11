"""Fenced, quality-gated enrollment into the existing speaker identity population."""

import asyncio
import hashlib
import io
import json
import math
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.domain.meeting import AUTO_ENROLL_SECONDS, clean_union
from app.domain.meeting_memory_trace import build_memory_match_trace
from app.domain.meeting_native_exclusions import (
    ABSENT_EXCLUSIONS,
    check_exclusion_graph,
    read_exclusions,
)
from app.domain.models.meeting import Meeting, MeetingSpeaker
from app.domain.models.mixins import new_public_id
from app.domain.models.speaker_identity import Recording, SpeakerJob, SpeakerProfile, SpeakerSample
from app.domain.speaker_identity import (
    MEETING_MODEL_ID,
    MEETING_MODEL_REVISION,
    MEETING_PREPROCESSING_VERSION,
    MODEL_ID,
    MODEL_REVISION,
    MatchDecision,
    MatchPolicy,
    decide,
    normalize,
)
from app.infrastructure.audio_storage import AudioStorage, StoredAudio
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.schemas.speaker_identity import MatchPolicyResponse, SpeakerResult
from app.services.meeting_memory_ports import MeetingMemoryPort, MeetingMemoryResult, MemoryContext
from app.services.meeting_memory_samples import prepare_context_sample, validate_context_result
from app.services.meeting_ports import MeetingTracking
from app.services.speaker_ports import EmbeddingPort, EmbeddingResult, SpeakerError

QUALITY_ERRORS = {"insufficient_speech", "inconsistent_audio", "clipped_audio", "invalid_audio"}


class MemoryAudio:
    def __init__(self, data: bytes) -> None:
        self.stream = io.BytesIO(data)

    async def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)


@dataclass(frozen=True, slots=True)
class MemoryEvidence:
    meeting_id: int
    tenant_id: int
    tenant_public_id: str
    speaker_id: int
    speaker_public_id: str
    storage_key: str
    sample_rate: int
    clean_ranges: list[tuple[int, int]]
    speech_seconds: float
    eligible: bool
    acoustic_embedding: list[float] | None
    fingerprint: str
    uses_context_quality: bool = False
    candidate_contexts: list[MemoryContext] = field(default_factory=list)
    tracking: MeetingTracking | None = None
    competitors: list[MeetingTracking] = field(default_factory=list)
    allow_context_enroll: bool = False


class MeetingMemory:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        storage: MeetingAudioStorage,
        sample_storage: AudioStorage,
        embedding: EmbeddingPort,
        settings: Settings,
        context_quality: MeetingMemoryPort | None = None,
    ) -> None:
        self.sessions = sessions
        self.storage = storage
        self.sample_storage = sample_storage
        self.embedding = embedding
        self.settings = settings
        self.context_quality = context_quality
        self.policy = MatchPolicy(
            settings.speaker_match_threshold,
            settings.speaker_new_threshold,
            settings.speaker_match_margin,
        )

    async def snapshot(self, meeting_id: int, token: int) -> MemoryEvidence | None:
        async with self.sessions() as session, session.begin():
            repository = MeetingRepository(session)
            meeting = await repository.fenced(meeting_id, token, datetime.now(UTC))
            if meeting is None or meeting.status != "finalizing":
                return None
            if not await repository.current_owner_allowed(meeting):
                raise SpeakerError("forbidden", 403)
            row = await repository.pending_speaker(meeting.tenant_id, meeting.meeting_id)
            if row is None:
                return None
            tenant_public_id = await repository.tenant_public_id(meeting.tenant_id)
            if not tenant_public_id:
                raise SpeakerError("recording_unavailable", 410)
            competitors = await self.competitors(repository, meeting, row)
            return self.evidence(meeting, row, tenant_public_id, competitors)

    @staticmethod
    async def competitors(
        repository: MeetingRepository, meeting: Meeting, row: MeetingSpeaker
    ) -> list[MeetingTracking]:
        rows, total = await repository.speakers(meeting.tenant_id, meeting.meeting_id, 0, 1000)
        try:
            if total > 1000:
                raise ValueError("invalid_native_exclusions")
            check_exclusion_graph(
                [
                    (
                        candidate.meeting_speaker_id,
                        candidate.props.get("native_exclusions", ABSENT_EXCLUSIONS),
                    )
                    for candidate in rows
                ],
                meeting.source_sha256,
            )
        except (TypeError, ValueError) as exc:
            raise SpeakerError("model_mismatch", 502) from exc
        result = []
        for candidate in rows:
            if (
                candidate.meeting_speaker_id == row.meeting_speaker_id
                or candidate.tracking_embedding is None
            ):
                continue
            try:
                result.append(
                    MeetingTracking.model_validate(
                        {
                            "embedding": list(candidate.tracking_embedding),
                            "model_id": candidate.tracking_model_id,
                            "model_revision": candidate.tracking_model_revision,
                            "component": "embedding",
                            "dimensions": 256,
                        }
                    )
                )
            except ValidationError as exc:
                raise SpeakerError("model_mismatch", 502) from exc
        return result

    @classmethod
    def evidence(
        cls,
        meeting: Meeting,
        row: MeetingSpeaker,
        tenant_public_id: str,
        competitors: list[MeetingTracking] | None = None,
    ) -> MemoryEvidence:
        if (
            meeting.sample_rate is None
            or meeting.duration_seconds is None
            or not meeting.source_sha256
        ):
            raise SpeakerError("recording_unavailable", 410)
        acoustic = None
        if row.embedding is not None:
            if (
                row.model_id != MODEL_ID
                or row.model_revision != MODEL_REVISION
                or row.source_sha256 != meeting.source_sha256
            ):
                raise SpeakerError("model_mismatch", 502)
            acoustic = cls.checked_vector(list(row.embedding))
        context_quality = "candidate_contexts" in row.props
        candidates: list[MemoryContext] = []
        tracking = None
        try:
            native_exclusions = read_exclusions(
                row.props.get("native_exclusions", ABSENT_EXCLUSIONS),
                meeting.source_sha256,
                row.meeting_speaker_id,
            )
            if context_quality:
                if row.props.get("candidate_version") != MEETING_PREPROCESSING_VERSION:
                    raise ValueError("unsupported_memory_candidate_version")
                raw_candidates = row.props["candidate_contexts"]
                if not isinstance(raw_candidates, list) or len(raw_candidates) > 256:
                    raise ValueError("invalid_memory_candidates")
                candidates = [
                    MemoryContext.model_validate(
                        {
                            **value,
                            "voiced_ranges": [
                                {"start": start, "end": end}
                                for start, end in value["voiced_ranges"]
                            ],
                        }
                    )
                    for value in raw_candidates
                ]
                limit = round(meeting.duration_seconds * meeting.sample_rate)
                previous = 0
                for context in candidates:
                    if context.start < previous or context.end > limit:
                        raise ValueError("invalid_memory_candidate_bounds")
                    previous = context.end
                if candidates:
                    if row.source_sha256 != meeting.source_sha256:
                        raise ValueError("memory_candidate_source_mismatch")
                    tracking = MeetingTracking.model_validate(
                        {
                            "embedding": (
                                list(row.tracking_embedding)
                                if row.tracking_embedding is not None
                                else []
                            ),
                            "model_id": row.tracking_model_id,
                            "model_revision": row.tracking_model_revision,
                            "component": "embedding",
                            "dimensions": 256,
                        }
                    )
            ranges = clean_union(
                [(start, end) for start, end in row.clean_ranges],
                [],
                0,
                round(meeting.duration_seconds * meeting.sample_rate),
            )
            seconds = sum(end - start for start, end in ranges) / meeting.sample_rate
            fingerprint = hashlib.sha256(
                json.dumps(
                    {
                        "source": meeting.source_sha256,
                        "native_exclusions": (
                            native_exclusions.to_record() if native_exclusions else None
                        ),
                        "rate": meeting.sample_rate,
                        "duration": meeting.duration_seconds,
                        "ranges": ranges,
                        "embedding": acoustic,
                        "auto_enroll": meeting.auto_enroll,
                        "ambiguous": row.props.get("reconciliation_ambiguous", False),
                        "speech_ranges": row.props.get("speech_ranges", []),
                        "context_quality": context_quality,
                        "candidate_contexts": [item.model_dump(mode="json") for item in candidates],
                        "tracking": tracking.model_dump(mode="json") if tracking else None,
                        "competitors": [item.model_dump(mode="json") for item in competitors or []],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode()
            ).hexdigest()
        except (TypeError, ValueError, OverflowError, KeyError) as exc:
            raise SpeakerError("model_mismatch", 502) from exc
        eligible = (
            meeting.auto_enroll
            and seconds > AUTO_ENROLL_SECONDS
            and acoustic is not None
            and not row.props.get("reconciliation_ambiguous", False)
        )
        return MemoryEvidence(
            meeting.meeting_id,
            meeting.tenant_id,
            tenant_public_id,
            row.meeting_speaker_id,
            row.public_id,
            meeting.storage_key,
            meeting.sample_rate,
            ranges,
            seconds,
            bool(eligible),
            acoustic,
            fingerprint,
            context_quality,
            candidates,
            tracking,
            competitors or [],
            meeting.auto_enroll and not bool(row.props.get("reconciliation_ambiguous", False)),
        )

    @staticmethod
    def checked_vector(values: list[float]) -> list[float]:
        try:
            vector = [float(value) for value in normalize(values)]
            if not 0.999 <= sum(value * value for value in vector) <= 1.001:
                raise ValueError("Invalid normalized embedding")
        except (TypeError, ValueError, OverflowError) as exc:
            raise SpeakerError("model_mismatch", 502) from exc
        return vector

    async def resolve_next(self, meeting_id: int, token: int) -> bool:
        evidence = await self.snapshot(meeting_id, token)
        if evidence is None:
            return False
        if evidence.uses_context_quality:
            return await self.resolve_context(evidence, token)
        result: EmbeddingResult | None = None
        quality_error: str | None = None
        payload: bytes | None = None
        enrollment_quality = False
        if evidence.speech_seconds >= 3:
            try:
                payload = await asyncio.to_thread(
                    self.storage.sample,
                    evidence.storage_key,
                    evidence.clean_ranges,
                    evidence.sample_rate,
                )
                result = await self.embedding.embed(
                    payload,
                    purpose="identify",
                    job_public_id=evidence.speaker_public_id,
                    tenant_public_id=evidence.tenant_public_id,
                )
                self.validate_result(result, evidence)
                if evidence.acoustic_embedding is not None:
                    agreement = sum(
                        left * right
                        for left, right in zip(
                            evidence.acoustic_embedding,
                            self.checked_vector(result.embedding),
                            strict=True,
                        )
                    )
                    if agreement < self.policy.match_threshold:
                        raise SpeakerError("inconsistent_audio", 422)
                if evidence.eligible:
                    try:
                        candidate = await self.embedding.embed(
                            payload,
                            purpose="enroll",
                            job_public_id=evidence.speaker_public_id,
                            tenant_public_id=evidence.tenant_public_id,
                        )
                        self.validate_result(candidate, evidence)
                        if candidate.speech_seconds >= 10 - 1e-6 and candidate.windows_count >= 2:
                            agreement = sum(
                                left * right
                                for left, right in zip(
                                    self.checked_vector(result.embedding),
                                    self.checked_vector(candidate.embedding),
                                    strict=True,
                                )
                            )
                            if agreement >= self.policy.match_threshold:
                                result, enrollment_quality = candidate, True
                            else:
                                quality_error = "inconsistent_audio"
                        else:
                            quality_error = "insufficient_speech"
                    except SpeakerError as exc:
                        if exc.code not in QUALITY_ERRORS:
                            raise
                        quality_error = exc.code
            except SpeakerError as exc:
                if exc.code not in QUALITY_ERRORS:
                    raise
                result, quality_error = None, exc.code
        else:
            quality_error = "insufficient_speech"
        return await self.persist(
            evidence, token, result, payload, enrollment_quality, quality_error
        )

    async def resolve_context(self, evidence: MemoryEvidence, token: int) -> bool:
        unqualified = replace(evidence, clean_ranges=[], speech_seconds=0.0, eligible=False)
        if not evidence.candidate_contexts or evidence.tracking is None:
            return await self.persist(unqualified, token, None, None, False, "insufficient_speech")
        if self.context_quality is None:
            raise SpeakerError("inference_unavailable", 503)
        try:
            sample = await asyncio.to_thread(
                prepare_context_sample,
                self.storage,
                evidence.storage_key,
                evidence.candidate_contexts,
                evidence.sample_rate,
            )
            quality = await self.context_quality.verify(
                sample.data,
                contexts=sample.contexts,
                target=evidence.tracking,
                competitors=evidence.competitors,
                job_public_id=evidence.speaker_public_id,
                tenant_public_id=evidence.tenant_public_id,
            )
            ranges, independent = validate_context_result(sample, quality)
            if quality.status != "usable":
                return await self.persist(unqualified, token, None, None, False, quality.status)
            payload = await asyncio.to_thread(
                self.storage.sample, evidence.storage_key, ranges, evidence.sample_rate
            )
            if hashlib.sha256(payload).hexdigest() != quality.retained_sha256:
                raise SpeakerError("model_mismatch", 502)
            seconds = sum(end - start for start, end in ranges) / evidence.sample_rate
            resolved = replace(
                evidence,
                clean_ranges=ranges,
                speech_seconds=seconds,
                eligible=(
                    seconds > AUTO_ENROLL_SECONDS
                    and independent >= 3
                    and evidence.allow_context_enroll
                ),
            )
            result = EmbeddingResult(
                quality.embedding192 or [],
                seconds,
                quality.windows_count,
                MODEL_ID,
                MODEL_REVISION,
                quality.device,
                preprocessing_version="meeting-natural-context-v1",
            )
            return await self.persist(
                resolved,
                token,
                result,
                payload,
                independent >= 3,
                "inconsistent_audio" if independent < 3 and seconds > AUTO_ENROLL_SECONDS else None,
                quality,
            )
        except SpeakerError as exc:
            if exc.code not in QUALITY_ERRORS:
                raise
            return await self.persist(unqualified, token, None, None, False, exc.code)

    @staticmethod
    def validate_result(result: EmbeddingResult, evidence: MemoryEvidence) -> None:
        if result.model_id != MODEL_ID or result.model_revision != MODEL_REVISION:
            raise SpeakerError("model_mismatch", 502)
        MeetingMemory.checked_vector(result.embedding)
        if (
            isinstance(result.speech_seconds, bool)
            or not math.isfinite(result.speech_seconds)
            or not 3 - 1e-6 <= result.speech_seconds <= min(60, evidence.speech_seconds) + 1e-6
            or type(result.windows_count) is not int
            or not 1 <= result.windows_count <= 20
            or not re.fullmatch(r"cpu|cuda:[0-9]+", result.device)
            or result.preprocessing_version
            not in (
                {"meeting-natural-context-v1"}
                if evidence.uses_context_quality
                else {None, "vad-windows-v1", "vad-packed-fallback-v1"}
            )
        ):
            raise SpeakerError("model_mismatch", 502)

    async def persist(
        self,
        evidence: MemoryEvidence,
        token: int,
        result: EmbeddingResult | None,
        payload: bytes | None,
        enrollment_quality: bool,
        quality_error: str | None,
        context_result: MeetingMemoryResult | None = None,
    ) -> bool:
        stored: StoredAudio | None = None
        keep_file = False
        try:
            async with self.sessions() as session, session.begin():
                repository = MeetingRepository(session)
                await repository.lock_tenant(evidence.tenant_id)
                meeting = await repository.fenced(evidence.meeting_id, token, datetime.now(UTC))
                if meeting is None or meeting.status != "finalizing":
                    return False
                if not await repository.current_owner_allowed(meeting):
                    raise SpeakerError("forbidden", 403)
                row = await repository.speaker_by_id(
                    evidence.tenant_id, evidence.meeting_id, evidence.speaker_id
                )
                if row is None:
                    return False
                if row.props.get("memory_completed"):
                    return True
                competitors = await self.competitors(repository, meeting, row)
                current = self.evidence(meeting, row, evidence.tenant_public_id, competitors)
                if current.fingerprint != evidence.fingerprint:
                    raise SpeakerError("model_mismatch", 502)
                row.speech_seconds = evidence.speech_seconds
                if evidence.uses_context_quality:
                    row.clean_ranges = [[a, b] for a, b in evidence.clean_ranges]
                row.profile_id = None
                # A rejected acoustic track has no eligible sample. Preserve the
                # observed quality failure rather than relabeling it as silence.
                retained_reason = (
                    row.reason
                    if row.reason in QUALITY_ERRORS and evidence.speech_seconds == 0
                    else "insufficient_speech"
                )
                row.decision = "profile_pending"
                row.reason = (
                    retained_reason
                    if quality_error in {None, "insufficient_speech"}
                    else quality_error
                )
                if result is not None:
                    self.validate_result(result, evidence)
                    vector = self.checked_vector(result.embedding)
                    ranked = await repository.speaker_repository.ranked(evidence.tenant_id, vector)
                    ecapa_scores = [score for _, score in ranked]
                    community_scores = None
                    winner_agreement = None
                    decision = decide(ecapa_scores, self.policy)
                    if context_result is not None:
                        if context_result.memory_embedding is None:
                            raise SpeakerError("model_mismatch", 502)
                        meeting_ranked = await repository.speaker_repository.ranked_meeting(
                            evidence.tenant_id, context_result.memory_embedding.embedding
                        )
                        community_scores = [score for _, score in meeting_ranked]
                        if ranked and meeting_ranked:
                            winner_agreement = (
                                ranked[0][0].speaker_profile_id
                                == meeting_ranked[0][0].speaker_profile_id
                            )
                        decision, ranked = self.fuse_populations(ranked, meeting_ranked)
                    try:
                        match_trace = build_memory_match_trace(
                            ecapa_scores,
                            community_scores,
                            policy=self.policy,
                            evidence_sha256=evidence.fingerprint,
                            preprocessing_version=result.preprocessing_version,
                            winner_agreement=winner_agreement,
                        )
                    except (TypeError, ValueError) as exc:
                        raise SpeakerError("model_mismatch", 502) from exc
                    row.props = {**row.props, "memory_match_trace": match_trace}
                    row.reason = decision.reason
                    if decision.decision == "recognized":
                        profile = ranked[0][0]
                        conflict_reason = await self.conflicting_assignment(
                            repository, row, profile.speaker_profile_id, meeting.source_sha256
                        )
                        if conflict_reason:
                            row.decision, row.reason = "ambiguous", conflict_reason
                        else:
                            row.profile_id = profile.speaker_profile_id
                            row.decision = "recognized"
                    elif decision.decision == "ambiguous":
                        row.decision = "ambiguous"
                    elif evidence.eligible and enrollment_quality and payload is not None:
                        stored = await self.sample_storage.receive(
                            MemoryAudio(payload), "sample.wav"
                        )
                        now = datetime.now(UTC)
                        provenance = f"meeting:{meeting.public_id}:{row.public_id}"
                        profile_public_id = new_public_id()
                        name = row.display_name or f"Konuşmacı {profile_public_id[:8]}"
                        recording = Recording(
                            tenant_id=evidence.tenant_id,
                            storage_key=stored.key,
                            sha256=stored.sha256,
                            size_bytes=stored.size_bytes,
                            format=stored.format,
                            duration_seconds=stored.duration_seconds,
                            idempotency_key=provenance,
                            idempotency_expires_at=now
                            + timedelta(days=self.settings.job_retention_days),
                            expires_at=now + timedelta(hours=self.settings.audio_retention_hours),
                            created_by=meeting.created_by,
                            updated_by=meeting.created_by,
                        )
                        profile = SpeakerProfile(
                            public_id=profile_public_id,
                            tenant_id=evidence.tenant_id,
                            name=name,
                            sample_count=1,
                            model_id=MODEL_ID,
                            model_revision=MODEL_REVISION,
                            embedding=vector,
                            source_sha256=hashlib.sha256(stored.sha256.encode()).hexdigest(),
                            created_by=meeting.created_by,
                            updated_by=meeting.created_by,
                        )
                        session.add_all([recording, profile])
                        await session.flush()
                        if (
                            context_result is not None
                            and context_result.memory_embedding is not None
                        ):
                            profile.meeting_embedding = context_result.memory_embedding.embedding
                            profile.meeting_model_id = MEETING_MODEL_ID
                            profile.meeting_model_revision = MEETING_MODEL_REVISION
                            profile.meeting_preprocessing_version = MEETING_PREPROCESSING_VERSION
                            profile.meeting_source_sha256 = stored.sha256
                            profile.meeting_recording_id = recording.recording_id
                        trace = SpeakerResult(
                            decision="enrolled",
                            profile_public_id=profile.public_id,
                            profile_name=name,
                            similarity=ranked[0][1] if ranked else None,
                            runner_up_similarity=ranked[1][1] if len(ranked) > 1 else None,
                            speech_seconds=result.speech_seconds,
                            windows_count=result.windows_count,
                            model_id=result.model_id,
                            model_revision=result.model_revision,
                            device=result.device,
                            reason="enrolled",
                            policy=MatchPolicyResponse(**asdict(self.policy)),
                            preprocessing_version=result.preprocessing_version,
                        )
                        job = SpeakerJob(
                            tenant_id=evidence.tenant_id,
                            recording_id=recording.recording_id,
                            requested_name=name,
                            purpose="enroll",
                            status="succeeded",
                            model_id=MODEL_ID,
                            model_revision=MODEL_REVISION,
                            idempotency_key=provenance,
                            fingerprint=hashlib.sha256(provenance.encode()).hexdigest(),
                            attempt_count=1,
                            started_at=now,
                            finished_at=now,
                            result=trace.model_dump(mode="json"),
                            created_by=meeting.created_by,
                            updated_by=meeting.created_by,
                        )
                        session.add(job)
                        await session.flush()
                        session.add(
                            SpeakerSample(
                                tenant_id=evidence.tenant_id,
                                speaker_profile_id=profile.speaker_profile_id,
                                recording_id=recording.recording_id,
                                speaker_job_id=job.speaker_job_id,
                                embedding=vector,
                                model_id=MODEL_ID,
                                model_revision=MODEL_REVISION,
                                source_sha256=stored.sha256,
                                speech_seconds=result.speech_seconds,
                                windows_count=result.windows_count,
                                created_by=meeting.created_by,
                                updated_by=meeting.created_by,
                            )
                        )
                        row.profile_id, row.enrollment_job_id = (
                            profile.speaker_profile_id,
                            job.speaker_job_id,
                        )
                        row.decision, row.reason = "enrolled", "new_profile_created"
                    else:
                        row.reason = quality_error or (
                            "reconciliation_ambiguous"
                            if row.props.get("reconciliation_ambiguous")
                            else (
                                "insufficient_speech"
                                if evidence.speech_seconds <= AUTO_ENROLL_SECONDS
                                else "automatic_memory_disabled"
                            )
                        )
                row.props = {**row.props, "memory_completed": True}
                if meeting.lease_expires_at is None or meeting.lease_expires_at <= datetime.now(
                    UTC
                ):
                    raise SpeakerError("job_timeout", 503)
                await session.flush()
                await session.commit()
                keep_file = True
                return True
        finally:
            if stored is not None and not keep_file:
                await self.remove_unreferenced_sample(evidence.tenant_id, stored.key)

    def fuse_populations(
        self,
        ecapa: list[tuple[SpeakerProfile, float]],
        meeting: list[tuple[SpeakerProfile, float]],
    ) -> tuple[MatchDecision, list[tuple[SpeakerProfile, float]]]:
        old = decide([score for _, score in ecapa], self.policy)
        current = decide([score for _, score in meeting], self.policy)
        if old.decision == "ambiguous" or current.decision == "ambiguous":
            return MatchDecision("ambiguous", "insufficient_margin"), meeting or ecapa
        if current.decision == "recognized":
            if (
                old.decision == "recognized"
                and ecapa[0][0].speaker_profile_id != meeting[0][0].speaker_profile_id
            ):
                return MatchDecision("ambiguous", "inconsistent_audio"), meeting
            return current, meeting
        if old.decision == "recognized":
            profile = ecapa[0][0]
            if (
                profile.meeting_embedding is not None
                and profile.meeting_model_id == MEETING_MODEL_ID
                and profile.meeting_model_revision == MEETING_MODEL_REVISION
                and profile.meeting_preprocessing_version == MEETING_PREPROCESSING_VERSION
            ):
                return MatchDecision("ambiguous", "inconsistent_audio"), ecapa
            return old, ecapa
        return (
            MatchDecision(
                "unknown", "no_profiles" if not meeting and not ecapa else "below_new_threshold"
            ),
            meeting or ecapa,
        )

    async def remove_unreferenced_sample(self, tenant_id: int, storage_key: str) -> None:
        try:
            async with self.sessions() as session:
                repository = MeetingRepository(session).speaker_repository
                committed = await repository.recording_by_storage_key(tenant_id, storage_key)
        except SQLAlchemyError:
            # A lost commit acknowledgement is not proof of rollback. Existing orphan
            # retention can remove this owned file after database availability returns.
            return
        if committed is None:
            await self.sample_storage.remove(storage_key)

    @staticmethod
    async def conflicting_assignment(
        repository: MeetingRepository,
        row: MeetingSpeaker,
        profile_id: int,
        source_sha256: str | None,
    ) -> str | None:
        others = await repository.speaker_profile_assignments(
            row.tenant_id, row.meeting_id, profile_id
        )
        conflict = None
        state = read_exclusions(
            row.props.get("native_exclusions", ABSENT_EXCLUSIONS),
            source_sha256,
            row.meeting_speaker_id,
        )
        excluded = {peer.meeting_speaker_id for peer in state.peers} if state else set()
        current_ranges = row.props.get("speech_ranges", [])
        for other in others:
            if other.meeting_speaker_id == row.meeting_speaker_id:
                continue
            overlap = any(
                max(start, left) < min(end, right)
                for start, end in current_ranges
                for left, right in other.props.get("speech_ranges", [])
            )
            if overlap or other.meeting_speaker_id in excluded:
                reason = "overlapping_identity_conflict" if overlap else "inconsistent_audio"
                if conflict != "overlapping_identity_conflict":
                    conflict = reason
                other.profile_id = None
                other.decision, other.reason = "ambiguous", reason
        return conflict
