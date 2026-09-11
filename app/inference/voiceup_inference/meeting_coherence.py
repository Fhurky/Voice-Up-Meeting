"""Independent secondary-voice veto on final retained 16 kHz meeting PCM."""

import hashlib
import io
import math
from collections.abc import Callable, Iterable

import numpy as np
import soundfile as sf

from voiceup.identity import normalize_embedding

RATE = 16000
WINDOW = 2 * RATE
STEP = RATE // 2


def _two_means(matrix: np.ndarray, dimensions: int = 256) -> np.ndarray | None:
    similarities = matrix @ matrix.T
    upper = np.where(
        np.triu(np.ones(similarities.shape, dtype=bool), k=1), similarities, np.inf
    )
    left, right = np.unravel_index(np.argmin(upper), upper.shape)
    centers = np.stack([matrix[left], matrix[right]])
    previous = None
    for _ in range(20):
        labels = np.argmax(matrix @ centers.T, axis=1)
        if any(not np.any(labels == label) for label in (0, 1)):
            return None
        centers = np.stack(
            [
                normalize_embedding(np.mean(matrix[labels == label], axis=0), dimensions)
                for label in (0, 1)
            ]
        )
        if previous is not None and np.array_equal(labels, previous):
            break
        previous = labels.copy()
    return centers


def has_secondary_voice(
    samples: np.ndarray,
    encode: Callable[[np.ndarray], np.ndarray],
    speech_spans: Iterable[tuple[float, float]],
    *,
    dimensions: int = 256,
) -> bool:
    """Veto only two separated, independently supported groups; never split profiles."""
    if type(dimensions) is not int or dimensions not in {192, 256}:
        raise ValueError("invalid_coherence_dimensions")
    if (
        samples.ndim != 1
        or samples.dtype.kind != "f"
        or not 0 < len(samples) <= 60 * RATE
        or not np.isfinite(samples).all()
        or np.max(np.abs(samples)) > 1
    ):
        raise ValueError("invalid_coherence_pcm")
    speech = np.zeros(len(samples), dtype=bool)
    for first, last in speech_spans:
        if not (
            math.isfinite(first)
            and math.isfinite(last)
            and 0 <= first < last <= len(samples) / RATE
        ):
            raise ValueError("invalid_coherence_vad")
        # Silero returns integer frame indices divided by RATE. Round only to
        # restore those exact frames, avoiding binary-float ceil/floor drift.
        speech[round(first * RATE) : round(last * RATE)] = True
    starts: list[int] = []
    vectors: list[np.ndarray] = []
    seen: set[bytes] = set()
    for first in range(0, len(samples) - WINDOW + 1, STEP):
        if np.count_nonzero(speech[first : first + WINDOW]) < RATE:
            continue
        window = samples[first : first + WINDOW]
        raw = io.BytesIO()
        sf.write(raw, window, RATE, format="RAW", subtype="PCM_16", endian="LITTLE")
        digest = hashlib.sha256(raw.getvalue()).digest()
        if digest in seen:
            continue
        seen.add(digest)
        starts.append(first)
        vectors.append(normalize_embedding(encode(window), dimensions))
    if len(vectors) < 2:
        return False
    matrix = np.stack(vectors)
    centers = _two_means(matrix, dimensions)
    if centers is None or float(centers[0] @ centers[1]) >= 0.55:
        return False
    scores = matrix @ centers.T
    labels = np.argmax(scores, axis=1)
    for label in (0, 1):
        last_end = -1
        independent = 0
        voiced_frames = 0
        for index in np.flatnonzero(labels == label):
            own, other = scores[index, label], scores[index, 1 - label]
            first = starts[index]
            if own >= 0.55 and own - other >= 0.1 and first >= last_end:
                independent += 1
                last_end = first + WINDOW
                voiced_frames += int(np.count_nonzero(speech[first:last_end]))
        if independent < 2 or voiced_frames < 3 * RATE:
            return False
    return True
