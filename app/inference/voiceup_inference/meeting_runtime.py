"""Bounded local meeting chunks with explicit source coordinates and model identity."""

from __future__ import annotations

import math
from numbers import Real
from typing import Protocol

import numpy as np

from voiceup.audio import Audio, Turn, validate_turns

from .meeting_evidence import extract_track_evidence
from .meeting_models import (
    ASR_ID,
    ASR_REVISION,
    DIARIZATION_ID,
    DIARIZATION_RECIPE,
    DIARIZATION_REVISION,
)
from .model_bundle import DIMENSIONS, FILES, MODEL_ID, MODEL_REVISION, SILERO_VERSION
from .models import ModelHandles


class MeetingModels(Protocol):
    def diarize(
        self,
        audio: Audio,
        *,
        max_speakers: int | None = None,
        num_speakers: int | None = None,
    ) -> dict: ...
    def transcribe(self, audio: Audio, language: str | None) -> dict: ...
    def voice_embedding(self, samples: np.ndarray) -> np.ndarray: ...


def model_identity() -> dict:
    return {
        "diarization": {
            "model_id": DIARIZATION_ID,
            "revision": DIARIZATION_REVISION,
            "recipe": DIARIZATION_RECIPE,
        },
        "asr": {"model_id": ASR_ID, "revision": ASR_REVISION},
        "embedding": {
            "model_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "dimensions": DIMENSIONS,
        },
    }


def _interval(row: dict, duration: float) -> tuple[float, float] | None:
    start, end = row["start"], row["end"]
    if (
        not isinstance(start, Real)
        or not isinstance(end, Real)
        or isinstance(start, bool)
        or isinstance(end, bool)
        or not math.isfinite(start)
        or not math.isfinite(end)
        or end < start
    ):
        raise ValueError("invalid_meeting_model_interval")
    first, last = max(0.0, start), min(duration, end)
    return (float(first), float(last)) if first < last else None


def _turns(rows: list, duration: float) -> list[Turn]:
    if not isinstance(rows, list) or len(rows) > 4096:
        raise ValueError("invalid_meeting_turns")
    turns = []
    for row in rows:
        if row["start"] == row["end"]:
            raise ValueError("invalid_meeting_turns")
        interval = _interval(row, duration)
        if interval is not None:
            label = row["speaker"]
            if not isinstance(label, str) or not 0 < len(label.strip()) <= 128:
                raise ValueError("invalid_meeting_speaker")
            turns.append(Turn(*interval, label))
    if len({turn.speaker for turn in turns}) > 1000:
        raise ValueError("invalid_meeting_speaker_count")
    return validate_turns(turns, duration)


def _tracking(diarization: dict) -> dict[str, dict | None]:
    embeddings = diarization.get("speaker_embeddings")
    labels = {row["speaker"] for row in diarization["speaker_diarization"]}
    if (
        not isinstance(embeddings, dict)
        or set(embeddings) != labels
        or len(embeddings) > 1000
    ):
        raise ValueError("invalid_meeting_tracking_labels")
    result = {}
    for label, vector in embeddings.items():
        if vector is None:
            result[label] = None
            continue
        if (
            not isinstance(vector, list)
            or len(vector) != 256
            or any(
                not isinstance(value, Real)
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in vector
            )
            or not math.isclose(
                math.sqrt(sum(value * value for value in vector)),
                1.0,
                rel_tol=0,
                abs_tol=1e-4,
            )
        ):
            raise ValueError("invalid_meeting_tracking_embedding")
        result[label] = {
            "embedding": [float(value) for value in vector],
            "model_id": DIARIZATION_ID,
            "model_revision": DIARIZATION_REVISION,
            "component": "embedding",
            "dimensions": 256,
        }
    return result


def analyze_meeting_chunk(
    audio: Audio,
    models: MeetingModels,
    pilot: ModelHandles,
    language: str | None,
    *,
    max_speakers: int | None = None,
    num_speakers: int | None = None,
) -> dict:
    speech = pilot.vad.speech_spans(audio.samples, audio.sample_rate)
    speech_turns = validate_turns(
        [Turn(start, end, "vad") for start, end in speech], audio.duration
    )
    speech = [(turn.start, turn.end) for turn in speech_turns]
    diarization = (
        models.diarize(audio, max_speakers=max_speakers, num_speakers=num_speakers)
        if speech
        else {
            "speaker_diarization": [],
            "exclusive_speaker_diarization": [],
            "speaker_embeddings": {},
        }
    )
    turns = _turns(diarization["speaker_diarization"], audio.duration)
    exclusive = _turns(diarization["exclusive_speaker_diarization"], audio.duration)
    tracking = _tracking(diarization)
    # Whisper must not invent speech for a chunk for which VAD found none.
    transcript = (
        models.transcribe(audio, language)
        if speech
        else {
            "segments": [],
            "language": None,
            "language_probability": 0.0,
        }
    )
    segments, words = [], []
    rows = transcript["segments"]
    if not isinstance(rows, list) or len(rows) > 4096:
        raise ValueError("invalid_meeting_segments")
    for row in rows:
        interval = _interval(row, audio.duration)
        text = row["text"]
        if not isinstance(text, str) or len(text) > 32768:
            raise ValueError("invalid_meeting_text")
        if interval is not None:
            segments.append({"start": interval[0], "end": interval[1], "text": text})
        for word in row["words"] or []:
            interval = _interval(word, audio.duration)
            probability, text = word["probability"], word["word"]
            if (
                not isinstance(text, str)
                or len(text) > 4096
                or not isinstance(probability, Real)
                or isinstance(probability, bool)
                or not math.isfinite(probability)
                or not 0 <= probability <= 1
            ):
                raise ValueError("invalid_meeting_word")
            if interval is not None:
                words.append(
                    {
                        "start": interval[0],
                        "end": interval[1],
                        "word": text,
                        "probability": float(probability),
                    }
                )
            if len(words) > 16384:
                raise ValueError("invalid_meeting_word_count")
    detected = transcript["language"]
    probability = transcript["language_probability"]
    if (
        (bool(speech) and detected is None)
        or (
            detected is not None
            and (
                not isinstance(detected, str)
                or not 2 <= len(detected) <= 3
                or not detected.isascii()
                or not detected.isalpha()
            )
        )
        or type(probability) not in {int, float}
        or not math.isfinite(probability)
        or not 0 <= probability <= 1
    ):
        raise ValueError("invalid_meeting_language")
    tracks = [
        {
            "speaker": label,
            **extract_track_evidence(audio, turns, label, speech, pilot.embedder),
            "tracking": tracking[label],
        }
        for label in sorted({turn.speaker for turn in turns})
    ]

    def serialize(sequence: list[Turn]) -> list[dict]:
        return [
            {"start": turn.start, "end": turn.end, "speaker": turn.speaker}
            for turn in sequence
        ]

    return {
        "input_seconds": audio.duration,
        "sample_rate": audio.sample_rate,
        "turns": serialize(turns),
        "exclusive_turns": serialize(exclusive),
        "segments": segments,
        "words": words,
        "language": detected,
        "language_probability": float(probability),
        "tracks": tracks,
        "vad": {
            "model_id": "silero-vad",
            "model_version": SILERO_VERSION,
            "model_sha256": FILES["silero/silero_vad.jit"],
            "ranges": [{"start": start, "end": end} for start, end in speech],
        },
        "model_identity": model_identity(),
    }
