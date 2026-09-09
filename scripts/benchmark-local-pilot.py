"""Measure the public local pilot API without treating repeated speech as accuracy data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class BenchmarkFailure(Exception):
    """A bounded diagnostic that never includes credentials or HTTP payloads."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise BenchmarkFailure("redirect_refused")


class Api:
    def __init__(self, origin: str, prefix: str) -> None:
        parsed = urllib.parse.urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise BenchmarkFailure("a_loopback_http_origin_is_required")
        if not prefix.startswith("/") or prefix.startswith("//") or "?" in prefix or "#" in prefix:
            raise BenchmarkFailure("invalid_api_prefix")
        self.origin = origin.rstrip("/")
        self.prefix = prefix.rstrip("/")
        self.headers: dict[str, str] = {}
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            urllib.parse.urljoin(self.origin, self.prefix + path),
            data=payload,
            method=method,
            headers={**self.headers, **(headers or {})},
        )
        for attempt in range(2):
            try:
                with self.opener.open(request, timeout=60) as response:
                    data = response.read(1024 * 1024)
                    value = json.loads(data)
                    if not isinstance(value, dict):
                        raise BenchmarkFailure("unexpected_response_shape")
                    return value
            except urllib.error.HTTPError as exc:
                # Never print the body: even diagnostic payloads may include sensitive fields.
                raise BenchmarkFailure(f"http_{exc.code}") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                # Mutation calls supply the same idempotency key on the one network retry.
                if attempt:
                    raise BenchmarkFailure("http_transport_failure") from None
                time.sleep(1)
        raise BenchmarkFailure("http_transport_failure")

    def json(self, path: str, body: dict[str, Any], *, key: str | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Idempotency-Key"] = key
        return self.request("POST", path, payload=json.dumps(body).encode(), headers=headers)


class DeviceMemorySampler:
    """Sample total device memory, including other processes; this is not allocator peak."""

    def __init__(self, enabled: bool) -> None:
        self.executable = shutil.which("nvidia-smi") if enabled else None
        self.samples: list[dict[str, Any]] = []
        self.unavailable = enabled and self.executable is None
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.executable:
            self.thread = threading.Thread(target=self._sample, daemon=True)
            self.thread.start()

    def _sample(self) -> None:
        while not self.stop_event.is_set():
            try:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    [
                        self.executable or "nvidia-smi",
                        "--query-gpu=index,memory.used,memory.total",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                    creationflags=flags,
                )
                for line in result.stdout.splitlines():
                    index, used, total = (int(value.strip()) for value in line.split(","))
                    self.samples.append(
                        {
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "index": index,
                            "used_mib": used,
                            "total_mib": total,
                        }
                    )
            except (OSError, ValueError, subprocess.SubprocessError):
                self.unavailable = True
                return
            self.stop_event.wait(0.5)

    def finish(self) -> dict[str, Any]:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=6)
        maxima: dict[int, int] = {}
        for sample in self.samples:
            index = sample["index"]
            maxima[index] = max(maxima.get(index, 0), sample["used_mib"])
        return {
            "measurement": "sampled total device memory used; includes other processes; not PyTorch allocator peak",
            "interval_seconds": 0.5,
            "unavailable": self.unavailable,
            "max_sampled_used_mib_by_device_index": maxima,
            "sample_count": len(self.samples),
            "samples": self.samples,
        }


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        raise BenchmarkFailure("missing_server_timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise BenchmarkFailure("naive_server_timestamp")
    return parsed


def percentile(values: list[float], percent: float) -> float:
    """Nearest-rank percentile, fixed before collecting measurements."""
    if not values:
        raise BenchmarkFailure("no_measurements")
    return sorted(values)[max(0, math.ceil(percent / 100 * len(values)) - 1)]


def run_job(
    api: Api, recording_id: str, *, key: str, timeout: float, poll_seconds: float
) -> dict[str, Any]:
    start = time.monotonic()
    job = api.json(
        "/speaker-jobs", {"recording_public_id": recording_id, "purpose": "identify"}, key=key
    )
    while job.get("status") in {"queued", "running"}:
        if time.monotonic() - start > timeout:
            raise BenchmarkFailure("job_poll_deadline_exceeded")
        time.sleep(poll_seconds)
        job = api.request(
            "GET", "/speaker-jobs/" + urllib.parse.quote(str(job["public_id"]), safe="")
        )
    if job.get("status") != "succeeded":
        code = (job.get("error") or {}).get("code", "unknown")
        if not isinstance(code, str) or not code.replace("_", "").isalnum():
            code = "unknown"
        raise BenchmarkFailure("job_failed_" + code)
    if job.get("attempt_count") != 1:
        raise BenchmarkFailure("retried_job_cannot_count_as_latency_evidence")
    result = job.get("result") or {}
    if not str(result.get("device", "")).startswith("cuda"):
        raise BenchmarkFailure("cuda_result_required")
    created, started, finished = (
        parse_timestamp(job.get(key)) for key in ["created_at", "started_at", "finished_at"]
    )
    if not created <= started <= finished:
        raise BenchmarkFailure("inconsistent_server_timestamps")
    return {
        "job_public_id": job["public_id"],
        "attempt_count": 1,
        "queue_seconds": (started - created).total_seconds(),
        "execution_seconds": (finished - started).total_seconds(),
        "server_total_seconds": (finished - created).total_seconds(),
        "observed_round_trip_seconds": time.monotonic() - start,
        "device": result["device"],
        "model_id": result["model_id"],
        "model_revision": result["model_revision"],
        "speech_seconds": result["speech_seconds"],
        "windows_count": result["windows_count"],
        "decision": result["decision"],
    }


def execute(args: argparse.Namespace, report: dict[str, Any]) -> None:
    credentials = json.loads(args.credentials.read_text(encoding="utf-8-sig"))
    api = Api(args.base_url or credentials["url"], args.api_prefix)
    with wave.open(str(args.audio), "rb") as source:
        duration = source.getnframes() / source.getframerate()
    if abs(duration - 30) > 0.01:
        raise BenchmarkFailure("benchmark_requires_a_30_second_wav")
    audio = args.audio.read_bytes()
    if len(audio) > 50 * 1024 * 1024:
        raise BenchmarkFailure("audio_size_limit")
    report["source"] = {
        "sha256": hashlib.sha256(audio).hexdigest(),
        "duration_seconds": duration,
        "classification": args.fixture_label,
        "accuracy_evidence": False,
    }
    authenticated = api.json(
        "/auth/login", {"username": credentials["username"], "password": credentials["password"]}
    )
    api.headers = {
        "Authorization": "Bearer " + authenticated["access_token"],
        "x-tenant-id": authenticated["user"]["tenant_id"],
    }
    boundary = "voiceup" + uuid4().hex
    payload = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="benchmark.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
        + audio
        + f"\r\n--{boundary}--\r\n".encode()
    )
    upload_start = time.monotonic()
    recording = api.request(
        "POST",
        "/recordings",
        payload=payload,
        headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "Idempotency-Key": str(uuid4()),
        },
    )
    report["upload_seconds"] = time.monotonic() - upload_start
    if recording.get("sha256") != report["source"]["sha256"]:
        raise BenchmarkFailure("upload_hash_mismatch")
    report["recording_public_id"] = recording["public_id"]
    sampler = DeviceMemorySampler(args.sample_device_memory)
    sampler.start()
    try:
        print("Running one excluded warm-up job.", flush=True)
        report["warmup"] = run_job(
            api,
            recording["public_id"],
            key=str(uuid4()),
            timeout=args.job_timeout,
            poll_seconds=args.poll_seconds,
        )
        for index in range(20):
            result = run_job(
                api,
                recording["public_id"],
                key=str(uuid4()),
                timeout=args.job_timeout,
                poll_seconds=args.poll_seconds,
            )
            report["jobs"].append(result)
            print(
                f"Measured {index + 1}/20: execution {result['execution_seconds']:.3f}s; queue {result['queue_seconds']:.3f}s",
                flush=True,
            )
    finally:
        report["device_memory"] = sampler.finish()
    values = [item["execution_seconds"] for item in report["jobs"]]
    report["execution_summary"] = {
        "jobs": len(values),
        "percentile_method": "nearest-rank",
        "p50_seconds": percentile(values, 50),
        "p95_seconds": percentile(values, 95),
        "max_seconds": max(values),
        "target_p95_seconds": 30,
        "target_met": percentile(values, 95) <= 30,
    }
    report["status"] = "measured"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--credentials",
        type=Path,
        required=True,
        help="Ignored local JSON with url, username and password",
    )
    parser.add_argument(
        "--audio",
        type=Path,
        required=True,
        help="Explicit 30-second WAV; never altered by the benchmark",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--api-prefix", default="/api/voiceup/v1")
    parser.add_argument(
        "--fixture-label",
        default="Repeated public speech fixture; not held-out speaker accuracy data",
    )
    parser.add_argument("--job-timeout", type=float, default=900)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--sample-device-memory", action="store_true")
    args = parser.parse_args()
    if args.job_timeout <= 0 or not 0.1 <= args.poll_seconds <= 10:
        parser.error(
            "timeout must be positive and poll interval must be between 0.1 and 10 seconds"
        )
    report: dict[str, Any] = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "incomplete",
        "protocol": "One upload, one excluded warm-up, 20 sequential single-attempt CUDA identification jobs",
        "accuracy_evidence": False,
        "jobs": [],
    }
    exit_code = 0
    try:
        execute(args, report)
    except BenchmarkFailure as exc:
        report["error_code"] = str(exc)
        print(f"Benchmark incomplete: {exc}", file=sys.stderr)
        exit_code = 1
    except (OSError, ValueError, KeyError, TypeError, wave.Error):
        report["error_code"] = "invalid_local_input_or_response"
        print("Benchmark incomplete: invalid local input or response.", file=sys.stderr)
        exit_code = 1
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
