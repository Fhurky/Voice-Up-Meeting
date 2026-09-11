"""Real long silence sources, bounded reads and TCP uploads across a server process restart.

These are filesystem and HTTP durability observations, never model accuracy evidence.
"""

import asyncio
import hashlib
import json
import os
import socket
import struct
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.domain.meeting import MAX_SOURCE_SECONDS, UPLOAD_PART_BYTES
from app.domain.models.meeting import Meeting, MeetingUploadPart
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.speaker_ports import SpeakerError
from tests.integration import test_meeting_workflow as fixtures
from tests.integration.test_meeting_workflow import MeetingHarness

meeting_harness = fixtures.meeting_harness
pytestmark = pytest.mark.integration

SOURCE_PROBE = """
import io,json,resource,sys,time
from pathlib import Path
import soundfile as sf
from app.domain.meeting import analysis_windows
from app.infrastructure.meeting_audio import MeetingAudioStorage
path=Path(sys.argv[1])
storage=MeetingAudioStorage(path.parent)
start=time.monotonic()
def peak_rss():
    # ru_maxrss can retain the fork parent's earlier peak across exec; VmHWM
    # belongs to this executable's new Linux address space.
    rows=Path('/proc/self/status').read_text().splitlines()
    return int(next(row.split()[1] for row in rows if row.startswith('VmHWM:')))*1024
baseline=peak_rss()
info=storage.validate(path.name,path.stat().st_size,'WAV')
maximum_bytes=maximum_seconds=0
window_count=frames_read=0
core_frames=0
for index,left,first,last,right in analysis_windows(info.duration_seconds):
    payload=storage.window(path.name,left,right)
    maximum_bytes=max(maximum_bytes,len(payload))
    with sf.SoundFile(io.BytesIO(payload)) as reader:
        assert reader.channels==1 and reader.samplerate==16000
        assert reader.frames==round((right-left)*16000)
        assert reader.frames<=310*16000
        maximum_seconds=max(maximum_seconds,reader.frames/reader.samplerate)
        # Read every sample of every source window, not just WAV headers.
        for block in reader.blocks(blocksize=65536,dtype='float32'):
            assert not block.any()
            frames_read+=len(block)
    core_frames+=round((last-first)*16000)
    window_count+=1
assert core_frames==round(info.duration_seconds*16000)
peak=peak_rss()
print(json.dumps({'duration_seconds':info.duration_seconds,'size_bytes':path.stat().st_size,
 'sha256':info.sha256,'windows':window_count,'max_window_seconds':maximum_seconds,
 'max_window_payload_bytes':maximum_bytes,'core_frames':core_frames,
 'context_frames_read':frames_read,'baseline_rss_bytes':baseline,'peak_rss_bytes':peak,
 'incremental_rss_bytes':peak-baseline,'elapsed_seconds':time.monotonic()-start,
 'rss_method':'Linux /proc/self/status VmHWM of new address space',
 'rusage_peak_including_inherited_history_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 'model_calls':0,'audio_content':'generated silence'}))
"""


def silence_source(path: Path, frames: int, *, rate: int = 16000, channels: int = 1) -> int:
    """A complete PCM16 WAV; filesystem holes, when supported, contain real zero samples."""
    size = 44 + frames * channels * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        size - 8,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        rate,
        rate * channels * 2,
        channels * 2,
        16,
        b"data",
        frames * channels * 2,
    )
    with path.open("xb") as stream:
        stream.write(header)
        stream.seek(size - 1)
        stream.write(b"\x00")
        stream.flush()
        os.fsync(stream.fileno())
    assert path.stat().st_size == size
    return size


def evidence(name: str, result: dict) -> None:
    destination = os.environ.get("VOICEUP_LONG_SOURCE_EVIDENCE_DIR")
    if destination:
        root = Path(destination)
        root.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


