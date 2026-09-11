"""Incremental durable meeting claims; completed source cores are never processed twice."""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.domain.meeting import analysis_windows, window_core_seconds
from app.domain.models.meeting import Meeting
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.services.meeting_chunks import MeetingChunkPersistence
from app.services.meeting_memory import MeetingMemory
from app.services.meeting_ports import MeetingAnalysisPort, MeetingChunkResult
from app.services.speaker_ports import SpeakerError

logger = logging.getLogger("app.meeting_worker")


@dataclass(frozen=True, slots=True)
class ClaimedMeeting:
    meeting_id: int
    public_id: str
    tenant_id: int
    tenant_public_id: str
    token: int
    storage_key: str
    window: tuple[int, float, float, float, float] | None
    language: str | None
    max_speakers: int | None
    num_speakers: int | None


class MeetingWorker:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        storage: MeetingAudioStorage,
        analysis: MeetingAnalysisPort,
        memory: MeetingMemory,
        settings: Settings,
    ) -> None:
        self.sessions, self.storage, self.analysis, self.memory, self.settings = (
            sessions,
            storage,
            analysis,
            memory,
            settings,
        )
        self.chunks = MeetingChunkPersistence(settings)

    def terminal_failure(self, meeting: Meeting, code: str, now: datetime) -> None:
        meeting.status, meeting.error_code = "failed", code
        meeting.finished_at, meeting.lease_expires_at = now, None
        meeting.source_expires_at = now + timedelta(
            days=self.settings.meeting_source_retention_days
        )

    async def claim(self) -> ClaimedMeeting | None:
        async with self.sessions() as session, session.begin():
            repository, now = MeetingRepository(session), datetime.now(UTC)
            meeting = await repository.claim(now)
            if meeting is None:
                return None
            if not await repository.current_owner_allowed(meeting):
                self.terminal_failure(meeting, "forbidden", now)
                return None
            if meeting.attempt_count >= 2:
                self.terminal_failure(meeting, "worker_interrupted", now)
                return None
            if (
                meeting.duration_seconds is None
                or meeting.sample_rate is None
                or not meeting.source_sha256
            ):
                self.terminal_failure(meeting, "recording_unavailable", now)
                return None
            windows = analysis_windows(
                meeting.duration_seconds,
                core_seconds=window_core_seconds(meeting.props),
            )
            finalizing = meeting.next_chunk_index == len(windows)
            meeting.status = "finalizing" if finalizing else "running"
            meeting.attempt_count += 1
            meeting.claim_token += 1
            meeting.started_at = meeting.started_at or now
            meeting.error_code = None
            meeting.lease_expires_at = now + timedelta(
                seconds=self.settings.meeting_chunk_timeout_seconds + 30
            )
            tenant_public_id = await repository.tenant_public_id(meeting.tenant_id)
            if tenant_public_id is None:
                self.terminal_failure(meeting, "recording_unavailable", now)
                return None
            return ClaimedMeeting(
                meeting.meeting_id,
                meeting.public_id,
                meeting.tenant_id,
                tenant_public_id,
                meeting.claim_token,
                meeting.storage_key,
                None if finalizing else windows[meeting.next_chunk_index],
                None if meeting.language == "auto" else meeting.language,
                meeting.expected_speakers or meeting.participant_count,
                meeting.expected_speakers if len(windows) == 1 else None,
            )

    async def process_once(self) -> bool:
        claim = await self.claim()
        if claim is None:
            return False
        started, state = time.monotonic(), "checkpointed"
        try:
            async with asyncio.timeout(self.settings.meeting_chunk_timeout_seconds):
                if claim.window is None:
                    await self.memory.resolve_next(claim.meeting_id, claim.token)
                    await self.finish_memory(claim)
                else:
                    _, context_start, _, _, context_end = claim.window
                    audio = await asyncio.to_thread(
                        self.storage.window,
                        claim.storage_key,
                        context_start,
                        context_end,
                    )
                    result = await self.analysis.analyze(
                        audio,
                        job_public_id=claim.public_id,
                        tenant_public_id=claim.tenant_public_id,
                        language=claim.language,
                        max_speakers=claim.max_speakers,
                        num_speakers=claim.num_speakers,
                    )
                    if not await self.save_chunk(claim, result):
                        state = "stale_claim"
        except TimeoutError:
            state = "job_timeout"
            await self.fail(claim, state, retryable=True)
        except SpeakerError as exc:
            state = exc.code
            await self.fail(
                claim,
                state,
                retryable=state in {"inference_unavailable", "inference_busy", "job_timeout"},
            )
        except (SQLAlchemyError, OSError):
            state = "inference_unavailable"
            await self.fail(claim, state, retryable=True)
        except ValueError:
            state = "model_mismatch"
            await self.fail(claim, state, retryable=False)
        logger.info(
            "meeting_chunk_attempt",
            extra={
                "structured_fields": {
                    "state": state,
                    "duration_seconds": round(time.monotonic() - started, 4),
                    "chunk_index": claim.window[0] if claim.window else None,
                }
            },
        )
        return True

    async def save_chunk(self, claim: ClaimedMeeting, result: MeetingChunkResult) -> bool:
        if claim.window is None:
            return False
        async with self.sessions() as session, session.begin():
            repository = MeetingRepository(session)
            meeting = await repository.fenced(claim.meeting_id, claim.token, datetime.now(UTC))
            if meeting is None or meeting.next_chunk_index != claim.window[0]:
                return False
            if not await repository.current_owner_allowed(meeting):
                raise SpeakerError("forbidden", 403)
            await self.chunks.persist(repository, meeting, claim.window, result)
            if meeting.lease_expires_at is None or meeting.lease_expires_at <= datetime.now(UTC):
                raise SpeakerError("job_timeout", 503)
            meeting.next_chunk_index += 1
            meeting.processed_seconds = claim.window[3]
            meeting.attempt_count = 0
            meeting.status = (
                "finalizing" if meeting.processed_seconds == meeting.duration_seconds else "running"
            )
            meeting.lease_expires_at = datetime.now(UTC)
            return True

    async def finish_memory(self, claim: ClaimedMeeting) -> bool:
        async with self.sessions() as session, session.begin():
            repository = MeetingRepository(session)
            meeting = await repository.fenced(claim.meeting_id, claim.token, datetime.now(UTC))
            if meeting is None or meeting.status != "finalizing":
                return False
            if not await repository.current_owner_allowed(meeting):
                raise SpeakerError("forbidden", 403)
            pending = await repository.pending_speaker(meeting.tenant_id, meeting.meeting_id)
            if meeting.lease_expires_at is None or meeting.lease_expires_at <= datetime.now(UTC):
                raise SpeakerError("job_timeout", 503)
            if pending is None:
                now = datetime.now(UTC)
                meeting.status, meeting.finished_at, meeting.lease_expires_at = (
                    "succeeded",
                    now,
                    None,
                )
                meeting.source_expires_at = now + timedelta(
                    days=self.settings.meeting_source_retention_days
                )
            else:
                meeting.lease_expires_at = datetime.now(UTC)
            meeting.attempt_count = 0
            return True

    async def fail(self, claim: ClaimedMeeting, code: str, *, retryable: bool) -> None:
        async with self.sessions() as session, session.begin():
            repository, now = MeetingRepository(session), datetime.now(UTC)
            meeting = await repository.fenced(claim.meeting_id, claim.token, now)
            if meeting is None:
                return
            if code == "inference_busy":
                meeting.attempt_count = max(0, meeting.attempt_count - 1)
                meeting.lease_expires_at = now + timedelta(
                    seconds=self.settings.worker_poll_seconds
                )
            elif retryable and meeting.attempt_count < 2:
                meeting.lease_expires_at = now
            else:
                self.terminal_failure(meeting, code, now)
