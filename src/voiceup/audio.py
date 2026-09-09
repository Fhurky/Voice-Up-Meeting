"""Audio preparation and conservative extraction of non-overlapping speech."""

from dataclasses import dataclass
from math import gcd, isfinite
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


@dataclass(frozen=True)
class Audio:
    samples: np.ndarray
    sample_rate: int = 16000

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate


@dataclass(frozen=True)
class Turn:
    start: float
    end: float
    speaker: str


def load_audio(path: str | Path, channel: int | None = None) -> Audio:
    """Read libsndfile formats. Keep separate participant channels separate upstream."""
    if channel is not None and (isinstance(channel, bool) or not isinstance(channel, int)):
        raise ValueError("Kanal indeksi bir tam sayı olmalı.")
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Ses dosyası bulunamadı: {path}")
    try:
        samples, rate = sf.read(path, dtype="float32", always_2d=True)
    except (RuntimeError, sf.LibsndfileError) as exc:
        raise ValueError(
            "Ses okunamadı. Önce FFmpeg ile WAV veya FLAC dosyasına dönüştürün."
        ) from exc
    if not len(samples) or rate <= 0 or not np.isfinite(samples).all():
        raise ValueError("Ses boş veya geçersiz örnekler içeriyor.")
    if channel is None:
        mono = samples.mean(axis=1)
    elif not 0 <= channel < samples.shape[1]:
        raise ValueError(f"Kanal 0 ile {samples.shape[1] - 1} arasında olmalı.")
    else:
        mono = samples[:, channel]
    if rate != 16000:
        factor = gcd(rate, 16000)
        mono = resample_poly(mono, 16000 // factor, rate // factor)
    return Audio(np.ascontiguousarray(mono, dtype=np.float32))


def validate_turns(turns: list[Turn], duration: float) -> list[Turn]:
    if not isinstance(duration, (int, float)) or not isfinite(duration) or duration <= 0:
        raise ValueError("Kayıt süresi sonlu ve pozitif olmalı.")
    for turn in turns:
        if (
            not isinstance(turn.start, (int, float))
            or not isinstance(turn.end, (int, float))
            or not isfinite(turn.start)
            or not isfinite(turn.end)
            or turn.start < 0
            or turn.start >= duration
            or turn.end <= turn.start
            or turn.end > duration + 0.02
            or not isinstance(turn.speaker, str)
            or not turn.speaker.strip()
        ):
            raise ValueError(f"Geçersiz konuşma aralığı: {turn}")
    return sorted(
        [Turn(t.start, min(t.end, duration), t.speaker) for t in turns],
        key=lambda t: (t.start, t.end, t.speaker),
    )


def merge_spans(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def clean_spans(turns: list[Turn], speaker: str) -> list[tuple[float, float]]:
    """Subtract ALL other speakers, including internal/nested overlaps."""
    own = merge_spans([(t.start, t.end) for t in turns if t.speaker == speaker])
    others = merge_spans([(t.start, t.end) for t in turns if t.speaker != speaker])
    clean: list[tuple[float, float]] = []
    for start, end in own:
        cursor = start
        for other_start, other_end in others:
            if other_end <= cursor:
                continue
            if other_start >= end:
                break
            if other_start > cursor:
                clean.append((cursor, other_start))
            cursor = max(cursor, other_end)
            if cursor >= end:
                break
        if cursor < end:
            clean.append((cursor, end))
    return clean


def speakers_overlap(turns: list[Turn], first: str, second: str) -> bool:
    return any(
        max(a.start, b.start) < min(a.end, b.end)
        for a in turns
        if a.speaker == first
        for b in turns
        if b.speaker == second
    )


def speech_windows(
    spans: list[tuple[float, float]], minimum: float = 3.0, maximum: float = 8.0
) -> list[tuple[float, float]]:
    """Use independent continuous chunks; do not stitch many tiny utterances together."""
    if minimum <= 0 or maximum < minimum:
        raise ValueError("Geçersiz pencere süreleri.")
    result = []
    for start, end in spans:
        duration = end - start
        if duration < minimum:
            continue
        count = max(1, int(np.ceil(duration / maximum)))
        if duration / count < minimum:
            continue
        boundaries = np.linspace(start, end, count + 1)
        result.extend((float(a), float(b)) for a, b in zip(boundaries[:-1], boundaries[1:]))
    return result
