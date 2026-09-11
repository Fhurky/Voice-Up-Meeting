"""Source-bound, symmetric exclusions supported by independent native voice evidence."""

import math
import re
from dataclasses import dataclass, replace

from app.domain.meeting_identity import normalized_evidence
from app.domain.speaker_identity import (
    MEETING_MODEL_ID,
    MEETING_MODEL_REVISION,
    MODEL_ID,
    MODEL_REVISION,
    MatchPolicy,
)

ABSENT_EXCLUSIONS = object()
MODEL_FIELDS = {
    "ecapa_model_id": MODEL_ID,
    "ecapa_model_revision": MODEL_REVISION,
    "diarization_model_id": MEETING_MODEL_ID,
    "diarization_model_revision": MEETING_MODEL_REVISION,
}


def _integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("invalid_native_exclusions")
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("invalid_native_exclusions")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError("invalid_native_exclusions") from exc
    if not math.isfinite(number):
        raise ValueError("invalid_native_exclusions")
    return number


@dataclass(frozen=True, slots=True)
class NativePeer:
    meeting_speaker_id: int
    chunk_index: int
    labels: tuple[str, str]
    recipe: str | None
    similarity: float
    new_threshold: float

    @classmethod
    def from_record(cls, value: object) -> "NativePeer":
        if not isinstance(value, dict) or set(value) != {
            "meeting_speaker_id",
            "chunk_index",
            "labels",
            "recipe",
            "similarity",
            "new_threshold",
        }:
            raise ValueError("invalid_native_exclusions")
        labels = value["labels"]
        recipe = value["recipe"]
        if (
            not isinstance(labels, list)
            or len(labels) != 2
            or any(
                not isinstance(label, str) or not label.strip() or not 1 <= len(label) <= 128
                for label in labels
            )
            or labels[0] >= labels[1]
            or (recipe is not None and recipe != "community-vbx-fa015-v1")
        ):
            raise ValueError("invalid_native_exclusions")
        similarity, threshold = _number(value["similarity"]), _number(value["new_threshold"])
        if not -1 <= similarity < threshold <= 1 or threshold < 0:
            raise ValueError("invalid_native_exclusions")
        return cls(
            _integer(value["meeting_speaker_id"], 1, 2**63 - 1),
            _integer(value["chunk_index"], 0, 239),
            (labels[0], labels[1]),
            recipe,
            similarity,
            threshold,
        )

    def to_record(self) -> dict[str, object]:
        return {
            "meeting_speaker_id": self.meeting_speaker_id,
            "chunk_index": self.chunk_index,
            "labels": list(self.labels),
            "recipe": self.recipe,
            "similarity": self.similarity,
            "new_threshold": self.new_threshold,
        }


@dataclass(frozen=True, slots=True)
class NativeExclusions:
    source_sha256: str
    peers: tuple[NativePeer, ...]

    def to_record(self) -> dict[str, object]:
        return {
            "version": 1,
            "source_sha256": self.source_sha256,
            **MODEL_FIELDS,
            "peers": [peer.to_record() for peer in self.peers],
        }


def read_exclusions(
    value: object, source_sha256: str | None, owner: int
) -> NativeExclusions | None:
    if value is ABSENT_EXCLUSIONS:
        return None
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "source_sha256", "peers", *MODEL_FIELDS}
        or type(value["version"]) is not int
        or value["version"] != 1
        or not isinstance(source_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None
        or value["source_sha256"] != source_sha256
        or any(value[key] != expected for key, expected in MODEL_FIELDS.items())
        or not isinstance(value["peers"], list)
        or not 1 <= len(value["peers"]) <= 999
    ):
        raise ValueError("invalid_native_exclusions")
    peers = tuple(NativePeer.from_record(peer) for peer in value["peers"])
    ids = [peer.meeting_speaker_id for peer in peers]
    if owner in ids or ids != sorted(set(ids)):
        raise ValueError("invalid_native_exclusions")
    return NativeExclusions(source_sha256, peers)


def check_exclusion_graph(
    records: list[tuple[int, object]], source_sha256: str | None
) -> dict[int, NativeExclusions | None]:
    if len(records) > 1000 or len({owner for owner, _ in records}) != len(records):
        raise ValueError("invalid_native_exclusions")
    graph = {owner: read_exclusions(value, source_sha256, owner) for owner, value in records}
    by_peer = {
        owner: {peer.meeting_speaker_id: peer for peer in state.peers} if state else {}
        for owner, state in graph.items()
    }
    for owner, state in graph.items():
        for peer in state.peers if state else ():
            reverse = by_peer.get(peer.meeting_speaker_id, {}).get(owner)
            if replace(peer, meeting_speaker_id=owner) != reverse:
                raise ValueError("invalid_native_exclusions")
    return graph


def link_native_peers(
    graph: dict[int, NativeExclusions | None],
    left: int,
    right: int,
    *,
    source_sha256: str,
    chunk_index: int,
    labels: tuple[str, str],
    recipe: str | None,
    similarity: float,
    new_threshold: float,
) -> None:
    if left == right or left not in graph or right not in graph:
        raise ValueError("invalid_native_exclusions")
    proof = NativePeer.from_record(
        {
            "meeting_speaker_id": right,
            "chunk_index": chunk_index,
            "labels": sorted(labels),
            "recipe": recipe,
            "similarity": similarity,
            "new_threshold": new_threshold,
        }
    )
    for owner, other in ((left, right), (right, left)):
        state = graph[owner]
        peers = list(state.peers) if state else []
        if not any(peer.meeting_speaker_id == other for peer in peers):
            peers.append(replace(proof, meeting_speaker_id=other))
        candidate = NativeExclusions(
            source_sha256, tuple(sorted(peers, key=lambda p: p.meeting_speaker_id))
        )
        graph[owner] = read_exclusions(candidate.to_record(), source_sha256, owner)


def separation_score(
    left: list[float] | None, right: list[float] | None, policy: MatchPolicy
) -> float | None:
    if left is None or right is None:
        return None
    a, b = normalized_evidence(left), normalized_evidence(right)
    score = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b, strict=True))))
    return score if score < policy.new_threshold else None
