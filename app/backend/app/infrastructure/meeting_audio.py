"""Bounded, opaque source storage; models remain behind the inference HTTP port."""

import hashlib
import io
import math
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf  # type: ignore[import-untyped]

from app.domain.meeting import (
    MAX_SOURCE_BYTES,
    MAX_SOURCE_SECONDS,
    UPLOAD_PART_BYTES,
    clean_union,
)
from app.domain.meeting_samples import SourceFrameManifest, select_source_ranges
from app.services.speaker_ports import SpeakerError


@dataclass(frozen=True, slots=True)
class MeetingSourceInfo:
    sha256: str
    duration_seconds: float
    sample_rate: int
    channels: int


@dataclass(frozen=True, slots=True)
class MeetingAudioSample:
    data: bytes
    manifest: SourceFrameManifest
    sha256: str


class MeetingAudioStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}\.meeting", key):
            raise SpeakerError("recording_unavailable", 410)
        target = self.root / key
        if target.is_symlink() or target.is_junction() or target.resolve().parent != self.root:
            raise SpeakerError("recording_unavailable", 410)
        return target

    def append(self, key: str, offset: int, data: bytes, sha256: str) -> None:
        if (
            not data
            or len(data) > UPLOAD_PART_BYTES
            or offset < 0
            or offset + len(data) > MAX_SOURCE_BYTES
        ):
            raise SpeakerError("audio_limit", 413)
        if hashlib.sha256(data).hexdigest() != sha256:
            raise SpeakerError("chunk_hash_mismatch", 409)
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path(key)
        if (not path.exists() and offset) or (path.exists() and path.stat().st_size < offset):
            raise SpeakerError("recording_unavailable", 410)
        if shutil.disk_usage(self.root).free < len(data) + 16 * 1024 * 1024:
            raise SpeakerError("storage_unavailable", 503)
        with path.open("r+b" if path.exists() else "xb") as destination:
            destination.seek(offset)
            destination.write(data)
            # A crash before the DB acknowledgement may leave a tail. The next fenced
            # write replaces precisely that unacknowledged tail, never committed bytes.
            destination.truncate()
            destination.flush()
            os.fsync(destination.fileno())

    def validate(self, key: str, expected_bytes: int, expected_format: str) -> MeetingSourceInfo:
        path = self.path(key)
        if not path.exists() or path.stat().st_size != expected_bytes:
            raise SpeakerError("upload_incomplete", 409)
        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                prefix = stream.read(12)
                valid = (expected_format == "FLAC" and prefix.startswith(b"fLaC")) or (
                    expected_format == "WAV"
                    and prefix[:4] in {b"RIFF", b"RF64"}
                    and prefix[8:12] == b"WAVE"
                )
                if not valid:
                    raise SpeakerError("unsupported_audio", 415)
                stream.seek(0)
                while block := stream.read(1024 * 1024):
                    digest.update(block)
            with sf.SoundFile(path) as source:
                duration = source.frames / source.samplerate
                if duration > MAX_SOURCE_SECONDS:
                    raise SpeakerError("audio_limit", 413)
                if (
                    duration <= 0
                    or not 1 <= source.channels <= 8
                    or not 8000 <= source.samplerate <= 192000
                ):
                    raise SpeakerError("invalid_audio", 400)
                frames = 0
                for samples in source.blocks(blocksize=65536, dtype="float32", always_2d=True):
                    frames += len(samples)
                    peak = float(abs(samples).max())
                    if not math.isfinite(peak) or peak > 1:
                        raise SpeakerError("invalid_audio", 400)
                if frames != source.frames:
                    raise SpeakerError("invalid_audio", 400)
                return MeetingSourceInfo(
                    digest.hexdigest(), duration, source.samplerate, source.channels
                )
        except SpeakerError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise SpeakerError("invalid_audio", 400) from exc

    def window(self, key: str, start: float, end: float) -> bytes:
        if (
            not all(math.isfinite(value) for value in (start, end))
            or start < 0
            or not 0 < end - start <= 310
        ):
            raise SpeakerError("invalid_audio", 400)
        try:
            with sf.SoundFile(self.path(key)) as source:
                if end > source.frames / source.samplerate + 1e-6:
                    raise SpeakerError("invalid_audio", 400)
                return self._extract(
                    source,
                    [
                        (
                            round(start * source.samplerate),
                            round(end * source.samplerate),
                        )
                    ],
                )
        except (OSError, RuntimeError, ValueError) as exc:
            raise SpeakerError("recording_unavailable", 410) from exc

    def sample(self, key: str, ranges: list[tuple[int, int]], sample_rate: int) -> bytes:
        return self.sample_with_manifest(key, ranges, sample_rate).data

    def sample_with_manifest(
        self, key: str, ranges: list[tuple[int, int]], sample_rate: int
    ) -> MeetingAudioSample:
        try:
            with sf.SoundFile(self.path(key)) as source:
                if source.samplerate != sample_rate:
                    raise SpeakerError("invalid_audio", 400)
                selected = select_source_ranges(
                    tuple(clean_union(ranges, [], 0, source.frames)),
                    source.frames,
                    sample_rate,
                )
                if not selected:
                    raise SpeakerError("insufficient_speech", 422)
                manifest = SourceFrameManifest(sample_rate, source.frames, selected)
                data = self._extract(source, list(selected))
                return MeetingAudioSample(data, manifest, hashlib.sha256(data).hexdigest())
        except (OSError, RuntimeError, ValueError) as exc:
            raise SpeakerError("recording_unavailable", 410) from exc

    @staticmethod
    def _extract(source: sf.SoundFile, ranges: list[tuple[int, int]]) -> bytes:
        output = io.BytesIO()
        clipped, samples = 0, 0
        with sf.SoundFile(
            output,
            mode="w",
            samplerate=source.samplerate,
            channels=1,
            format="WAV",
            subtype="PCM_16",
        ) as destination:
            for start, end in ranges:
                source.seek(start)
                remaining = end - start
                while remaining:
                    block = source.read(min(65536, remaining), dtype="float32", always_2d=True)
                    if not len(block):
                        raise SpeakerError("invalid_audio", 400)
                    peak = float(abs(block).max())
                    if not math.isfinite(peak) or peak > 1:
                        raise SpeakerError("invalid_audio", 400)
                    clipped += int((abs(block) >= 0.999).sum())
                    samples += block.size
                    destination.write(block.mean(axis=1))
                    remaining -= len(block)
        if samples and clipped / samples > 0.05:
            raise SpeakerError("clipped_audio", 422)
        return output.getvalue()

    def remove(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)
