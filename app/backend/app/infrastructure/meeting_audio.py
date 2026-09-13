"""Bounded, opaque source storage; models remain behind the inference HTTP port."""

import hashlib
import io
import math
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import soundfile as sf  # type: ignore[import-untyped]

from app.domain.meeting import (
    MAX_SOURCE_BYTES,
    MAX_SOURCE_SECONDS,
    UPLOAD_PART_BYTES,
    clean_union,
)
from app.domain.meeting_samples import SourceFrameManifest, select_source_ranges
from app.services.speaker_ports import SpeakerError

PREVIEW_MAX_SECONDS = 30
PREVIEW_MAX_BYTES = 11520128


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
        self._preview_root = Path(os.path.abspath(root))
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
                if prefix[:4] == b"RIFF":
                    self._validate_riff_chunks(stream, prefix, expected_bytes)
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

    @staticmethod
    def _validate_riff_chunks(stream: BinaryIO, prefix: bytes, expected_bytes: int) -> None:
        # libsndfile tolerates truncated chunks and trailing bytes. A completed source
        # must account for every byte before that permissive decoder can accept it.
        if int.from_bytes(prefix[4:8], "little") + 8 != expected_bytes:
            raise SpeakerError("invalid_audio", 400)
        offset = 12
        while offset < expected_bytes:
            stream.seek(offset)
            header = stream.read(8)
            if len(header) != 8:
                raise SpeakerError("invalid_audio", 400)
            size = int.from_bytes(header[4:8], "little")
            # RIFF allows unknown chunks and requires a pad byte for odd lengths.
            offset += 8 + size + size % 2
            if offset > expected_bytes:
                raise SpeakerError("invalid_audio", 400)

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

    def preview(
        self,
        key: str,
        start: float,
        end: float,
        *,
        expected_bytes: int,
        expected_format: str,
        sample_rate: int,
        channels: int,
        duration_seconds: float,
    ) -> bytes:
        if (
            not all(math.isfinite(value) for value in (start, end))
            or start < 0
            or not 0 < end - start <= PREVIEW_MAX_SECONDS
            or end > duration_seconds
        ):
            raise SpeakerError("invalid_audio_range", 422)
        if (
            expected_format not in {"WAV", "FLAC"}
            or not 8000 <= sample_rate <= 192000
            or not 1 <= channels <= 8
            or not math.isfinite(duration_seconds)
            or not 0 < duration_seconds <= MAX_SOURCE_SECONDS
            or not 0 < expected_bytes <= MAX_SOURCE_BYTES
        ):
            raise SpeakerError("recording_unavailable", 410)
        first, last = round(start * sample_rate), round(end * sample_rate)
        if first >= last:
            raise SpeakerError("invalid_audio_range", 422)
        try:
            path = self._preview_path(key)
            before = path.stat(follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise SpeakerError("recording_unavailable", 410)
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            with os.fdopen(os.open(path, flags), "rb") as stream:
                opened = os.fstat(stream.fileno())
                if opened.st_size != expected_bytes or self._preview_identity(
                    opened
                ) != self._preview_identity(before):
                    raise SpeakerError("recording_unavailable", 410)
                prefix = stream.read(12)
                if expected_format == "WAV":
                    if prefix[:4] not in {b"RIFF", b"RF64"} or prefix[8:12] != b"WAVE":
                        raise SpeakerError("recording_unavailable", 410)
                    if prefix[:4] == b"RIFF":
                        self._validate_riff_chunks(stream, prefix, expected_bytes)
                elif not prefix.startswith(b"fLaC"):
                    raise SpeakerError("recording_unavailable", 410)
                stream.seek(0)
                with sf.SoundFile(stream) as source:
                    formats = {"FLAC"} if expected_format == "FLAC" else {"WAV", "WAVEX", "RF64"}
                    if (
                        source.format not in formats
                        or source.samplerate != sample_rate
                        or source.channels != channels
                        or source.frames != round(duration_seconds * sample_rate)
                        or last > source.frames
                    ):
                        raise SpeakerError("recording_unavailable", 410)
                    output = self._extract(source, [(first, last)], allow_clipped=True)
                # Observe the same opened file and opaque path after reading, including
                # deletion/replacement and in-place changes during extraction. This is
                # a metadata fence, not a fresh hash of the entire sealed recording.
                after = self._preview_path(key).stat(follow_symlinks=False)
                if (
                    self._preview_identity(opened)
                    != self._preview_identity(os.fstat(stream.fileno()))
                    or self._preview_identity(opened) != self._preview_identity(after)
                    or len(output) > PREVIEW_MAX_BYTES
                ):
                    raise SpeakerError("recording_unavailable", 410)
                return output
        except SpeakerError as exc:
            if exc.code == "recording_unavailable":
                raise
            raise SpeakerError("recording_unavailable", 410) from exc
        except (OSError, RuntimeError, ValueError) as exc:
            raise SpeakerError("recording_unavailable", 410) from exc

    def _preview_path(self, key: str) -> Path:
        if self._preview_root.resolve() != self._preview_root:
            raise SpeakerError("recording_unavailable", 410)
        return self.path(key)

    @staticmethod
    def _preview_identity(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_nlink,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

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
    def _extract(
        source: sf.SoundFile, ranges: list[tuple[int, int]], *, allow_clipped: bool = False
    ) -> bytes:
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
        if not allow_clipped and samples and clipped / samples > 0.05:
            raise SpeakerError("clipped_audio", 422)
        return output.getvalue()

    def remove(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)
