"""Compose diarization, acoustic evidence and persistent identity decisions."""

from dataclasses import asdict, dataclass
from typing import Protocol

import numpy as np

from .audio import Audio, Turn, clean_spans, speakers_overlap, speech_windows, validate_turns
from .identity import MatchDecision, MatchPolicy, identify, normalize_embedding
from .registry import Registry


class Embedder(Protocol):
    model_id: str
    dimension: int

    def encode(self, samples: np.ndarray, sample_rate: int = 16000) -> np.ndarray: ...


@dataclass
class Evidence:
    embedding: np.ndarray | None
    clean_seconds: float
    used_seconds: float
    windows: int
    consistency: float | None
    reason: str


def extract_evidence(audio: Audio, turns: list[Turn], speaker: str, embedder: Embedder) -> Evidence:
    spans = clean_spans(turns, speaker)
    available = sum(end - start for start, end in spans)
    windows = speech_windows(spans)
    # Cap compute and sample across the whole recording, not just the introduction.
    if len(windows) > 20:
        indices = np.linspace(0, len(windows) - 1, 20, dtype=int)
        windows = [windows[i] for i in indices]
    vectors, lengths = [], []
    for start, end in windows:
        chunk = audio.samples[round(start * audio.sample_rate) : round(end * audio.sample_rate)]
        # These checks complement VAD; they are not a noise or speaker-quality estimator.
        if not len(chunk) or not np.isfinite(chunk).all():
            continue
        rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
        clipping = float(np.mean(np.abs(chunk) >= 0.999))
        if rms < 1e-4 or clipping > 0.05:
            continue
        vectors.append(
            normalize_embedding(embedder.encode(chunk, audio.sample_rate), embedder.dimension)
        )
        lengths.append(end - start)
    if not vectors:
        return Evidence(None, available, 0.0, 0, None, "insufficient_clean_speech")
    # Pairwise agreement catches a cluster containing multiple unrelated voices.
    similarities = np.stack(vectors) @ np.stack(vectors).T
    consistency = (
        float(np.min(similarities[np.triu_indices(len(vectors), 1)])) if len(vectors) > 1 else 1.0
    )
    if consistency < 0.55:
        return Evidence(
            None, available, sum(lengths), len(vectors), consistency, "inconsistent_voice_windows"
        )
    pooled = normalize_embedding(np.average(vectors, axis=0, weights=lengths), embedder.dimension)
    return Evidence(pooled, available, sum(lengths), len(vectors), consistency, "usable")


def analyze(
    audio: Audio,
    turns: list[Turn],
    embedder: Embedder,
    registry: Registry,
    policy: MatchPolicy | None = None,
    learn_new: bool = False,
) -> dict:
    if embedder.model_id != registry.model_id or embedder.dimension != registry.dimension:
        raise ValueError("Embedding model/version or dimension does not match the registry.")
    turns = validate_turns(turns, audio.duration)
    policy = policy or MatchPolicy()
    labels = sorted({t.speaker for t in turns})
    evidence = {label: extract_evidence(audio, turns, label, embedder) for label in labels}
    profiles = registry.list_speakers()
    decisions = {
        label: identify(e.embedding, profiles, policy)
        if e.embedding is not None
        else MatchDecision("ambiguous", None, None, None, e.reason)
        for label, e in evidence.items()
    }
    # Two simultaneous local speakers cannot safely be the same global identity.
    conflicts = set()
    for i, first in enumerate(labels):
        for second in labels[i + 1 :]:
            a, b = decisions[first], decisions[second]
            if (
                a.speaker_id is not None
                and a.speaker_id == b.speaker_id
                and speakers_overlap(turns, first, second)
            ):
                conflicts.update((first, second))
    for label in conflicts:
        d = decisions[label]
        decisions[label] = MatchDecision(
            "ambiguous", None, d.score, d.margin, "overlapping_identity_conflict"
        )

    assignments: dict[str, list[str]] = {}
    for label, decision in decisions.items():
        if decision.speaker_id:
            assignments.setdefault(decision.speaker_id, []).append(label)
    speakers = []
    for label in labels:
        e, d = evidence[label], decisions[label]
        created = False
        if learn_new and d.status == "unknown" and e.used_seconds >= 10 and e.windows >= 2:
            # Recheck newly enrolled speakers to avoid duplicate profiles for split clusters.
            fresh = identify(e.embedding, registry.list_speakers(), policy)
            if fresh.status == "recognized":
                if any(
                    speakers_overlap(turns, label, other)
                    for other in assignments.get(fresh.speaker_id, [])
                ):
                    d = MatchDecision(
                        "ambiguous",
                        None,
                        fresh.score,
                        fresh.margin,
                        "overlapping_identity_conflict",
                    )
                else:
                    d = fresh
            elif fresh.status == "ambiguous":
                d = fresh
            else:
                profile = registry.enroll(e.embedding)
                d = MatchDecision(
                    "new", profile.speaker_id, fresh.score, fresh.margin, "new_profile_created"
                )
                created = True
            if d.speaker_id:
                assignments.setdefault(d.speaker_id, []).append(label)
        elif learn_new and d.status == "unknown":
            d = MatchDecision(
                "unknown", None, d.score, d.margin, "new_candidate_needs_10_seconds_and_two_windows"
            )
        names = {p.speaker_id: p.name for p in registry.list_speakers()}
        speakers.append(
            {
                "local_speaker": label,
                "status": d.status,
                "speaker_id": d.speaker_id,
                "name": names.get(d.speaker_id),
                "similarity": d.score,
                "margin": d.margin,
                "reason": d.reason,
                "profile_created": created,
                "clean_seconds": round(e.clean_seconds, 3),
                "used_seconds": round(e.used_seconds, 3),
                "windows": e.windows,
                "consistency": e.consistency,
            }
        )
    by_label = {s["local_speaker"]: s for s in speakers}
    return {
        "schema_version": 1,
        "model_id": embedder.model_id,
        "duration_seconds": audio.duration,
        "policy": asdict(policy),
        "learn_new": learn_new,
        "speech_detected": bool(turns),
        "score_note": "Cosine similarities are not calibrated probabilities.",
        "speakers": speakers,
        "turns": [
            dict(
                start=t.start,
                end=t.end,
                local_speaker=t.speaker,
                speaker_id=by_label[t.speaker]["speaker_id"],
                name=by_label[t.speaker]["name"],
                status=by_label[t.speaker]["status"],
            )
            for t in turns
        ],
    }
