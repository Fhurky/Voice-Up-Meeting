"""Latency arithmetic and local-only transport for the benchmark runner."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark-local-pilot.py"
SPEC = importlib.util.spec_from_file_location("local_benchmark", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def test_nearest_rank_p95_for_twenty_jobs() -> None:
    assert benchmark.percentile(list(range(1, 21)), 95) == 19
    assert benchmark.percentile(list(range(1, 21)), 50) == 10


@pytest.mark.parametrize(
    "origin", ["http://example.com", "http://user:password@127.0.0.1", "http://127.0.0.1?secret=x"]
)
def test_benchmark_never_accepts_remote_or_credentialed_origin(origin: str) -> None:
    with pytest.raises(benchmark.BenchmarkFailure):
        benchmark.Api(origin, "/api/voiceup/v1")


def test_api_prefix_cannot_replace_loopback_host() -> None:
    with pytest.raises(benchmark.BenchmarkFailure):
        benchmark.Api("http://127.0.0.1:8081", "//example.com")


def test_server_timestamps_must_include_timezone() -> None:
    with pytest.raises(benchmark.BenchmarkFailure, match="naive_server_timestamp"):
        benchmark.parse_timestamp("2026-09-09T00:00:00")
    assert benchmark.parse_timestamp("2026-09-09T00:00:00Z").utcoffset().total_seconds() == 0
