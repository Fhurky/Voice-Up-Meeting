"""Bounded source validation and opaque, application-owned file storage."""

import asyncio
import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import soundfile as sf  # type: ignore[import-untyped]

from app.core.config import Settings
from app.services.speaker_ports import SpeakerError


class UploadSource(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True, slots=True)
class StoredAudio:
    key: str
    sha256: str
    size_bytes: int
    format: str
    duration_seconds: float


class AudioStorage:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.audio_storage_path.resolve()
        self.max_bytes = settings.audio_max_bytes
        self.max_seconds = settings.audio_max_seconds

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}\.audio", key):
            raise SpeakerError("recording_unavailable", 410)
        target = (self.root / key).resolve()
        if target.parent != self.root:
            raise SpeakerError("recording_unavailable", 410)
        return target

    async def receive(self, source: UploadSource, filename: str | None) -> StoredAudio:
        if Path(filename or "").suffix.lower() not in {".wav", ".flac"}:
            raise SpeakerError("unsupported_audio", 415)
        await asyncio.to_thread(self.root.mkdir, parents=True, exist_ok=True)
        key = f"{uuid4().hex}.audio"
        path = self.path(key)
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("xb") as destination:
                while chunk := await source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise SpeakerError("audio_limit", 413)
                    digest.update(chunk)
                    await asyncio.to_thread(destination.write, chunk)
            format_name, duration = await asyncio.to_thread(self.validate, path)
            return StoredAudio(key, digest.hexdigest(), size, format_name, duration)
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    def validate(self, path: Path) -> tuple[str, float]:
        try:
            header = path.open("rb")
            with header:
                prefix = header.read(12)
            if not (
                prefix.startswith(b"fLaC")
                or (prefix[:4] in {b"RIFF", b"RF64"} and prefix[8:12] == b"WAVE")
            ):
                raise SpeakerError("unsupported_audio", 415)
            with sf.SoundFile(path) as audio:
                if audio.format not in {"WAV", "WAVEX", "RF64", "FLAC"}:
                    raise SpeakerError("unsupported_audio", 415)
                duration = audio.frames / audio.samplerate
                if duration > self.max_seconds:
                    raise SpeakerError("audio_limit", 413)
                if (
                    duration <= 0
                    or not 1 <= audio.channels <= 8
                    or not 8000 <= audio.samplerate <= 192000
                ):
                    raise SpeakerError("invalid_audio", 400)
                frames = 0
                for block in audio.blocks(blocksize=65536, dtype="float32", always_2d=True):
                    frames += len(block)
                    if not math.isfinite(float(abs(block).max())):
                        raise SpeakerError("invalid_audio", 400)
                if frames != audio.frames:
                    raise SpeakerError("invalid_audio", 400)
                return ("FLAC" if audio.format == "FLAC" else "WAV", duration)
        except SpeakerError:
            raise
        except (RuntimeError, ValueError, OSError) as exc:
            raise SpeakerError("invalid_audio", 400) from exc

    async def read(self, key: str) -> bytes:
        path = self.path(key)
        try:
            if path.stat().st_size > self.max_bytes:
                raise SpeakerError("audio_limit", 413)
            return await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            raise SpeakerError("recording_unavailable", 410) from exc

    async def remove(self, key: str) -> None:
        await asyncio.to_thread(self.path(key).unlink, missing_ok=True)