@asynccontextmanager
async def real_http_server(harness: MeetingHarness, storage: Path, measurements: list[dict]):
    # The child imports a fresh FastAPI application and settings; no ASGITransport
    # or in-process dependency overrides are used for the measured HTTP requests.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = dict(os.environ)
    environment.update(
        {
            "VOICEUP_AUDIO_STORAGE_PATH": str(storage),
            "VOICEUP_INFERENCE_URL": "http://127.0.0.1:9",
            "VOICEUP_ENVIRONMENT": "test",
            "VOICEUP_LOG_LEVEL": "ERROR",
            "VOICEUP_LOCAL_ADMIN_LOGIN_ENABLED": "false",
            "VOICEUP_LOCAL_ADMIN_USERNAME": "",
        }
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-access-log",
        "--log-level",
        "error",
        env=environment,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    client = httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{port}{harness.settings.api_prefix}",
        headers=dict(harness.client.headers),
        timeout=90,
        trust_env=False,
    )
    try:
        for _ in range(200):
            if process.returncode is not None:
                pytest.fail(f"Long-source HTTP process exited: {process.returncode}")
            try:
                response = await client.get("/meetings?limit=1")
                if response.status_code == 200:
                    break
                pytest.fail(f"Long-source HTTP readiness status: {response.status_code}")
            except httpx.ConnectError:
                await asyncio.sleep(0.05)
        else:
            pytest.fail("Long-source HTTP process did not become ready")
        yield client, process.pid
    finally:
        await client.aclose()
        if process.returncode is None:
            status = Path(f"/proc/{process.pid}/status").read_text().splitlines()
            peak = int(next(row.split()[1] for row in status if row.startswith("VmHWM:"))) * 1024
            measurements.append({"peak_rss_bytes": peak, "rss_method": "Linux VmHWM"})
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()


async def put_part(client: httpx.AsyncClient, route: str, index: int, part: bytes) -> dict:
    response = await client.put(
        f"{route}/upload-parts/{index}",
        content=part,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Chunk-SHA256": hashlib.sha256(part).hexdigest(),
        },
    )
    assert response.status_code == 200, f"part HTTP status {response.status_code}"
    return response.json()


@pytest.mark.parametrize("hours", [1, 2, 4])
async def test_long_source_windows_and_tcp_upload_resume_after_process_restart(
    meeting_harness: MeetingHarness, hours: int
) -> None:
    harness = meeting_harness
    with tempfile.TemporaryDirectory(prefix="voiceup-long-source-") as directory:
        root = Path(directory)
        source = root / f"{uuid4().hex}.meeting"
        size = silence_source(source, hours * 3600 * 16000)
        probe = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            SOURCE_PROBE,
            str(source),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await asyncio.wait_for(probe.communicate(), 120)
        assert probe.returncode == 0, f"source reader exited {probe.returncode}"
        measurement = json.loads(stdout)
        assert measurement["duration_seconds"] == hours * 3600
        assert measurement["windows"] == hours * 12
        assert measurement["max_window_seconds"] == 310
        assert measurement["max_window_payload_bytes"] <= 310 * 16000 * 2 + 128
        assert measurement["peak_rss_bytes"] < 512 * 1024**2
        assert measurement["incremental_rss_bytes"] < 128 * 1024**2
        started = time.monotonic()
        storage = root / "uploads"
        servers: list[dict] = []
        key = str(uuid4())
        body = {
            "title": "Long silence source",
            "format": "WAV",
            "size_bytes": size,
            "language": "en",
            "auto_enroll": False,
            "participant_count": 50,
        }
        with source.open("rb") as stream:
            async with real_http_server(harness, storage, servers) as (
                client,
                first_pid,
            ):
                created = await client.post(
                    "/meetings", json=body, headers={"Idempotency-Key": key}
                )
                assert created.status_code == 201
                meeting = created.json()
                route = f"/meetings/{meeting['public_id']}"
                first_part = stream.read(UPLOAD_PART_BYTES)
                first_ack = await put_part(client, route, 0, first_part)
                assert first_ack["uploaded_bytes"] == UPLOAD_PART_BYTES
                assert first_ack["next_index"] == 1
            async with real_http_server(harness, storage, servers) as (
                client,
                second_pid,
            ):
                assert first_pid != second_pid
                recreated = await client.post(
                    "/meetings", json=body, headers={"Idempotency-Key": key}
                )
                assert (
                    recreated.status_code == 201
                    and recreated.json()["public_id"] == meeting["public_id"]
                )
                manifest = (await client.get(route + "/upload-parts")).json()
                assert manifest == first_ack
                assert await put_part(client, route, 0, first_part) == first_ack
                uploaded, index = UPLOAD_PART_BYTES, 1
                while part := stream.read(UPLOAD_PART_BYTES):
                    acknowledgement = await put_part(client, route, index, part)
                    uploaded += len(part)
                    index += 1
                    assert acknowledgement["uploaded_bytes"] == uploaded
                    assert acknowledgement["next_index"] == index
                assert uploaded == size
                completed = await client.post(route + "/complete")
                assert completed.status_code == 202
                state = completed.json()
                assert state["status"] == "queued"
                assert state["duration_seconds"] == hours * 3600
                assert state["sha256"] == measurement["sha256"]
                assert state["uploaded_bytes"] == size and state["total_chunks"] == hours * 12
                assert state["completed_chunks"] == 0 and state["observed_speakers"] == 0
                assert (await client.post(route + "/complete")).json() == state
                assert (await client.get(route + "/transcript")).json()["provisional"]
                # This test never invokes a model worker; cancelling the queued source
                # keeps the disposable test queue separate from later worker suites.
                assert (await client.post(route + "/cancel")).json()["status"] == "cancelled"
        async with harness.sessions() as session:
            row = await session.scalar(
                select(Meeting).where(Meeting.public_id == meeting["public_id"])
            )
            parts = list(
                await session.scalars(
                    select(MeetingUploadPart).where(MeetingUploadPart.meeting_id == row.meeting_id)
                )
            )
            assert len(parts) == index and row.next_chunk_index == 0
        measurement.update(
            {
                "http_upload_and_validation_seconds": time.monotonic() - started,
                "acknowledged_parts": index,
                "http_process_restart": True,
                "distinct_server_processes": 2,
                "resumed_part_index": 1,
                "idempotent_create_and_first_part": True,
                "final_upload_status": "queued",
                "cleanup_status": "cancelled",
                "model_worker_run": False,
                "ordinary_role": True,
                "transport": "real loopback TCP HTTP",
                "persistence": "PostgreSQL",
                "http_server_processes": servers,
            }
        )
        assert len(servers) == 2 and max(row["peak_rss_bytes"] for row in servers) < 512 * 1024**2
        evidence(f"long-source-{hours}h.json", measurement)


