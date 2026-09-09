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
from app.infrastructure.speaker_inference import HttpEmbeddingAdapter
from app.services.speaker_worker import SpeakerWorker

HEARTBEAT_PATH = Path("/tmp/voiceup-worker-health")


def healthcheck() -> bool:
    try:
        age = time.time() - HEARTBEAT_PATH.stat().st_mtime
    except OSError:
        return False
    return 0 <= age <= get_settings().job_timeout_seconds + 60


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.inference_key is None:
        raise RuntimeError("VOICEUP_INFERENCE_KEY is required by the worker")
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            worker = SpeakerWorker(
                async_session_factory,
                AudioStorage(settings),
                HttpEmbeddingAdapter(settings, client),
                settings,
            )
            next_cleanup = 0.0
            while True:
                if time.monotonic() >= next_cleanup:
                    await worker.cleanup()
                    HEARTBEAT_PATH.touch()
                    next_cleanup = time.monotonic() + settings.cleanup_interval_seconds
                try:
                    worked = await worker.process_once()
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
