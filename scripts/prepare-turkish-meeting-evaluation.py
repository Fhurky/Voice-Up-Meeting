#!/usr/bin/env python3
"""Download pinned Turkish references, then prepare bounded offline meeting mixtures."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
import wave
from array import array
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "tugrulbayrak/Real-TurnTurk"
REVISION = "db8f20f6eb6b215ec75fb466374fc5cc861b91df"
PROTOCOL = "voiceup-real-turnturk-v1"
SOURCE_MANIFEST_SHA256 = "02c9494ad9137d642258f7cc3a4720b4f3821b3fc2368d22699d33e08da6ea4b"
PRESETS = {
    "development": (PROTOCOL, 0, 180),
    "window300": ("voiceup-real-turnturk-window300-v1", 300, 300),
    "window600": ("voiceup-real-turnturk-window600-v1", 600, 300),
}
SAMPLE_RATE = 16000
CASES = (
    ("rec01", ("p06", "p03")),
    ("rec02", ("p04", "p06")),
    ("rec03", ("p03", "p01")),
    ("rec04", ("p01", "p02")),
    ("rec05", ("p05", "p06")),
    ("rec06", ("p04", "p01")),
)
# Pinned publisher tree: ordinary objects use Git blob SHA-1; LFS audio uses SHA-256.
AUDIO = (
    (17967198, "9055508a6d32188d73966ac21a283af5b5a52be51488d51ef8f3acd5f790e06e"),
    (15275728, "6886bc8519b25ef0fc6f2215b7bbd3554a114cdfa8c4989f79315b8ed1c8acab"),
    (18210793, "4600d91d44298ad8724dfccdae50c3542ac0faf4bcbdae0633800e57e7860cf8"),
    (19791434, "6ece72a58ed8fce6a8db5117a845be6c8a1a96bf92c8ed19fc673e7927a08bdb"),
    (22810564, "453553d612069265422c2bc15075f6e436a8d6160428a63669592fd85d1ca539"),
    (23484117, "92a353a502f46ca4a648a24a2d22038735f060d45f86d4caee79a3db0c41da63"),
    (15660124, "40fd92f7d3e1c489a11a3d2f3e193239a275573419f5b95be3ee34353dad93f7"),
    (16952257, "f9c0f90eed778f5af32b3fb246a437ea9c7bb81e73fce4253a7721aa17d2d0b5"),
    (24101273, "ff06542b86acb3964bf76ca17196927e3df41eb12175a4416a76494a83cc11fc"),
    (29854761, "ced675a6d24783ba2f958db5af9606fbda04bc0baa0c8a34cb9593909d8612a0"),
    (17853760, "f78357bb2881ef966618088325e110915b0be6650a83700e6603999329530cb8"),
    (16427465, "092480b2c79f02d8f8904833b76419812d80cdc850e728a33a8af059016a1464"),
)
TEXT = (
    (26976, "57aa88655acb1d8c98e43d3b4e7874719710ca7a"),
    (26344, "75a76a001baa62e5b3f861feed08bd5120eb861c"),
    (40642, "67e0b6ca904934f9c70323237161f2b3699ecafa"),
    (27660, "44a35d319eb153a080a9ae0936e51df5d0408b01"),
    (43403, "a094ba7bef74b8d009dd8ed0fc75ed044ccbbb22"),
    (26781, "7b6f184cc6569cdc86f53cf89541b643b9c992fd"),
)
ACTIVITY = (
    (807361, "0d70656973aabfdd182929e266269d5185b2a856"),
    (867441, "f6c8980a33ad9f5e6fa7bc9282c703aaa7368ff3"),
    (1260291, "ad41c44782e8bff963c0bdf1f34ff8940f40d935"),
    (827109, "0bd4f2e561d3a4f228c32a9712d56ea403f3f6e1"),
    (1319073, "68891d4ba6395e1826dac68f3364b8946b4cd8c1"),
    (863051, "e7591c6ae131202181cb20c6169726c43a9e3d93"),
)


def source_inventory() -> list[dict]:
    rows = []

    def add(path: str, value: tuple[int, str], algorithm: str) -> None:
        rows.append(
            {
                "path": path,
                "size_bytes": value[0],
                "upstream_algorithm": algorithm,
                "upstream_digest": value[1],
            }
        )

    add("README.md", (16464, "2ee510e8ea465ba87b428fe67bbef78aca2bf1f5"), "git-blob-sha1")
    for index, (key, people) in enumerate(CASES):
        for channel, speaker, offset in zip(("L", "R"), people, (0, 1), strict=True):
            add(f"{key}/{key}__{channel}_{speaker}.webm", AUDIO[index * 2 + offset], "sha256")
        add(f"{key}/{key}__text.csv", TEXT[index], "git-blob-sha1")
        add(f"{key}/{key}__speech_activity.csv", ACTIVITY[index], "git-blob-sha1")
    return rows


def checked_path(path: Path) -> Path:
    absolute = path.absolute()
    for candidate in (absolute, *absolute.parents):
        if candidate.is_symlink() or (
            hasattr(candidate, "is_junction") and candidate.is_junction()
        ):
            raise ValueError("unsafe_source_path")
    return absolute


def source_path(root: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or ":" in relative
        or part.is_absolute()
        or any(item in {"", ".", ".."} for item in relative.split("/"))
    ):
        raise ValueError("unsafe_source_path")
    root = checked_path(root)
    target = checked_path(root.joinpath(*part.parts))
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("unsafe_source_path")
    return target


def digest(path: Path) -> str:
    with checked_path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_source(row: dict, path: Path) -> str:
    path = checked_path(path)
    if not path.is_file() or path.stat().st_size != row["size_bytes"]:
        raise ValueError("source_size_mismatch")
    sha256 = hashlib.sha256()
    blob = hashlib.sha1(b"blob " + str(row["size_bytes"]).encode() + b"\0")
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            sha256.update(chunk)
            blob.update(chunk)
    expected = sha256.hexdigest() if row["upstream_algorithm"] == "sha256" else blob.hexdigest()
    if expected != row["upstream_digest"]:
        raise ValueError("source_hash_mismatch")
    return sha256.hexdigest()


def validate_url(url: str) -> None:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not (host == "huggingface.co" or host.endswith(".hf.co"))
    ):
        raise ValueError("untrusted_download_url")


class SourceRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def publish(temporary: Path, target: Path) -> None:
    checked_path(target)
    try:
        os.link(temporary, target)
    except FileExistsError:
        if target.stat().st_size != temporary.stat().st_size or digest(target) != digest(temporary):
            raise FileExistsError("existing_output_conflict") from None


def write_once(target: Path, payload: bytes) -> None:
    target = checked_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".turkish-", suffix=".partial", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        publish(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def fetch_source(row: dict, root: Path, *, opener=None) -> dict:
    target = source_path(root, row["path"])
    if target.exists():
        return {**row, "sha256": verify_source(row, target)}
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".turkish-", suffix=".partial", dir=target.parent)
    temporary = Path(name)
    url = f"https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/{row['path']}"
    validate_url(url)
    connection = opener or build_opener(SourceRedirects())
    try:
        with os.fdopen(descriptor, "wb") as stream:
            request = Request(url, headers={"User-Agent": "VoiceUp-dataset-preparation/1"})
            with connection.open(request, timeout=60) as response:
                validate_url(response.geturl())
                total = 0
                while chunk := response.read(min(1024 * 1024, row["size_bytes"] - total + 1)):
                    total += len(chunk)
                    if total > row["size_bytes"]:
                        raise ValueError("source_size_mismatch")
                    stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        content_digest = verify_source(row, temporary)
        publish(temporary, target)
        return {**row, "sha256": content_digest}
    finally:
        temporary.unlink(missing_ok=True)


def download_sources(root: Path) -> dict:
    files = []
    for index, row in enumerate(source_inventory(), start=1):
        files.append(fetch_source(row, root))
        print(json.dumps({"stage": "source_verified", "completed": index, "total": 25}), flush=True)
    manifest = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "revision": REVISION,
        "license": "apache-2.0",
        "files": files,
    }
    write_once(root / "source_manifest.json", json_bytes(manifest))
    return manifest


def verify_sources(root: Path) -> dict:
    path = checked_path(root / "source_manifest.json")
    if not path.is_file() or path.stat().st_size > 32768:
        raise ValueError("invalid_source_manifest")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    inventory = source_inventory()
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "repository", "revision", "license", "files"}
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["repository"] != REPOSITORY
        or manifest["revision"] != REVISION
        or manifest["license"] != "apache-2.0"
        or not isinstance(manifest["files"], list)
        or len(manifest["files"]) != len(inventory)
    ):
        raise ValueError("invalid_source_manifest")
    for actual, expected in zip(manifest["files"], inventory, strict=True):
        if (
            not isinstance(actual, dict)
            or set(actual) != {*expected, "sha256"}
            or any(actual[key] != value for key, value in expected.items())
            or not isinstance(actual["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", actual["sha256"]) is None
        ):
            raise ValueError("invalid_source_manifest")
        if verify_source(expected, source_path(root, expected["path"])) != actual["sha256"]:
            raise ValueError("source_hash_mismatch")
    return manifest


def timestamp(value: str) -> float:
    if not re.fullmatch(r"\d{2}:\d{2}:\d{2}\.\d{3}", value):
        raise ValueError("invalid_transcript_reference")
    hours, minutes, seconds = value.split(":")
    if int(minutes) >= 60 or float(seconds) >= 60:
        raise ValueError("invalid_transcript_reference")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read_references(
    activity: Path,
    transcript: Path,
    key: str,
    people: tuple[str, str],
    duration: float,
    *,
    start_seconds: float = 0,
) -> tuple[list[dict], list[dict], int]:
    if (
        not math.isfinite(start_seconds)
        or start_seconds < 0
        or not math.isfinite(duration)
        or duration <= 0
        or not math.isclose(start_seconds * 16, round(start_seconds * 16), abs_tol=1e-9)
    ):
        raise ValueError("invalid_excerpt_selection")
    end_seconds = start_seconds + duration
    intervals = []
    previous = dict.fromkeys(people, -1)
    active: dict[str, float | None] = dict.fromkeys(people)
    with checked_path(activity).open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["recording", "frame", "t_sec", "person", "speaking"]:
            raise ValueError("invalid_activity_reference")
        for row in rows:
            if (
                set(row) != set(rows.fieldnames)
                or row["recording"] != key
                or row["person"] not in people
                or row["speaking"] not in {"0", "1"}
            ):
                raise ValueError("invalid_activity_reference")
            person = row["person"]
            frame, seconds = int(row["frame"]), float(row["t_sec"])
            if (
                frame != previous[person] + 1
                or not math.isfinite(seconds)
                or not math.isclose(seconds, frame / 16, abs_tol=0.000001)
            ):
                raise ValueError("activity_timeline_mismatch")
            previous[person] = frame
            if not start_seconds <= seconds < end_seconds:
                continue
            seconds -= start_seconds
            if row["speaking"] == "1" and active[person] is None:
                active[person] = seconds
            elif row["speaking"] == "0" and active[person] is not None:
                intervals.append(
                    {"speaker_id": person, "start_seconds": active[person], "end_seconds": seconds}
                )
                active[person] = None
    for person in people:
        if (previous[person] + 1) / 16 < end_seconds:
            raise ValueError("activity_coverage_incomplete")
        if active[person] is not None:
            intervals.append(
                {"speaker_id": person, "start_seconds": active[person], "end_seconds": duration}
            )
    text: dict[str, list[str]] = {person: [] for person in people}
    previous_start = dict.fromkeys(people, -1.0)
    crossing = 0
    with checked_path(transcript).open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["start_time", "end_time", "speaker", "text"]:
            raise ValueError("invalid_transcript_reference")
        for row in rows:
            if set(row) != set(rows.fieldnames) or row["speaker"] not in people or not row["text"]:
                raise ValueError("invalid_transcript_reference")
            start, end = timestamp(row["start_time"]), timestamp(row["end_time"])
            person = row["speaker"]
            if start < previous_start[person] or end <= start:
                raise ValueError("invalid_transcript_reference")
            previous_start[person] = start
            contained = start_seconds <= start < end <= end_seconds
            if start < end_seconds and end > start_seconds and not contained:
                crossing += 1
            if contained:
                text[person].append(row["text"])
    return (
        sorted(intervals, key=lambda row: (row["start_seconds"], row["speaker_id"])),
        [{"speaker_id": person, "text": " ".join(text[person])} for person in people],
        crossing,
    )


def new_timeline_audit() -> dict:
    return {
        "source_samples": 0,
        "source_frames": 0,
        "first_pts_seconds": None,
        "last_pts_seconds": None,
        "last_pts_end_seconds": None,
        "timestamp_repeated_count": 0,
        "timestamp_gap_count": 0,
        "timestamp_overlap_count": 0,
        "max_abs_pts_sample_clock_delta_seconds": 0.0,
    }


def audit_source_frame(state: dict, start: float, samples: int, *, sample_rate: int) -> None:
    if not math.isfinite(start) or samples <= 0 or sample_rate <= 0:
        raise ValueError("invalid_source_audio_timeline")
    if state["first_pts_seconds"] is None:
        state["first_pts_seconds"] = start
    last_end = state["last_pts_end_seconds"]
    if last_end is not None:
        delta = start - last_end
        state["timestamp_gap_count"] += int(delta > 0.000001)
        state["timestamp_overlap_count"] += int(delta < -0.000001)
        state["timestamp_repeated_count"] += int(start == state["last_pts_seconds"])
    sample_clock = state["source_samples"] / sample_rate
    state["max_abs_pts_sample_clock_delta_seconds"] = max(
        state["max_abs_pts_sample_clock_delta_seconds"], abs(start - sample_clock)
    )
    state["source_samples"] += samples
    state["source_frames"] += 1
    state["last_pts_seconds"] = start
    state["last_pts_end_seconds"] = start + samples / sample_rate


def append_pcm(destination: array, samples: array, state: dict) -> None:
    source_start = state["output_samples"]
    offset = state.get("selection_start_samples", 0)
    start = max(source_start, offset)
    end = min(offset + len(destination), source_start + len(samples))
    if start < end:
        destination[start - offset : end - offset] = samples[
            start - source_start : end - source_start
        ]
    state["output_samples"] += len(samples)


def reference_ends(activity: Path, transcript: Path, people: tuple[str, str]) -> dict:
    # The complete CSV contract is validated by read_references before this audit.
    result = {
        person: {"activity_end_seconds": 0.0, "transcript_end_seconds": 0.0} for person in people
    }
    with activity.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            result[row["person"]]["activity_end_seconds"] = max(
                result[row["person"]]["activity_end_seconds"], float(row["t_sec"]) + 1 / 16
            )
    with transcript.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            result[row["speaker"]]["transcript_end_seconds"] = max(
                result[row["speaker"]]["transcript_end_seconds"], timestamp(row["end_time"])
            )
    return result


def decode_channel(path: Path, duration: float, *, start_seconds: float = 0) -> tuple[array, dict]:
    if (
        not math.isfinite(start_seconds)
        or start_seconds < 0
        or not math.isfinite(duration)
        or not 0 < duration <= 600
    ):
        raise ValueError("invalid_excerpt_selection")
    try:
        import av
    except ImportError as error:
        raise RuntimeError("prepared_pyav_runtime_required") from error
    target = array("h", [0]) * round(duration * SAMPLE_RATE)
    state = {"output_samples": 0}
    offset = round(start_seconds * SAMPLE_RATE)
    if offset:
        state["selection_start_samples"] = offset
    audit = new_timeline_audit()
    resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)

    def consume(decoded) -> None:
        samples = array("h", bytes(decoded.planes[0])[: decoded.samples * 2])
        if sys.byteorder != "little":
            samples.byteswap()
        append_pcm(target, samples, state)

    with av.open(str(checked_path(path))) as container:
        if len(container.streams.audio) != 1:
            raise ValueError("source_audio_stream_mismatch")
        stream = container.streams.audio[0]
        if stream.codec_context.channels != 1 or stream.codec_context.sample_rate != 48000:
            raise ValueError("source_audio_format_mismatch")
        for frame in container.decode(stream):
            if frame.pts is None or frame.time_base is None:
                raise ValueError("source_audio_timestamps_missing")
            audit_source_frame(
                audit, float(frame.pts * frame.time_base), frame.samples, sample_rate=48000
            )
            # Preserve every decoded sample; publisher WebM packet timestamps can repeat.
            # This policy is explicit in the protocol, with source timestamp diagnostics.
            frame.pts = None
            for decoded in resampler.resample(frame):
                consume(decoded)
        for decoded in resampler.resample(None):
            consume(decoded)
        if state["output_samples"] < offset + len(target):
            raise ValueError("source_audio_coverage_incomplete")
    return target, {
        **state,
        **audit,
        "source_decoded_seconds": audit["source_samples"] / 48000,
        "resampled_seconds": state["output_samples"] / SAMPLE_RATE,
        "selected_samples": len(target),
        "decoder": f"PyAV-{av.__version__}",
        "timeline_policy": "decoded-sample-clock-v1",
        "timeline_alignment": "unverified-source-timestamps",
    }


def write_mixture(left: array, right: array, output: Path) -> str:
    if left.typecode != "h" or right.typecode != "h" or not left or len(left) != len(right):
        raise ValueError("invalid_pcm_sources")
    combined = array("h", ((a + b) // 2 for a, b in zip(left, right, strict=True)))
    if sys.byteorder != "little":
        combined.byteswap()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as stream:
        stream.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        stream.writeframes(combined.tobytes())
    write_once(output, buffer.getvalue())
    return digest(output)


def json_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def resolve_selection(preset: str, duration: float | None = None) -> tuple[str, float, float]:
    if preset not in PRESETS:
        raise ValueError("invalid_excerpt_selection")
    protocol_id, start_seconds, default_duration = PRESETS[preset]
    if duration is None:
        duration = float(default_duration) if preset == "development" else default_duration
    if (
        type(duration) not in (int, float)
        or not math.isfinite(duration)
        or not 0 < duration <= (180 if preset == "development" else 300)
        or (preset != "development" and duration != default_duration)
    ):
        raise ValueError("invalid_excerpt_selection")
    return protocol_id, start_seconds, duration


def source_binding(index: int) -> dict:
    key, _people = CASES[index]
    return {
        "recording": key,
        "left_sha256": AUDIO[index * 2][1],
        "right_sha256": AUDIO[index * 2 + 1][1],
        "activity_git_blob_sha1": ACTIVITY[index][1],
        "text_git_blob_sha1": TEXT[index][1],
    }


def prepare(
    root: Path, output: Path, *, duration: float | None = None, preset: str = "development"
) -> dict:
    protocol_id, start_seconds, duration = resolve_selection(preset, duration)
    verify_sources(root)
    source_manifest_sha256 = digest(root / "source_manifest.json")
    if preset != "development" and source_manifest_sha256 != SOURCE_MANIFEST_SHA256:
        raise ValueError("source_manifest_hash_mismatch")
    output = checked_path(output)
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    for index, (key, people) in enumerate(CASES):
        source = source_path(root, key)
        intervals, reference, crossing = read_references(
            source / f"{key}__speech_activity.csv",
            source / f"{key}__text.csv",
            key,
            people,
            duration,
            start_seconds=start_seconds,
        )
        left, left_info = decode_channel(
            source / f"{key}__L_{people[0]}.webm", duration, start_seconds=start_seconds
        )
        right, right_info = decode_channel(
            source / f"{key}__R_{people[1]}.webm", duration, start_seconds=start_seconds
        )
        endpoints = reference_ends(
            source / f"{key}__speech_activity.csv", source / f"{key}__text.csv", people
        )
        for person, info in zip(people, (left_info, right_info), strict=True):
            info["reference_ends"] = endpoints[person]
            info["audio_minus_activity_end_seconds"] = (
                info["source_decoded_seconds"] - endpoints[person]["activity_end_seconds"]
            )
            info["audio_minus_transcript_end_seconds"] = (
                info["source_decoded_seconds"] - endpoints[person]["transcript_end_seconds"]
            )
        output_path = output / f"{key}.wav"
        output_sha256 = write_mixture(left, right, output_path)
        del left, right
        cases.append(
            {
                "key": key,
                "path": output_path.name,
                "sha256": output_sha256,
                "duration_seconds": duration,
                "expected_speakers": 2,
                "speaker_ids": list(people),
                "intervals": intervals,
                "reference": reference,
                "excluded_crossing_utterances": crossing,
                "decoding": {"left": left_info, "right": right_info},
            }
        )
        if preset != "development":
            cases[-1]["source"] = source_binding(index)
        print(
            json.dumps({"stage": "fixture_prepared", "completed": len(cases), "total": 6}),
            flush=True,
        )
    protocol = {
        "schema_version": 1,
        "protocol_id": protocol_id,
        "language": "tr",
        "dataset_revision": REVISION,
        "source_manifest_sha256": source_manifest_sha256,
        "selection": {"start_seconds": start_seconds, "duration_seconds": duration},
        "reference_quality": {"activity": "automatic-silero", "transcript": "unverified-source"},
        "mixing": {"sample_rate": SAMPLE_RATE, "format": "PCM_16", "gain_per_channel": 0.5},
        "timeline_policy": "decoded-sample-clock-v1",
        "timeline_alignment": "unverified-source-timestamps",
        "cases": cases,
        "limitations": [
            "Six real speakers in dyadic conversations do not establish 50-speaker meeting accuracy.",
            "Source VAD is automatic; transcript human verification is not certified by the publisher.",
            "Only fully contained transcript utterances are referenced; crossing-edge speech remains in audio and hypotheses, biasing diagnostic text scores.",
            "The first 180 seconds are fixed development excerpts, not full meetings or an unseen-speaker benchmark.",
            "The two channels retain decoded sample order at fixed half gain; no turn concatenation or silence removal.",
            "Source WebM timestamps repeat and jump in some channels. Decoded sample clock replaces packet timestamps; source-reference alignment remains unverified and diagnostics record the discrepancy.",
        ],
    }
    if preset != "development":
        protocol["limitations"][3] = (
            "Fixed unused temporal excerpts from the same six source sessions and people; "
            "not independent sessions or an unseen-speaker benchmark."
        )
    write_once(output / "protocol.json", json_bytes(protocol))
    return protocol


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root", type=Path, default=ROOT / "data/turkish/real-turnturk" / REVISION
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs/2026-09-13-turkish-evaluation/fixtures"
    )
    parser.add_argument(
        "--download", action="store_true", help="Acquire and verify only pinned source files"
    )
    parser.add_argument(
        "--prepare", action="store_true", help="Decode locally with already-installed PyAV"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify the local pinned source inventory"
    )
    parser.add_argument("--preset", choices=tuple(PRESETS), default="development")
    args = parser.parse_args()
    if not any((args.download, args.prepare, args.verify)):
        parser.error("Select --download, --prepare or --verify")
    if args.download:
        download_sources(args.data_root)
    if args.prepare:
        if args.preset != "development" and args.output == parser.get_default("output"):
            parser.error("A new preset requires an explicit separate --output directory")
        result = prepare(args.data_root, args.output, preset=args.preset)
        print(json.dumps({"protocol_id": result["protocol_id"], "cases": len(result["cases"])}))
    elif args.verify or args.download:
        result = verify_sources(args.data_root)
        print(json.dumps({"stage": "sources_verified", "files": len(result["files"])}))


if __name__ == "__main__":
    main()