def test_source_duration_one_pcm_sample_over_four_hours_is_rejected(
    tmp_path: Path,
) -> None:
    key = f"{uuid4().hex}.meeting"
    size = silence_source(tmp_path / key, MAX_SOURCE_SECONDS * 16000 + 1)
    with pytest.raises(SpeakerError) as error:
        MeetingAudioStorage(tmp_path).validate(key, size, "WAV")
    assert error.value.code == "audio_limit"


HIGH_CHANNEL_PROBE = """
import io,json,time
from pathlib import Path
import soundfile as sf
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.meeting_worker import MeetingWorker
def peak_rss():
 rows=Path('/proc/self/status').read_text().splitlines()
 return int(next(row.split()[1] for row in rows if row.startswith('VmHWM:')))*1024
import sys
path=Path(sys.argv[1])
storage=MeetingAudioStorage(path.parent)
baseline=peak_rss()
start=time.monotonic()
info=storage.validate(path.name,path.stat().st_size,'WAV')
assert (info.duration_seconds,info.sample_rate,info.channels)==(310,192000,8)
stages=[]
for purpose in ('window','sample'):
 payload=storage.window(path.name,0,310) if purpose=='window' else storage.sample(path.name,[(0,310*192000)],192000)
 expected_seconds=310 if purpose=='window' else 60
 frames=0
 with sf.SoundFile(io.BytesIO(payload)) as reader:
  assert reader.channels==1 and reader.samplerate==192000
  assert reader.frames==expected_seconds*192000
  for block in reader.blocks(blocksize=65536,dtype='float32'):
   assert not block.any()
   frames+=len(block)
 stages.append({'purpose':purpose,'seconds':expected_seconds,'mono_payload_bytes':len(payload),
                'frames_actually_read':frames,'peak_rss_bytes':peak_rss()})
 del payload
print(json.dumps({'duration_seconds':info.duration_seconds,'sample_rate':info.sample_rate,
 'channels':info.channels,'source_bytes':path.stat().st_size,'source_sha256':info.sha256,
 'baseline_rss_bytes':baseline,'peak_rss_bytes':peak_rss(),'stages':stages,
 'elapsed_seconds':time.monotonic()-start,'model_calls':0,'worker_constructed':False,
 'measurement_scope':'Worker module imports plus validate/window/sample; no HTTP/model inference',
 'rss_method':'Linux /proc/self/status VmHWM of new address space','audio_content':'generated silence'}))
"""


async def test_maximum_rate_and_eight_channels_keep_worker_source_reads_bounded() -> None:
    with tempfile.TemporaryDirectory(prefix="voiceup-high-channel-source-") as directory:
        source = Path(directory) / f"{uuid4().hex}.meeting"
        size = silence_source(source, 310 * 192000, rate=192000, channels=8)
        assert size == 952320044
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            HIGH_CHANNEL_PROBE,
            str(source),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await asyncio.wait_for(process.communicate(), 120)
        assert process.returncode == 0, f"high-channel source reader exited {process.returncode}"
        result = json.loads(stdout)
        evidence("maximum-rate-eight-channels.json", result)
        assert result["peak_rss_bytes"] < 256 * 1024**2
        assert result["stages"][0]["mono_payload_bytes"] <= 310 * 192000 * 2 + 128
        assert result["stages"][1]["mono_payload_bytes"] <= 60 * 192000 * 2 + 128
