"""AMI benchmark scoring: person-disjoint rotations, cluster ownership and pooled metrics."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ami():
    spec = importlib.util.spec_from_file_location(
        "run_ami_evaluation", ROOT / "scripts/run-ami-evaluation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MEETINGS = [
    {"meeting": "ES2004a", "speakers": ["A", "B"]},
    {"meeting": "ES2004b", "speakers": ["A", "B"]},
    {"meeting": "IB4001", "speakers": ["C", "X"]},
    {"meeting": "IS1008a", "speakers": ["C", "D"]},
    {"meeting": "TS3003a", "speakers": ["E", "F"]},
]


def turn(start, end, speaker):
    return {"start_seconds": start, "end_seconds": end, "speaker_public_id": speaker}


def test_components_join_meetings_through_shared_people(ami):
    groups = [[row["meeting"] for row in group] for group in ami.components(MEETINGS)]
    assert groups == [["ES2004a", "ES2004b"], ["IB4001", "IS1008a"], ["TS3003a"]]


@pytest.mark.parametrize("rotation", [1, 2])
def test_rotation_roles_are_person_disjoint_and_swap(ami, rotation):
    steps = ami.plan(MEETINGS, rotation)
    roles = {}
    for step in steps:
        for person in step["speakers"]:
            roles.setdefault(person, set()).add(step["role"])
    assert all(len(found) == 1 for found in roles.values())
    gallery = {step["meeting"] for step in steps if step["role"] == "gallery"}
    other = {step["meeting"] for step in ami.plan(MEETINGS, 3 - rotation) if step["role"] == "gallery"}
    assert gallery and other and not gallery & other and gallery | other == {m["meeting"] for m in MEETINGS}
    first_other = next(index for index, step in enumerate(steps) if step["role"] == "non_gallery")
    assert all(step["role"] == "non_gallery" for step in steps[first_other:])


def test_dominance_requires_majority_and_clips_to_uem(ami):
    reference = [(0, 10, "A"), (10, 20, "B")]
    turns = [turn(0, 10, "h1"), turn(5, 15, "h2"), turn(15, 40, "h3"), turn(0, 5, None)]
    dominance = ami.dominant_people(turns, reference, (0, 20))
    assert dominance["h1"] == ("A", 1.0)
    assert dominance["h2"][0] in {"A", "B"} and dominance["h2"][1] == 0.5
    assert dominance["h3"] == ("B", 1.0)
    assert ami.dominant_people([turn(0, 10, "h")], [(0, 4, "A"), (4, 8, "B")], (0, 10))["h"][0] is None


def speaker(public_id, decision, profile=None):
    return {"public_id": public_id, "decision": decision, "profile_public_id": profile}


def test_gallery_sequence_scores_first_correct_misidentified_duplicate_and_missed(ami):
    owners = {}
    reference = [(0, 30, "A"), (30, 60, "B"), (60, 61, "C")]
    first = ami.score_meeting(
        "gallery",
        [speaker("h1", "enrolled", "pA"), speaker("h2", "profile_pending")],
        {"h1": ("A", 1.0), "h2": ("B", 1.0)},
        reference,
        owners,
    )
    assert [(o["person"], o["kind"], o["outcome"]) for o in first] == [
        ("A", "first", "enrolled"),
        ("B", "first", "not_enrolled"),
    ]
    assert owners == {"pA": "A"}
    owners["pB"] = "B"
    second = ami.score_meeting(
        "gallery",
        [speaker("h1", "recognized", "pA"), speaker("h2", "recognized", "pA")],
        {"h1": ("A", 1.0), "h2": ("B", 1.0)},
        reference,
        owners,
    )
    assert [o["outcome"] for o in second] == ["correct", "misidentified"]
    third = ami.score_meeting(
        "gallery",
        [speaker("h1", "enrolled", "pA2"), speaker("h2", "ambiguous")],
        {"h1": ("A", 1.0), "h2": ("B", 1.0)},
        reference,
        owners,
    )
    assert [o["outcome"] for o in third] == ["duplicate_profile", "missed"]


def test_non_gallery_recognition_is_false_accept_and_short_speech_is_not_scored(ami):
    outcomes = ami.score_meeting(
        "non_gallery",
        [speaker("h1", "recognized", "pA"), speaker("h2", "profile_pending")],
        {"h1": ("E", 1.0), "h2": ("F", 1.0)},
        [(0, 10, "E"), (10, 20, "F"), (20, 22, "G")],
        {"pA": "A"},
    )
    assert [(o["person"], o["outcome"]) for o in outcomes] == [
        ("E", "false_accept"),
        ("F", "rejected"),
    ]


def test_der_is_permutation_invariant_and_counts_missed_speech(ami):
    reference = [(0, 10, "A"), (10, 20, "B")]
    perfect = ami.der_components([turn(0, 10, "x"), turn(10, 20, "y")], reference, (0, 20), 0.0)
    assert perfect["missed"] == perfect["false_alarm"] == perfect["confusion"] == 0
    assert perfect["total"] == pytest.approx(20)
    half = ami.der_components([turn(0, 10, "x")], reference, (0, 20), 0.0)
    assert half["missed"] == pytest.approx(10)


def test_jer_scores_each_reference_speaker_and_penalizes_a_split_person(ami):
    reference = [(0, 10, "A"), (10, 20, "B")]
    extra = ami.jer_components(
        [turn(0, 10, "x"), turn(10, 20, "y"), turn(0, 5, "z")], reference, (0, 20), 0.0
    )
    assert extra == {"speaker_count": 2.0, "speaker_error": pytest.approx(0.0)}
    split = ami.jer_components(
        [turn(0, 10, "x"), turn(10, 15, "y"), turn(15, 20, "z")], reference, (0, 20), 0.0
    )
    assert split["speaker_error"] == pytest.approx(0.5)
    one_lost = ami.jer_components([turn(0, 10, "x")], reference, (0, 20), 0.0)
    assert one_lost["speaker_error"] == pytest.approx(1.0)


def test_aggregate_pools_jer_over_reference_speakers(ami):
    der = {"total": 100.0, "missed": 5.0, "false_alarm": 3.0, "confusion": 2.0}
    meetings = [
        {
            "der": {"collar_0": der, "collar_0_25": der},
            "jer": {key: {"speaker_count": count, "speaker_error": error} for key in ("collar_0", "collar_0_25")},
            "outcomes": [],
        }
        for count, error in ((4.0, 1.0), (2.0, 2.0))
    ]
    report = ami.aggregate(meetings)
    assert report["diarization"]["collar_0"]["jer"] == pytest.approx(0.5)
    assert report["diarization"]["collar_0_25"]["jer"] == pytest.approx(0.5)


def test_aggregate_pools_counts_and_bounds_rates(ami):
    der = {"total": 100.0, "missed": 5.0, "false_alarm": 3.0, "confusion": 2.0}
    jer = {"speaker_count": 2.0, "speaker_error": 0.2}
    meetings = [
        {
            "der": {"collar_0": der, "collar_0_25": der},
            "jer": {"collar_0": jer, "collar_0_25": jer},
            "outcomes": [
                {"person": "A", "kind": "first", "outcome": "enrolled"},
                {"person": "B", "kind": "first", "outcome": "not_enrolled"},
            ],
        },
        {
            "der": {"collar_0": der, "collar_0_25": der},
            "jer": {"collar_0": jer, "collar_0_25": jer},
            "outcomes": [
                {"person": "A", "kind": "known", "outcome": "correct"},
                {"person": "B", "kind": "first", "outcome": "enrolled"},
                {"person": "E", "kind": "unknown", "outcome": "rejected"},
            ],
        },
    ]
    report = ami.aggregate(meetings)
    assert report["diarization"]["collar_0"]["der"] == pytest.approx(0.10)
    assert report["diarization"]["collar_0"]["jer"] == pytest.approx(0.10)
    identity = report["identity"]
    assert identity["gallery_people"] == 2
    assert identity["enrolled_first"] == 1 and identity["enrolled_cumulative"] == 2
    assert identity["known_probes"] == 1 and identity["recognition_rate"] == 1.0
    assert identity["unknown_probes"] == 1 and identity["fpir"] == 0.0
    low, high = report["diarization"]["collar_0_interval"]
    assert low == high == pytest.approx(0.10)


def test_roster_lists_only_saved_profiles_of_attending_people(ami):
    owners = {"pA": "A", "pB": "B", "pX": None, "pC": "C"}
    gallery = {"meeting": "ES2004b", "speakers": ["A", "B", "D"], "role": "gallery"}
    body = ami.creation_body(gallery, 10, owners, known_speaker_count=False, roster=True)
    assert body["participant_profile_ids"] == ["pA", "pB"]
    assert "participant_count" not in body and body["auto_enroll"] is True
    plain = ami.creation_body(gallery, 10, owners, known_speaker_count=True, roster=False)
    assert "participant_profile_ids" not in plain and plain["expected_speakers"] == 3
    other = {**gallery, "role": "non_gallery"}
    assert "participant_profile_ids" not in ami.creation_body(other, 10, owners, known_speaker_count=False, roster=True)
