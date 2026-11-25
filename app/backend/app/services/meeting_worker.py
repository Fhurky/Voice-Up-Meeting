"""Incremental durable meeting claims; completed source cores are never processed twice."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.domain.meeting import (
    WHOLE_RECORDING_MAX_SECONDS,
    meeting_tracks,
    previous_track_chunk,
    track_windows,
    window_core_seconds,
    window_turns,
)
from app.domain.meeting_identity import normalized_evidence
from app.domain.models.meeting import Meeting, MeetingDiarization, MeetingSpeaker
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.services.meeting_chunks import RECONCILIATION_VERSION, MeetingChunkPersistence
from app.services.meeting_memory import MeetingMemory
from app.services.meeting_ports import (
    MeetingAnalysisPort,
    MeetingChunkResult,
    MeetingRecordingResult,
)
from app.services.speaker_ports import SpeakerError

logger = logging.getLogger("app.meeting_worker")

# "whole": speakers come from one pass over the recording (PRD 030); "chunked": each chunk
# separates its own speakers and the meeting end reconciles them (PRD 021).
Flow = Literal["whole", "chunked"]
Phase = Literal["diarize", "chunk", "finalize"]


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
    phase: Phase = "chunk"
    flow: Flow = "chunked"
    # The source channel of a two-channel capture this step reads; None mixes all channels.
    channel: int | None = None


def meeting_chunks(
    meeting: Meeting,
) -> list[tuple[tuple[int, float, float, float, float], int | None]]:
    if meeting.duration_seconds is None:
        raise SpeakerError("recording_unavailable", 410)
    return track_windows(
        meeting.duration_seconds,
        meeting_tracks(meeting.capture_mode),
        core_seconds=window_core_seconds(meeting.props),
    )


def log_flow(flow: Flow, reason: str | None, **fields: float) -> None:
    logger.info(
        "meeting_diarization",
        extra={"structured_fields": {"flow": flow, "reason": reason, **fields}},
    )


async def stream_blocks(blocks: Iterator[bytes]) -> AsyncIterator[bytes]:
    """Read the source file off the event loop, one bounded block at a time."""
    try:
        while (block := await asyncio.to_thread(next, blocks, None)) is not None:
            yield block
    finally:
        close = getattr(blocks, "close", None)
        if close is not None:
            close()


class StaleClaim(Exception):
    """Another worker or a newer claim owns the meeting; this attempt changes nothing."""


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
            if (
                meeting.duration_seconds is None
                or meeting.sample_rate is None
                or not meeting.source_sha256
            ):
                self.terminal_failure(meeting, "recording_unavailable", now)
                return None
            chunks = meeting_chunks(meeting)
            finalizing = meeting.next_chunk_index == len(chunks)
            flow = meeting.props.get("diarization_flow")
            if flow is None and (finalizing or meeting.next_chunk_index > 0):
                # Meetings already underway keep the flow they started with (Decision 7).
                self.choose_chunked(meeting, "started_before_whole_recording")
            elif flow is None and meeting.duration_seconds > WHOLE_RECORDING_MAX_SECONDS:
                self.choose_chunked(meeting, "duration")
            elif flow is None and meeting.attempt_count >= 2:
                self.choose_chunked(meeting, "worker_interrupted", reset_attempts=True)
            if meeting.attempt_count >= 2:
                self.terminal_failure(meeting, "worker_interrupted", now)
                return None
            phase: Phase = (
                "finalize"
                if finalizing
                else "diarize" if meeting.props.get("diarization_flow") is None else "chunk"
            )
            channel: int | None = None
            if phase == "diarize":
                # One pass per claim: a two-channel capture diarizes its channels in turn.
                done = await repository.diarized_channels(meeting.tenant_id, meeting.meeting_id)
                channel = next(
                    (
                        track
                        for track in meeting_tracks(meeting.capture_mode)
                        if (track or 0) not in done
                    ),
                    None,
                )
            elif phase == "chunk":
                channel = chunks[meeting.next_chunk_index][1]
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
                None if finalizing else chunks[meeting.next_chunk_index][0],
                None if meeting.language == "auto" else meeting.language,
                # The speaker estimate is non-binding and never reaches the model.
                meeting.participant_count,
                None,
                phase,
                "whole" if meeting.props.get("diarization_flow") == "whole" else "chunked",
                channel,
            )

    @staticmethod
    def choose_chunked(meeting: Meeting, reason: str, *, reset_attempts: bool = False) -> None:
        meeting.props = {
            **meeting.props,
            "diarization_flow": "chunked",
            "diarization_fallback": reason,
        }
        # Only a failed whole-recording pass gives the chunks a fresh retry budget.
        if reset_attempts:
            meeting.attempt_count = 0
        log_flow("chunked", reason)

    async def process_once(self) -> bool:
        claim = await self.claim()
        if claim is None:
            return False
        started, state = time.monotonic(), "checkpointed"
        diarizing = claim.phase == "diarize"
        try:
            async with asyncio.timeout(self.settings.meeting_chunk_timeout_seconds):
                if claim.phase == "finalize":
                    await self.reconcile(claim)
                    await self.order_transcript(claim)
                    await self.memory.resolve_next(claim.meeting_id, claim.token)
                    await self.finish_memory(claim)
                    return self.log_attempt(claim, state, started)
                if claim.phase == "diarize":
                    next_claim = await self.diarize(claim)
                    if next_claim is None:
                        return self.log_attempt(claim, "diarized", started)
                    # The CPU keeps chunked separation; the first chunk follows at once.
                    claim, diarizing = next_claim, False
                await self.analyze_chunk(claim)
        except TimeoutError:
            state = "job_timeout"
            await self.fail(claim, state, retryable=True, fallback=diarizing)
        except SpeakerError as exc:
            state = exc.code
            await self.fail(
                claim,
                state,
                retryable=state in {"inference_unavailable", "inference_busy", "job_timeout"},
                fallback=diarizing,
            )
        except (SQLAlchemyError, OSError):
            state = "inference_unavailable"
            await self.fail(claim, state, retryable=True, fallback=diarizing)
        except ValueError:
            state = "model_mismatch"
            await self.fail(claim, state, retryable=False, fallback=diarizing)
        except StaleClaim:
            state = "stale_claim"
        return self.log_attempt(claim, state, started)

    def log_attempt(self, claim: ClaimedMeeting, state: str, started: float) -> bool:
        logger.info(
            "meeting_chunk_attempt",
            extra={
                "structured_fields": {
                    "state": state,
                    "duration_seconds": round(time.monotonic() - started, 4),
                    "chunk_index": (
                        claim.window[0] if claim.phase == "chunk" and claim.window else None
                    ),
                }
            },
        )
        return True

    async def analyze_chunk(self, claim: ClaimedMeeting) -> None:
        if claim.window is None:
            raise SpeakerError("model_mismatch", 502)
        _, context_start, _, _, context_end = claim.window
        audio = await asyncio.to_thread(
            self.storage.window,
            claim.storage_key,
            context_start,
            context_end,
            channel=claim.channel,
        )
        if claim.flow == "whole":
            result = await self.analysis.analyze_attributed(
                audio,
                await self.window_speakers(claim, context_start, context_end),
                job_public_id=claim.public_id,
                tenant_public_id=claim.tenant_public_id,
                language=claim.language,
            )
        else:
            result = await self.analysis.analyze(
                audio,
                job_public_id=claim.public_id,
                tenant_public_id=claim.tenant_public_id,
                language=claim.language,
                max_speakers=claim.max_speakers,
                num_speakers=claim.num_speakers,
            )
        if not await self.save_chunk(claim, result):
            raise StaleClaim

    async def window_speakers(
        self, claim: ClaimedMeeting, start: float, end: float
    ) -> dict[str, list[dict[str, float | str]]]:
        async with self.sessions() as session:
            diarization = await MeetingRepository(session).diarization(
                claim.tenant_id, claim.meeting_id, claim.channel or 0
            )
        if diarization is None:
            raise SpeakerError("model_mismatch", 502)
        turns = window_turns([tuple(row) for row in diarization.result["turns"]], start, end)
        labels = {row["speaker"] for row in turns}
        exclusive = [
            row
            for row in window_turns(
                [tuple(row) for row in diarization.result["exclusive_turns"]], start, end
            )
            if row["speaker"] in labels
        ]
        return {"turns": turns, "exclusive_turns": exclusive}

    async def diarize(self, claim: ClaimedMeeting) -> ClaimedMeeting | None:
        """Separate speakers once; on the CPU, choose chunks and return the first chunk claim."""
        processor = await self.analysis.processor()
        if processor.get("device") != "gpu":
            async with self.sessions() as session, session.begin():
                meeting = await MeetingRepository(session).fenced(
                    claim.meeting_id, claim.token, datetime.now(UTC)
                )
                if meeting is None or meeting.props.get("diarization_flow") is not None:
                    raise StaleClaim
                self.choose_chunked(meeting, "cpu")
            return replace(claim, phase="chunk", flow="chunked")
        started = time.monotonic()
        rate, frames = await asyncio.to_thread(self.storage.recording_info, claim.storage_key)
        result = await self.analysis.diarize_recording(
            stream_blocks(self.storage.recording_blocks(claim.storage_key, channel=claim.channel)),
            sample_rate=rate,
            size_bytes=frames * 2,
            job_public_id=claim.public_id,
            tenant_public_id=claim.tenant_public_id,
            max_speakers=claim.max_speakers,
        )
        if not await self.save_diarization(claim, result):
            raise StaleClaim
        log_flow(
            "whole",
            None,
            speakers=len(result.speakers),
            duration_seconds=round(time.monotonic() - started, 4),
            **({} if claim.channel is None else {"channel": claim.channel}),
        )
        return None

    async def save_diarization(self, claim: ClaimedMeeting, result: MeetingRecordingResult) -> bool:
        async with self.sessions() as session, session.begin():
            repository = MeetingRepository(session)
            meeting = await repository.fenced(claim.meeting_id, claim.token, datetime.now(UTC))
            if (
                meeting is None
                or meeting.next_chunk_index != 0
                or meeting.props.get("diarization_flow") is not None
            ):
                return False
            if not await repository.current_owner_allowed(meeting):
                raise SpeakerError("forbidden", 403)
            earlier, _ = await repository.speakers(meeting.tenant_id, meeting.meeting_id, 0, 1001)
            channel_number = claim.channel or 0
            previously = await repository.diarized_channels(meeting.tenant_id, meeting.meeting_id)
            if (
                any(row.channel == claim.channel for row in earlier)
                or channel_number in previously
                or meeting.duration_seconds is None
                or meeting.source_sha256 is None
                or abs(result.input_seconds - meeting.duration_seconds) > 0.001
            ):
                raise SpeakerError("model_mismatch", 502)
            first: dict[str, float] = {}
            for turn in sorted(result.turns, key=lambda value: (value.start, value.end)):
                first.setdefault(turn.speaker, turn.start)
            tracking = {speaker.speaker: speaker.tracking for speaker in result.speakers}
            session.add(
                MeetingDiarization(
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.meeting_id,
                    channel=channel_number,
                    recipe=result.model_identity.diarization.recipe,
                    model_id=result.model_identity.diarization.model_id,
                    model_revision=result.model_identity.diarization.revision,
                    source_sha256=meeting.source_sha256,
                    speaker_count=len(first),
                    result={
                        name: [[turn.start, turn.end, turn.speaker] for turn in turns]
                        for name, turns in (
                            ("turns", result.turns),
                            ("exclusive_turns", result.exclusive_turns),
                        )
                    },
                    created_by=meeting.created_by,
                    updated_by=meeting.created_by,
                )
            )
            # Speakers are numbered by first speech, so the transcript reads in order.
            base = max((row.ordinal for row in earlier), default=-1) + 1
            created: list[MeetingSpeaker] = []
            for ordinal, label in enumerate(sorted(first, key=lambda value: (first[value], value))):
                vector = tracking[label]
                speaker = MeetingSpeaker(
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.meeting_id,
                    ordinal=base + ordinal,
                    channel=claim.channel,
                    speech_seconds=0,
                    clean_ranges=[],
                    props={"diarization_label": label, "first_speech": first[label]},
                    tracking_embedding=(
                        normalized_evidence(vector.embedding, dimensions=256)
                        if vector is not None
                        else None
                    ),
                    tracking_model_id=vector.model_id if vector is not None else None,
                    tracking_model_revision=(vector.model_revision if vector is not None else None),
                    created_by=meeting.created_by,
                    updated_by=meeting.created_by,
                )
                session.add(speaker)
                created.append(speaker)
            tracks = meeting_tracks(meeting.capture_mode)
            # A silent channel is diarized too; it simply has no speakers.
            done = {channel_number, *previously}
            if all((track or 0) in done for track in tracks):
                if len(tracks) > 1:
                    await self.number_by_first_speech(session, [*earlier, *created])
                meeting.props = {
                    **meeting.props,
                    "diarization_flow": "whole",
                    "diarization_fallback": None,
                }
            if meeting.lease_expires_at is None or meeting.lease_expires_at <= datetime.now(UTC):
                raise SpeakerError("job_timeout", 503)
            meeting.attempt_count = 0
            meeting.lease_expires_at = datetime.now(UTC)
            return True

    @staticmethod
    async def number_by_first_speech(session: AsyncSession, rows: list[MeetingSpeaker]) -> None:
        """Both channels' speakers in one order of first speech; ordinals stay unique throughout."""
        await session.flush()
        offset = max((row.ordinal for row in rows), default=0) + 1
        for row in rows:
            row.ordinal += offset
        await session.flush()
        ordered = sorted(
            rows,
            key=lambda row: (
                float(row.props.get("first_speech", 0.0)),
                row.channel or 0,
                str(row.props.get("diarization_label", "")),
            ),
        )
        for ordinal, row in enumerate(ordered):
            row.ordinal = ordinal
        await session.flush()

    async def reconcile(self, claim: ClaimedMeeting) -> None:
        started = time.monotonic()
        async with self.sessions() as session, session.begin():
            repository = MeetingRepository(session)
            meeting = await repository.fenced(claim.meeting_id, claim.token, datetime.now(UTC))
            if (
                meeting is None
                or meeting.status != "finalizing"
                or meeting.props.get("reconciliation_version") == RECONCILIATION_VERSION
                # One pass over the recording already gave one identity per voice.
                or meeting.props.get("diarization_flow") == "whole"
            ):
                return
            if not await repository.current_owner_allowed(meeting):
                raise SpeakerError("forbidden", 403)
            await self.chunks.reconcile(repository, meeting)
        logger.info(
            "meeting_reconciliation",
            extra={"structured_fields": {"duration_seconds": round(time.monotonic() - started, 4)}},
        )

    async def order_transcript(self, claim: ClaimedMeeting) -> None:
        """A capture's channels are analysed window by window; its lines read in time order."""
        async with self.sessions() as session, session.begin():
            repository = MeetingRepository(session)
            meeting = await repository.fenced(claim.meeting_id, claim.token, datetime.now(UTC))
            if (
                meeting is None
                or meeting.status != "finalizing"
                or meeting.capture_mode != "two_channel"
                or meeting.props.get("transcript_order") == "time"
            ):
                return
            await repository.order_transcript_by_time(meeting.tenant_id, meeting.meeting_id)
            meeting.props = {**meeting.props, "transcript_order": "time"}

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
            chunks = meeting_chunks(meeting)
            await self.chunks.persist(
                repository,
                meeting,
                claim.window,
                result,
                channel=claim.channel,
                previous_index=previous_track_chunk(chunks, claim.window[0]),
            )
            if meeting.lease_expires_at is None or meeting.lease_expires_at <= datetime.now(UTC):
                raise SpeakerError("job_timeout", 503)
            meeting.next_chunk_index += 1
            meeting.processed_seconds = claim.window[3]
            meeting.attempt_count = 0
            meeting.status = "finalizing" if meeting.next_chunk_index == len(chunks) else "running"
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

    async def fail(
        self, claim: ClaimedMeeting, code: str, *, retryable: bool, fallback: bool = False
    ) -> None:
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
            elif fallback and code != "forbidden" and meeting.props.get("diarization_flow") is None:
                # A failed whole-recording pass never fails the meeting: chunks still work.
                self.choose_chunked(meeting, code, reset_attempts=True)
                meeting.lease_expires_at = now
            else:
                self.terminal_failure(meeting, code, now)
