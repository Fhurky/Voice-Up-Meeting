#!/usr/bin/env python3
"""Exercise the real private HTTP service inside a GPU/network-none container.

Fixture repetition only proves software wiring. This does not measure speaker
recognition, gallery decisions or accuracy on held-out natural speech.
"""

import argparse
import io
import json
import logging
import math
import secrets
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import numpy as np
import soundfile as sf
import torch
import uvicorn
from pydantic import SecretStr

from voiceup_inference.api import create_app
from voiceup_inference.config import Settings


def run(fixtures: list[Path], *, cpu_profile: str | None = None) -> dict:
    key = secrets.token_urlsafe(48)
    device_options = {"device": "cpu", "runtime_profile": cpu_profile} if cpu_profile else {}
    settings = Settings(internal_key=SecretStr(key), host="127.0.0.1", port=8090, **device_options)
    logging.getLogger("voiceup.inference").disabled = True
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings),
            host=settings.host,
            port=settings.port,
            access_log=False,
            log_level="error",
            workers=1,
        )
    )
    startup_started = time.perf_counter()
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    records = []

    def request(path, payload=None, content_type="audio/wav", supplied_key=key):
        started = time.perf_counter()
        headers = {
            "Content-Type": content_type,
            "X-Inference-Key": supplied_key,
            "X-Job-Id": str(uuid4()),
            "X-Tenant-Id": str(uuid4()),
        }
        req = Request(f"http://127.0.0.1:8090{path}", data=payload, headers=headers)
        try:
            with urlopen(req, timeout=180) as response:
                return response.status, json.load(response), time.perf_counter() - started
        except HTTPError as exc:
            return exc.code, json.load(exc), time.perf_counter() - started

    def record(name, response, expected):
        status, body, elapsed = response
        if status != expected:
            raise RuntimeError(
                f"{name}: expected {expected}, received {status}: {body.get('detail')}"
            )
        entry = {"case": name, "status": status, "http_seconds": elapsed}
        if "embedding" in body:
            vector = body["embedding"]
            norm = math.sqrt(sum(value * value for value in vector))
            assert len(vector) == 192 and abs(norm - 1) < 1e-5
            assert body["device"] == settings.device
            if settings.device == "cpu":
                assert not any(name.startswith("gpu_") for name in body["quality"])
            else:
                assert body["quality"]["gpu_peak_allocated_bytes"] > 0
            entry.update({k: v for k, v in body.items() if k != "embedding"})
            entry["embedding_norm"] = norm
        elif "detail" in body:
            entry["error_code"] = body["detail"]["code"]
        else:
            entry.update(body)
        records.append(entry)

    try:
        deadline = time.monotonic() + 180
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("HTTP startup failed or exceeded 180 seconds")
            time.sleep(0.1)
        record("live", request("/live"), 200)
        record("ready", request("/ready"), 200)
        startup_seconds = time.perf_counter() - startup_started
        record(
            "invalid_audio",
            request("/v1/embeddings?purpose=identify", b"RIFF\x04\x00\x00\x00WAVE"),
            400,
        )
        record("unsupported_audio", request("/v1/embeddings?purpose=identify", b"invalid"), 415)
        record(
            "invalid_key",
            request("/v1/embeddings?purpose=identify", b"invalid", supplied_key="incorrect"),
            401,
        )
        silence = io.BytesIO()
        sf.write(silence, np.zeros(16000 * 12), 16000, format="WAV", subtype="PCM_16")
        record(
            "silence_quality_rejection",
            request("/v1/embeddings?purpose=enroll", silence.getvalue()),
            422,
        )
        for fixture in fixtures:
            payload = fixture.read_bytes()
            for purpose in ("enroll", "identify"):
                record(
                    f"constructed_fixture_{fixture.name}_{purpose}",
                    request(f"/v1/embeddings?purpose={purpose}", payload),
                    200,
                )
            samples, sample_rate = sf.read(io.BytesIO(payload), dtype="float32")
            flac = io.BytesIO()
            sf.write(flac, samples, sample_rate, format="FLAC", subtype="PCM_16")
            record(
                f"constructed_fixture_{fixture.name}_flac_identify",
                request("/v1/embeddings?purpose=identify", flac.getvalue(), "audio/flac"),
                200,
            )
        return {
            "purpose": "Real private HTTP software smoke; constructed public fixtures are not accuracy evidence",
            "python": __import__("sys").version.split()[0],
            "torch": torch.__version__,
            "cuda_build": torch.version.cuda,
            "device": settings.device,
            "runtime_profile": settings.runtime_profile,
            "gpu": None if settings.device == "cpu" else torch.cuda.get_device_name(0),
            "startup_seconds": startup_seconds,
            "startup_scope": "In-process HTTP startup including model verification/load/warmup; excludes container creation and initial Python imports",
            "request_order": "First constructed enrollment request precedes repeated warm identify requests; readiness already performed synthetic warmup",
            "checks": records,
        }
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.fixtures), indent=2))
