"""Run the same-domain durable worker as a separate deployment process."""

import argparse
import asyncio
import logging
import time
from pathlib import Path

import httpx
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db import base as _model_registry  # noqa: F401
from app.db.session import async_session_factory, engine
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.meeting_inference import HttpMeetingAdapter
from app.infrastructure.meeting_memory_inference import HttpMeetingMemoryAdapter
from app.infrastructure.speaker_inference import HttpEmbeddingAdapter
from app.services.meeting_cleanup import MeetingCleanup
from app.services.meeting_memory import MeetingMemory
from app.services.meeting_worker import MeetingWorker
from app.services.speaker_ports import SpeakerError
from app.services.speaker_worker import SpeakerWorker

HEARTBEAT_PATH = Path("/tmp/voiceup-worker-health")


async def process_ready_meeting(adapter: HttpMeetingAdapter, worker: MeetingWorker) -> bool:
    """Keep cold model startup outside persisted claim and retry accounting."""
    try:
        ready = await adapter.ready()
    except SpeakerError as exc:
        logging.getLogger("app.speaker_worker").error(
            "meeting_readiness_failed", extra={"structured_fields": {"code": exc.code}}
        )
        return False
    if not ready:
        return False
    return await worker.process_once()


def healthcheck() -> bool:
    try:
        age = time.time() - HEARTBEAT_PATH.stat().st_mtime
    except OSError:
        return False
    settings = get_settings()
    return (
        0 <= age <= max(settings.job_timeout_seconds, settings.meeting_chunk_timeout_seconds) + 60
    )


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.inference_key is None:
        raise RuntimeError("VOICEUP_INFERENCE_KEY is required by the worker")
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            audio_storage = AudioStorage(settings)
            embedding = HttpEmbeddingAdapter(settings, client)
            worker = SpeakerWorker(
                async_session_factory,
                audio_storage,
                embedding,
                settings,
            )
            meeting_storage = MeetingAudioStorage(settings.audio_storage_path / "meetings")
            meeting_adapter = HttpMeetingAdapter(settings, client)
            meeting_worker = MeetingWorker(
                async_session_factory,
                meeting_storage,
                meeting_adapter,
                MeetingMemory(
                    async_session_factory,
                    meeting_storage,
                    audio_storage,
                    embedding,
                    settings,
                    HttpMeetingMemoryAdapter(settings, client),
                ),
                settings,
            )
            meeting_cleanup = MeetingCleanup(async_session_factory, meeting_storage, settings)
            next_cleanup = 0.0
            while True:
                if time.monotonic() >= next_cleanup:
                    await worker.cleanup()
                    await meeting_cleanup.run()
                    HEARTBEAT_PATH.touch()
                    next_cleanup = time.monotonic() + settings.cleanup_interval_seconds
                try:
                    worked = await worker.process_once()
                    HEARTBEAT_PATH.touch()
                    worked = await process_ready_meeting(meeting_adapter, meeting_worker) or worked
                    HEARTBEAT_PATH.touch()
                except (SQLAlchemyError, OSError, ValueError):
                    logging.getLogger("app.speaker_worker").error("worker_iteration_failed")
                    worked = False
                if not worked:
                    await asyncio.sleep(settings.worker_poll_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run or probe the durable speaker worker")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        raise SystemExit(0 if healthcheck() else 1)
    asyncio.run(run())
