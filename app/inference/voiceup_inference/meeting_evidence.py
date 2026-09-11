"""Authorize voice memory only from individually checked original speech regions."""

from __future__ import annotations

from math import ceil, floor

import numpy as np

from voiceup.audio import Audio, Turn, clean_spans, merge_spans, speech_windows
from voiceup.identity import normalize_embedding
from voiceup.pipeline import Embedder

from .evidence import _usable, extract_pilot_evidence


def extract_track_evidence(
    audio: Audio,
    turns: list[Turn],
    speaker: str,
    speech: list[tuple[float, float]],
    embedder: Embedder,
) -> dict:
    """Keep gaps and competing speakers out of evidence; preserve original guards."""
    intersections = merge_spans(
        [
            (max(start, first), min(end, last))
            for start, end in clean_spans(turns, speaker)
            for first, last in speech
            if max(start, first) < min(end, last)
        ]
    )
    ranges = []
    pieces = []
    for start, end in intersections:
        blocks = speech_windows([(start, end)]) if end - start >= 3 else [(start, end)]
        for first, last in blocks:
            # Crop the outer source region; adjacent internal guard windows share
            # the same PCM boundary rather than creating artificial sample gaps.
            left = (
                ceil(first * audio.sample_rate)
                if first == start
                else round(first * audio.sample_rate)
            )
            right = (
                floor(last * audio.sample_rate) if last == end else round(last * audio.sample_rate)
            )
            samples = audio.samples[left:right]
            if len(samples) >= 1.5 * audio.sample_rate and _usable(samples):
                ranges.append((left / audio.sample_rate, right / audio.sample_rate))
                pieces.append(samples)
    evidence, preprocessing = extract_pilot_evidence(
        audio, [Turn(start, end, "probe") for start, end in ranges], embedder, "identify"
    )
    result = {
        "status": "insufficient_speech",
        "embedding": None,
        "dimensions": embedder.dimension,
        "validated_ranges": [],
        "validated_seconds": 0.0,
        "used_seconds": evidence.used_seconds,
        "windows_count": evidence.windows,
        "min_pair_similarity": evidence.consistency,
        "preprocessing_version": preprocessing,
    }
    if evidence.reason == "inconsistent_voice_windows":
        result["status"] = "inconsistent_audio"
        return result
    if evidence.embedding is None or evidence.used_seconds < 3 - 1e-6 or evidence.windows < 1:
        return result
    # The pilot's successful continuous baseline can omit shorter regions. Every
    # region counted for memory needs its own guard, even after baseline success.
    guards = np.stack(
        [
            normalize_embedding(embedder.encode(piece, audio.sample_rate), embedder.dimension)
            for piece in pieces
        ]
    )
    matrix = guards @ guards.T
    pair = float(np.min(matrix[np.triu_indices(len(guards), 1)])) if len(guards) > 1 else 1.0
    agreement = float(np.min(guards @ evidence.embedding))
    consistency = min(
        pair, agreement, evidence.consistency if evidence.consistency is not None else 1.0
    )
    result["min_pair_similarity"] = consistency
    if consistency < 0.55:
        result["status"] = "inconsistent_audio"
        return result
    result.update(
        {
            "status": "usable",
            "embedding": evidence.embedding.tolist(),
            "validated_ranges": [
                {"start": start, "end": end} for start, end in merge_spans(ranges)
            ],
            "validated_seconds": sum(len(piece) for piece in pieces) / audio.sample_rate,
        }
    )
    return result
