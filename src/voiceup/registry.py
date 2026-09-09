"""Persistent, explicitly enrolled speaker memory backed by SQLite.

One registry belongs to one embedding model/version and dimension. Embeddings
are normalized, little-endian float64 blobs, never executable serialized data.
Speaker embeddings can identify people: protect the database as personal data.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Iterator
from uuid import uuid4

import numpy as np

from .identity import normalize_embedding


@dataclass
class SpeakerProfile:
    speaker_id: str
    name: str
    embeddings: list[np.ndarray]


class Registry:
    """A model-specific registry with atomic writes and at most 20 examples/person.

    ``enroll(..., speaker_id=...)`` explicitly appends to an existing identity.
    Recognition does not call this method. Adding a sample cannot rename a
    person; use ``rename``. Oldest examples are evicted when the cap is reached.
    Each created identity consumes a monotonic participant number, including
    identities with an explicit name. Deleted numbers are never reused.
    """

    MAX_EXEMPLARS = 20
    SCHEMA_VERSION = "1"

    def __init__(self, path: str | Path, model_id: str, dimension: int):
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must be a nonempty model/version identifier")
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1:
            raise ValueError("dimension must be a positive integer")
        self.path = Path(path) if str(path) != ":memory:" else Path(":memory:")
        self.model_id = model_id
        self.dimension = dimension
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path), timeout=30, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        try:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._initialize()
        except BaseException:
            self._connection.close()
            raise

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise

    def _initialize(self) -> None:
        with self._transaction():
            tables = {
                row[0]
                for row in self._connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
            }
            if tables:
                required = {"voiceup_metadata", "voiceup_speakers", "voiceup_embeddings"}
                if not required.issubset(tables):
                    raise ValueError("database is not a complete VoiceUp speaker registry")
                self._validate_metadata()
                return
            self._connection.execute(
                "CREATE TABLE voiceup_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._connection.execute(
                "CREATE TABLE voiceup_speakers ("
                "speaker_id TEXT PRIMARY KEY, name TEXT NOT NULL, "
                "participant_number INTEGER UNIQUE NOT NULL)"
            )
            self._connection.execute(
                "CREATE TABLE voiceup_embeddings ("
                "sample_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "speaker_id TEXT NOT NULL REFERENCES voiceup_speakers(speaker_id) "
                "ON DELETE CASCADE, embedding BLOB NOT NULL)"
            )
            self._connection.execute(
                "CREATE INDEX voiceup_embeddings_speaker "
                "ON voiceup_embeddings(speaker_id, sample_id)"
            )
            self._connection.executemany(
                "INSERT INTO voiceup_metadata(key, value) VALUES (?, ?)",
                [
                    ("schema_version", self.SCHEMA_VERSION),
                    ("model_id", self.model_id),
                    ("dimension", str(self.dimension)),
                    ("next_participant_number", "1"),
                ],
            )

    def _validate_metadata(self) -> None:
        metadata = dict(self._connection.execute("SELECT key, value FROM voiceup_metadata"))
        expected = {
            "schema_version": self.SCHEMA_VERSION,
            "model_id": self.model_id,
            "dimension": str(self.dimension),
        }
        for key, value in expected.items():
            if metadata.get(key) != value:
                raise ValueError(
                    f"registry {key} mismatch: stored {metadata.get(key)!r}, "
                    f"requested {value!r}; use a separate registry for another model/version"
                )
        try:
            next_number = int(metadata["next_participant_number"])
        except (KeyError, ValueError) as exc:
            raise ValueError("registry has invalid participant numbering metadata") from exc
        if next_number < 1:
            raise ValueError("registry has invalid participant numbering metadata")

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("speaker name must be a nonempty string")
        return name.strip()

    def _profile(self, speaker_id: str) -> SpeakerProfile:
        row = self._connection.execute(
            "SELECT speaker_id, name FROM voiceup_speakers WHERE speaker_id = ?",
            (speaker_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown speaker_id: {speaker_id}")
        embeddings = []
        for sample in self._connection.execute(
            "SELECT embedding FROM voiceup_embeddings WHERE speaker_id = ? ORDER BY sample_id",
            (speaker_id,),
        ):
            blob = sample[0]
            if not isinstance(blob, bytes) or len(blob) != self.dimension * 8:
                raise ValueError(f"corrupt embedding for speaker {speaker_id}")
            embeddings.append(normalize_embedding(np.frombuffer(blob, dtype="<f8"), self.dimension))
        if not embeddings:
            raise ValueError(f"speaker {speaker_id} has no stored embeddings")
        return SpeakerProfile(row["speaker_id"], row["name"], embeddings)

    def list_speakers(self) -> list[SpeakerProfile]:
        """Return detached profile copies in original enrollment order."""
        # A deferred read transaction keeps names and examples in one snapshot
        # without taking the write lock that enrollment requires.
        self._connection.execute("BEGIN")
        try:
            self._validate_metadata()
            speaker_ids = [
                row[0]
                for row in self._connection.execute(
                    "SELECT speaker_id FROM voiceup_speakers ORDER BY participant_number"
                )
            ]
            profiles = [self._profile(speaker_id) for speaker_id in speaker_ids]
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise
        else:
            return profiles

    def enroll(
        self,
        embedding: object,
        name: str | None = None,
        speaker_id: str | None = None,
    ) -> SpeakerProfile:
        """Create a person or explicitly append an example to an existing person."""
        vector = normalize_embedding(embedding, self.dimension)
        if name is not None:
            name = self._validate_name(name)
        if speaker_id is not None and name is not None:
            raise ValueError("enrolling an existing speaker cannot rename it; use rename()")
        with self._transaction():
            self._validate_metadata()
            if speaker_id is None:
                next_number = int(
                    self._connection.execute(
                        "SELECT value FROM voiceup_metadata WHERE key = 'next_participant_number'"
                    ).fetchone()[0]
                )
                speaker_id = "spk_" + uuid4().hex
                self._connection.execute(
                    "INSERT INTO voiceup_speakers(speaker_id, name, participant_number) "
                    "VALUES (?, ?, ?)",
                    (
                        speaker_id,
                        name if name is not None else f"Katılımcı {next_number}",
                        next_number,
                    ),
                )
                self._connection.execute(
                    "UPDATE voiceup_metadata SET value = ? WHERE key = 'next_participant_number'",
                    (str(next_number + 1),),
                )
            elif (
                self._connection.execute(
                    "SELECT 1 FROM voiceup_speakers WHERE speaker_id = ?", (speaker_id,)
                ).fetchone()
                is None
            ):
                raise KeyError(f"unknown speaker_id: {speaker_id}")
            self._connection.execute(
                "INSERT INTO voiceup_embeddings(speaker_id, embedding) VALUES (?, ?)",
                (speaker_id, vector.astype("<f8").tobytes()),
            )
            self._connection.execute(
                "DELETE FROM voiceup_embeddings WHERE speaker_id = ? AND sample_id NOT IN "
                "(SELECT sample_id FROM voiceup_embeddings WHERE speaker_id = ? "
                "ORDER BY sample_id DESC LIMIT ?)",
                (speaker_id, speaker_id, self.MAX_EXEMPLARS),
            )
            profile = self._profile(speaker_id)
        return profile

    def rename(self, speaker_id: str, name: str) -> None:
        name = self._validate_name(name)
        with self._transaction():
            self._validate_metadata()
            cursor = self._connection.execute(
                "UPDATE voiceup_speakers SET name = ? WHERE speaker_id = ?", (name, speaker_id)
            )
            if cursor.rowcount == 0:
                raise KeyError(f"unknown speaker_id: {speaker_id}")

    def delete(self, speaker_id: str) -> None:
        """Remove the profile and all its examples in the same transaction."""
        with self._transaction():
            self._validate_metadata()
            cursor = self._connection.execute(
                "DELETE FROM voiceup_speakers WHERE speaker_id = ?", (speaker_id,)
            )
            if cursor.rowcount == 0:
                raise KeyError(f"unknown speaker_id: {speaker_id}")

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Registry:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
