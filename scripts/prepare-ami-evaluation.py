#!/usr/bin/env python3
"""Acquire pinned AMI dev/test meetings and references for the public benchmark protocol.

Reference RTTM/UEM files are verified against Git blob identities at a pinned setup
commit. The AMI mirror publishes no digests, so audio is checked against the
committed size and its SHA-256 is recorded on first acquisition (trust on first use).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts/ami-evaluation-manifest.json"
PROTOCOL = "voiceup-ami-public-benchmark-v1"
SETUP_REPOSITORY = "pyannote/AMI-diarization-setup"
SETUP_REVISION = "67c2d539286e89f68952d5dcf83912bd9f01dfae"
AUDIO_BASE = "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus"
CONDITIONS = {"headset": "Mix-Headset", "array1": "Array1-01"}
# The AMI mirror only serves wget clients; without a host wget, BusyBox wget from the
# admitted digest-pinned backend base image performs the transfer.
WGET_IMAGE = (
    "python:3.13-alpine3.23@sha256:7ea3f82de8ea6d4fb7e5d2bbe3fe3c9d931700b7a529f1fe5769e42abe514ca1"
)
REFERENCE_HOSTS = frozenset({"raw.githubusercontent.com"})
AUDIO_HOSTS = frozenset({"groups.inf.ed.ac.uk"})
MEETING_RE = re.compile(r"[A-Z]{2}[0-9]{4}[a-d]?")
MAX_REFERENCE_BYTES = 4 * 1024 * 1024
MAX_AUDIO_BYTES = 512 * 1024 * 1024
SAMPLE_RATE = 16000

Downloader = Callable[[str, Path], None]


def load_manifest(path: Path = MANIFEST) -> dict:
    document = json.loads(checked_path(path).read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("setup_repository") != SETUP_REPOSITORY
        or document.get("setup_revision") != SETUP_REVISION
        or document.get("setup_license") != "apache-2.0"
        or document.get("audio_base_url") != AUDIO_BASE
        or document.get("audio_license") != "cc-by-4.0"
        or document.get("conditions") != CONDITIONS
        or not isinstance(document.get("meetings"), list)
        or not document["meetings"]
    ):
        raise ValueError("invalid_ami_manifest")
    seen = set()
    for row in document["meetings"]:
        name = row.get("meeting") if isinstance(row, dict) else None
        if (
            not isinstance(name, str)
            or MEETING_RE.fullmatch(name) is None
            or name in seen
            or row.get("split") not in {"dev", "test"}
            or set(row) != {"meeting", "split", "references", "audio"}
            or set(row["references"]) != {"rttm", "uem"}
            or set(row["audio"]) != set(CONDITIONS)
        ):
            raise ValueError("invalid_ami_manifest")
        seen.add(name)
        for kind, reference in row["references"].items():
            folder = "only_words/rttms" if kind == "rttm" else "uems"
            if (
                reference.get("path") != f"{folder}/{row['split']}/{name}.{kind}"
                or not 0 < reference.get("size_bytes", 0) <= MAX_REFERENCE_BYTES
                or re.fullmatch(r"[0-9a-f]{40}", reference.get("git_blob_sha1", "")) is None
            ):
                raise ValueError("invalid_ami_manifest")
        for condition, audio in row["audio"].items():
            if (
                audio.get("file") != f"{name}.{CONDITIONS[condition]}.wav"
                or not 44 < audio.get("size_bytes", 0) <= MAX_AUDIO_BYTES
            ):
                raise ValueError("invalid_ami_manifest")
    return document


def checked_path(path: Path) -> Path:
    absolute = path.absolute()
    for candidate in (absolute, *absolute.parents):
        if candidate.is_symlink() or (
            hasattr(candidate, "is_junction") and candidate.is_junction()
        ):
            raise ValueError("unsafe_path")
    return absolute


def inside(root: Path, *parts: str) -> Path:
    for part in parts:
        if not part or part in {".", ".."} or "/" in part or "\\" in part or ":" in part:
            raise ValueError("unsafe_path")
    root = checked_path(root)
    target = checked_path(root.joinpath(*parts))
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("unsafe_path")
    return target


def validate_url(url: str, hosts: frozenset[str]) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.hostname not in hosts
    ):
        raise ValueError("untrusted_download_url")


class ReferenceRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        validate_url(newurl, REFERENCE_HOSTS)
        return super().redirect_request(request, response, code, message, headers, newurl)


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def file_sha256(path: Path) -> str:
    with checked_path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def publish(temporary: Path, target: Path) -> None:
    checked_path(target)
    try:
        os.link(temporary, target)
    except FileExistsError:
        if file_sha256(target) != file_sha256(temporary):
            raise FileExistsError("existing_output_conflict") from None


def write_once(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".ami-", suffix=".partial", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        publish(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def reference_payload(reference: dict, *, opener=None) -> bytes:
    url = f"https://raw.githubusercontent.com/{SETUP_REPOSITORY}/{SETUP_REVISION}/{reference['path']}"
    validate_url(url, REFERENCE_HOSTS)
    connection = opener or build_opener(ReferenceRedirects())
    request = Request(url, headers={"User-Agent": "VoiceUp-dataset-preparation/1"})
    with connection.open(request, timeout=60) as response:
        payload = response.read(reference["size_bytes"] + 1)
    verify_reference(reference, payload)
    return payload


def verify_reference(reference: dict, payload: bytes) -> None:
    if len(payload) != reference["size_bytes"] or git_blob_sha1(payload) != reference["git_blob_sha1"]:
        raise ValueError("reference_hash_mismatch")


def wget_download(url: str, temporary: Path) -> None:
    validate_url(url, AUDIO_HOSTS)
    host_wget = shutil.which("wget")
    if host_wget:
        command = [host_wget, "--quiet", "--tries=3", "--output-document", str(temporary), url]
    else:
        command = [
            "docker", "run", "--rm", "--pull", "never",
            "--volume", f"{temporary.parent}:/out",
            WGET_IMAGE, "wget", "-q", "-O", f"/out/{temporary.name}", url,
        ]
    result = subprocess.run(command, capture_output=True, timeout=3600, check=False)
    if result.returncode:
        raise RuntimeError("audio_download_failed")


def fetch_audio(name: str, audio: dict, target: Path, *, downloader: Downloader = wget_download) -> str:
    if target.exists():
        if target.stat().st_size != audio["size_bytes"]:
            raise ValueError("audio_size_mismatch")
        return file_sha256(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.partial")
    temporary.unlink(missing_ok=True)
    try:
        downloader(f"{AUDIO_BASE}/{name}/audio/{audio['file']}", temporary)
        if not temporary.is_file() or temporary.stat().st_size != audio["size_bytes"]:
            raise ValueError("audio_size_mismatch")
        wav_info(temporary)
        digest = file_sha256(temporary)
        publish(temporary, target)
        return digest
    finally:
        temporary.unlink(missing_ok=True)


def pcm_data(path: Path) -> tuple[int, int]:
    """Locate the PCM16 16 kHz mono data chunk as (offset, size) without decoding samples."""
    path = checked_path(path)
    total = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError("unsupported_audio_format")
        fmt = None
        while chunk := stream.read(8):
            if len(chunk) != 8:
                break
            kind, size = chunk[:4], struct.unpack("<I", chunk[4:])[0]
            if kind == b"fmt ":
                fmt = struct.unpack("<HHIIHH", stream.read(16))
                stream.seek(size - 16, os.SEEK_CUR)
            elif kind == b"data":
                if fmt is None:
                    break
                audio_format, channels, rate, _, _, bits = fmt
                if (audio_format, channels, rate, bits) != (1, 1, SAMPLE_RATE, 16):
                    raise ValueError("unsupported_audio_format")
                offset = stream.tell()
                if size % 2 or offset + size > total:
                    raise ValueError("unsupported_audio_format")
                return offset, size
            else:
                stream.seek(size + (size & 1), os.SEEK_CUR)
    raise ValueError("unsupported_audio_format")


def wav_info(path: Path) -> dict:
    _, size = pcm_data(path)
    return {"sample_rate": SAMPLE_RATE, "duration_seconds": round(size / (2 * SAMPLE_RATE), 3)}


def canonical_wav(source: Path, target: Path) -> str:
    """Write the upload copy: a 44-byte PCM header and the source's sample bytes unchanged.

    AMI files carry broadcast-wave metadata chunks, and some end with a stray byte that
    no chunk accounts for; the meeting API rejects such uploads. Samples are not decoded,
    resampled or altered.
    """
    offset, size = pcm_data(source)
    header = b"RIFF" + struct.pack("<I", 36 + size) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SAMPLE_RATE, 2 * SAMPLE_RATE, 2, 16)
    header += b"data" + struct.pack("<I", size)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".ami-", suffix=".partial", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output, checked_path(source).open("rb") as stream:
            output.write(header)
            stream.seek(offset)
            remaining = size
            while remaining:
                block = stream.read(min(remaining, 1024 * 1024))
                if not block:
                    raise ValueError("unsupported_audio_format")
                output.write(block)
                remaining -= len(block)
            output.flush()
            os.fsync(output.fileno())
        publish(temporary, target)
        return file_sha256(target)
    finally:
        temporary.unlink(missing_ok=True)


def rttm_speakers(payload: bytes, meeting: str) -> list[str]:
    speakers = set()
    for line in payload.decode("utf-8").splitlines():
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 8 or fields[0] != "SPEAKER" or fields[1] != meeting:
            raise ValueError("invalid_rttm")
        if float(fields[3]) < 0 or float(fields[4]) <= 0:
            raise ValueError("invalid_rttm")
        speakers.add(fields[7])
    if not speakers:
        raise ValueError("invalid_rttm")
    return sorted(speakers)


def uem_bounds(payload: bytes, meeting: str) -> tuple[float, float]:
    rows = [line.split() for line in payload.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != 1 or len(rows[0]) != 4 or rows[0][0] != meeting:
        raise ValueError("invalid_uem")
    start, end = float(rows[0][2]), float(rows[0][3])
    if not 0 <= start < end:
        raise ValueError("invalid_uem")
    return start, end


def prepare(
    data_root: Path,
    *,
    conditions: tuple[str, ...] = tuple(CONDITIONS),
    meetings: frozenset[str] | None = None,
    manifest: dict | None = None,
    opener=None,
    downloader: Downloader = wget_download,
) -> dict:
    manifest = manifest or load_manifest()
    root = checked_path(data_root)
    rows = [row for row in manifest["meetings"] if meetings is None or row["meeting"] in meetings]
    if meetings is not None and {row["meeting"] for row in rows} != meetings:
        raise ValueError("unknown_meeting")
    protocol_meetings = []
    for number, row in enumerate(rows, start=1):
        name = row["meeting"]
        references = {}
        for kind, reference in row["references"].items():
            target = inside(root, "references", kind, f"{name}.{kind}")
            if target.exists():
                payload = target.read_bytes()
                verify_reference(reference, payload)
            else:
                payload = reference_payload(reference, opener=opener)
                write_once(target, payload)
            references[kind] = payload
        start, end = uem_bounds(references["uem"], name)
        audio = {}
        for condition in conditions:
            source = inside(root, "raw", condition, row["audio"][condition]["file"])
            source_digest = fetch_audio(name, row["audio"][condition], source, downloader=downloader)
            target = inside(root, "audio", condition, row["audio"][condition]["file"])
            audio[condition] = {
                "path": f"audio/{condition}/{target.name}",
                "sha256": canonical_wav(source, target),
                "size_bytes": target.stat().st_size,
                "source_sha256": source_digest,
                "source_size_bytes": row["audio"][condition]["size_bytes"],
                **wav_info(target),
            }
        protocol_meetings.append(
            {
                "meeting": name,
                "split": row["split"],
                "speakers": rttm_speakers(references["rttm"], name),
                "uem": [start, end],
                "rttm": f"references/rttm/{name}.rttm",
                "audio": audio,
            }
        )
        print(json.dumps({"stage": "meeting_ready", "completed": number, "total": len(rows)}), flush=True)
    protocol = {
        "schema_version": 2,
        "protocol": PROTOCOL,
        "setup_repository": SETUP_REPOSITORY,
        "setup_revision": SETUP_REVISION,
        "conditions": list(conditions),
        "meetings": protocol_meetings,
    }
    payload = (json.dumps(protocol, indent=2, sort_keys=True) + "\n").encode()
    target = inside(root, "protocol.json")
    if target.exists() and target.read_bytes() != payload:
        raise FileExistsError("existing_protocol_conflict")
    write_once(target, payload)
    return protocol


def verify(data_root: Path) -> dict:
    """Offline check: recompute every recorded digest; no network access."""
    root = checked_path(data_root)
    protocol = json.loads(inside(root, "protocol.json").read_text(encoding="utf-8"))
    manifest = {row["meeting"]: row for row in load_manifest()["meetings"]}
    if protocol.get("protocol") != PROTOCOL or protocol.get("setup_revision") != SETUP_REVISION:
        raise ValueError("invalid_protocol")
    for row in protocol["meetings"]:
        source = manifest[row["meeting"]]
        for kind in ("rttm", "uem"):
            verify_reference(
                source["references"][kind],
                inside(root, "references", kind, f"{row['meeting']}.{kind}").read_bytes(),
            )
        for condition, audio in row["audio"].items():
            name = source["audio"][condition]["file"]
            for target, size, digest in (
                (inside(root, "raw", condition, name), audio["source_size_bytes"], audio["source_sha256"]),
                (inside(root, "audio", condition, name), audio["size_bytes"], audio["sha256"]),
            ):
                if target.stat().st_size != size or file_sha256(target) != digest:
                    raise ValueError("audio_hash_mismatch")
    return protocol


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data/ami" / SETUP_REVISION)
    parser.add_argument("--download", action="store_true", help="Acquire, verify and write protocol.json")
    parser.add_argument("--verify", action="store_true", help="Verify local files offline")
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--meetings", help="Comma-separated subset for smoke runs")
    args = parser.parse_args()
    if args.download == args.verify:
        parser.error("Select exactly one of --download or --verify")
    if args.download:
        conditions = tuple(item for item in args.conditions.split(",") if item)
        if not conditions or any(item not in CONDITIONS for item in conditions):
            parser.error("Unknown condition")
        subset = frozenset(args.meetings.split(",")) if args.meetings else None
        protocol = prepare(args.data_root, conditions=conditions, meetings=subset)
    else:
        protocol = verify(args.data_root)
    print(json.dumps({"protocol": protocol["protocol"], "meetings": len(protocol["meetings"])}))


if __name__ == "__main__":
    main()
