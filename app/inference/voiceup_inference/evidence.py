"""Recover fragmented speech without replacing sufficient continuous evidence."""

from dataclasses import replace
from typing import Literal

import numpy as np

from voiceup.audio import Audio, Turn, clean_spans, speech_windows
from voiceup.identity import normalize_embedding
from voiceup.pipeline import Embedder, Evidence, extract_evidence

PreprocessingVersion = Literal["vad-windows-v1", "vad-packed-fallback-v1"]


def _usable(samples: np.ndarray) -> bool:
    # Check each original block before joining: a loud fragment must not make
    # quiet or clipped fragments count toward the enrollment speech minimum.
    if not len(samples) or not np.isfinite(samples).all():
        return False
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    clipping = float(np.mean(np.abs(samples) >= 0.999))
    return rms >= 1e-4 and clipping <= 0.05


def _usable_blocks(audio: Audio, turns: list[Turn]) -> list[np.ndarray]:
    pieces = []
    for start, end in clean_spans(turns, "probe"):
        # Long blocks use the exact original quality-check boundaries; only
        # shorter speech regions gain eligibility for the packing fallback.
        blocks = speech_windows([(start, end)]) if end - start >= 3 else [(start, end)]
        for first, last in blocks:
            samples = audio.samples[
                round(first * audio.sample_rate) : round(last * audio.sample_rate)
            ]
            if len(samples) >= 1.5 * audio.sample_rate and _usable(samples):
                pieces.append(samples)
    return pieces


def extract_pilot_evidence(
    audio: Audio,
    turns: list[Turn],
    embedder: Embedder,
    purpose: Literal["enroll", "identify"],
) -> tuple[Evidence, PreprocessingVersion]:
    minimum_seconds, minimum_windows = (10, 2) if purpose == "enroll" else (3, 1)
    baseline = extract_evidence(audio, turns, "probe", embedder)
    if baseline.reason == "inconsistent_voice_windows" or (
        baseline.embedding is not None
        and baseline.used_seconds >= minimum_seconds - 1e-6
        and baseline.windows >= minimum_windows
    ):
        return baseline, "vad-windows-v1"

    pieces = _usable_blocks(audio, turns)
    # Count original PCM samples, not elapsed wall time or the number of regions.
    if sum(len(piece) for piece in pieces) < minimum_seconds * audio.sample_rate:
        return baseline, "vad-windows-v1"
    # A repeated A/B mixture can look identical in every packed window. Compare
    # the original regions before pooling; short guards never become profile
    # evidence and cannot bypass the existing 3–8 second window requirement.
    guards = np.stack(
        [
            normalize_embedding(embedder.encode(piece, audio.sample_rate), embedder.dimension)
            for piece in pieces
        ]
    )
    similarities = guards @ guards.T
    guard_consistency = (
        float(np.min(similarities[np.triu_indices(len(guards), 1)])) if len(guards) > 1 else 1.0
    )
    if guard_consistency < 0.55:
        return replace(
            baseline,
            embedding=None,
            consistency=guard_consistency,
            reason="inconsistent_voice_windows",
        ), "vad-packed-fallback-v1"
    samples = np.ascontiguousarray(np.concatenate(pieces), dtype=np.float32)
    packed = Audio(samples, audio.sample_rate)
    candidate = extract_evidence(packed, [Turn(0.0, packed.duration, "probe")], "probe", embedder)
    candidate = replace(candidate, clean_seconds=baseline.clean_seconds)
    if candidate.embedding is not None:
        agreement = float(np.min(guards @ candidate.embedding))
        consistency = min(
            candidate.consistency if candidate.consistency is not None else 1.0,
            guard_consistency,
            agreement,
        )
        candidate = replace(candidate, consistency=consistency)
        if agreement < 0.55:
            candidate = replace(candidate, embedding=None, reason="inconsistent_voice_windows")
    if candidate.embedding is not None and baseline.embedding is not None:
        agreement = float(np.dot(candidate.embedding, baseline.embedding))
        consistency = min(
            candidate.consistency if candidate.consistency is not None else 1.0,
            baseline.consistency if baseline.consistency is not None else 1.0,
            agreement,
        )
        candidate = replace(candidate, consistency=consistency)
        if agreement < 0.55:
            candidate = replace(candidate, embedding=None, reason="inconsistent_voice_windows")
    return candidate, "vad-packed-fallback-v1"
