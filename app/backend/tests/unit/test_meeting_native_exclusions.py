"""Independent native evidence remains bounded, source-bound and symmetric."""

import math
from copy import deepcopy

import pytest

from app.domain.meeting_native_exclusions import (
    ABSENT_EXCLUSIONS,
    check_exclusion_graph,
    link_native_peers,
    read_exclusions,
    separation_score,
)
from app.domain.speaker_identity import MatchPolicy


def pair():
    graph = {1: None, 2: None}
    link_native_peers(
        graph,
        1,
        2,
        source_sha256="a" * 64,
        chunk_index=1,
        labels=("SPEAKER_16", "SPEAKER_15"),
        recipe="community-vbx-fa015-v1",
        similarity=0.433,
        new_threshold=0.45,
    )
    return graph


def test_same_native_label_does_not_prove_difference_without_independent_vector() -> None:
    unit = [1.0] + [0.0] * 191
    different = [0.433, math.sqrt(1 - 0.433**2)] + [0.0] * 190
    assert separation_score(unit, different, MatchPolicy()) == pytest.approx(0.433)
    assert separation_score(unit, unit, MatchPolicy()) is None
    assert separation_score(None, different, MatchPolicy()) is None
    assert separation_score(unit, None, MatchPolicy()) is None
    assert separation_score(unit, different, MatchPolicy(new_threshold=0.4)) is None


def test_peer_record_is_symmetric_and_first_proof_is_not_repeated() -> None:
    graph = pair()
    records = [(key, value.to_record()) for key, value in graph.items()]
    assert check_exclusion_graph(records, "a" * 64) == graph
    proof = graph[1].peers[0]
    assert proof.meeting_speaker_id == 2 and proof.labels == ("SPEAKER_15", "SPEAKER_16")
    before = deepcopy(graph)
    link_native_peers(
        graph,
        1,
        2,
        source_sha256="a" * 64,
        chunk_index=2,
        labels=("OTHER_1", "OTHER_2"),
        recipe=None,
        similarity=0.2,
        new_threshold=0.45,
    )
    assert graph == before


def test_missing_legacy_is_absent_but_present_null_is_invalid() -> None:
    assert read_exclusions(ABSENT_EXCLUSIONS, None, 1) is None
    with pytest.raises(ValueError, match="invalid_native_exclusions"):
        read_exclusions(None, "a" * 64, 1)


def test_cached_peer_and_meeting_population_bounds_do_not_truncate() -> None:
    record = pair()[1].to_record()
    template = record["peers"][0]
    record["peers"] = [{**template, "meeting_speaker_id": identity} for identity in range(2, 1001)]
    state = read_exclusions(record, "a" * 64, 1)
    assert state is not None and len(state.peers) == 999
    record["peers"].append({**template, "meeting_speaker_id": 1001})
    with pytest.raises(ValueError, match="invalid_native_exclusions"):
        read_exclusions(record, "a" * 64, 1)
    records = [(identity, ABSENT_EXCLUSIONS) for identity in range(1, 1001)]
    assert len(check_exclusion_graph(records, "a" * 64)) == 1000
    with pytest.raises(ValueError, match="invalid_native_exclusions"):
        check_exclusion_graph([*records, (1001, ABSENT_EXCLUSIONS)], "a" * 64)


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "version",
        "model",
        "unknown_key",
        "null_peers",
        "duplicate",
        "self",
        "range",
        "label",
        "recipe",
        "score",
        "threshold",
        "bool_id",
    ],
)
def test_malformed_private_proof_is_not_silently_ignored(change) -> None:
    record = pair()[1].to_record()
    if change == "source":
        record["source_sha256"] = "b" * 64
    if change == "version":
        record["version"] = 2
    if change == "model":
        record["ecapa_model_revision"] = "unsupported"
    if change == "unknown_key":
        record["extra"] = True
    if change == "null_peers":
        record["peers"] = None
    if change == "duplicate":
        record["peers"] *= 2
    if change == "self":
        record["peers"][0]["meeting_speaker_id"] = 1
    if change == "range":
        record["peers"][0]["chunk_index"] = 240
    if change == "label":
        record["peers"][0]["labels"] = ["x", "x"]
    if change == "recipe":
        record["peers"][0]["recipe"] = "unknown"
    if change == "score":
        record["peers"][0]["similarity"] = float("nan")
    if change == "threshold":
        record["peers"][0]["new_threshold"] = 0.4
    if change == "bool_id":
        record["peers"][0]["meeting_speaker_id"] = True
    with pytest.raises(ValueError, match="invalid_native_exclusions"):
        read_exclusions(record, "a" * 64, 1)


@pytest.mark.parametrize("kind", ["foreign", "missing", "different_proof"])
def test_graph_requires_same_meeting_peers_and_identical_reciprocal_proof(kind) -> None:
    graph = pair()
    left, right = graph[1].to_record(), graph[2].to_record()
    if kind == "foreign":
        records = [(1, left)]
    elif kind == "missing":
        records = [(1, left), (2, ABSENT_EXCLUSIONS)]
    else:
        right["peers"][0]["similarity"] = 0.2
        records = [(1, left), (2, right)]
    with pytest.raises(ValueError, match="invalid_native_exclusions"):
        check_exclusion_graph(records, "a" * 64)
