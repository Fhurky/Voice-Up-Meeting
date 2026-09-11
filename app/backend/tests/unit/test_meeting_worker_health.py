"""The worker remains healthy during its explicitly bounded meeting inference wait."""

import os
import time
from pathlib import Path

from app.core.config import get_settings
from app.scripts import speaker_worker


def test_heartbeat_budget_includes_meeting_chunk_timeout(tmp_path: Path, monkeypatch) -> None:
    marker = tmp_path / "health"
    marker.touch()
    settings = get_settings().model_copy(
        update={"job_timeout_seconds": 300, "meeting_chunk_timeout_seconds": 600}
    )
    monkeypatch.setattr(speaker_worker, "get_settings", lambda: settings)
    monkeypatch.setattr(speaker_worker, "HEARTBEAT_PATH", marker)
    now = time.time()
    os.utime(marker, (now - 500, now - 500))
    assert speaker_worker.healthcheck()
    os.utime(marker, (now - 700, now - 700))
    assert not speaker_worker.healthcheck()
