"""Independent corpus boundaries; generated audio tests software, not voice quality."""

import hashlib
import importlib.util
import json
import sys
import wave
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def preparer():
    path = Path(__file__).resolve().parents[1] / "scripts/prepare-meeting-identity-evaluation.py"
    spec = importlib.util.spec_from_file_location("meeting_identity_preparer", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def inventory():
    return {
        f"ls-{person}": {str(chapter): [] for chapter in range(3 if person < 90 else 2)}
        for person in range(120)
    }


def test_selection_is_independent_of_enumeration_and_excludes_prior_people(preparer):
    data = inventory()
    excluded = {f"ls-{person}" for person in range(10)}
    known, unknown = preparer.select_people(data, excluded)
    assert len(known) == 50 and len(unknown) == 20
    assert not (set(known) & set(unknown))
    assert not (set(known + unknown) & excluded)
    assert all(len(data[person]) >= 3 for person in known)
    assert all(len(data[person]) >= 2 for person in unknown)
    reversed_data = dict(reversed(list(data.items())))
    assert preparer.select_people(reversed_data, excluded) == (known, unknown)
    expected = sorted(
        [person for person in data if person not in excluded and len(data[person]) >= 3],
        key=lambda person: (
            hashlib.sha256(f"{preparer.SEED}|known|{person}".encode()).digest(),
            person,
        ),
    )[:50]
    assert known == expected


def test_insufficient_people_fail_instead_of_reusing_or_replacing(preparer):
    with pytest.raises(preparer.PreparationError, match="insufficient_known_people"):
        preparer.select_people(inventory(), {f"ls-{person}" for person in range(50)})


def test_whole_utterance_selection_has_frozen_duration_limit(preparer):
    rows = [{"id": str(n), "frames": seconds * 16000} for n, seconds in enumerate([30, 35, 10])]
    selected = preparer.select_utterances(rows)
    assert [row["id"] for row in selected] == ["0", "2"]
    assert sum(row["frames"] for row in selected) == 40 * 16000
    assert rows[1]["frames"] == 35 * 16000


def test_short_sources_are_a_failure_not_an_implicit_quality_pass(preparer):
    with pytest.raises(preparer.PreparationError, match="insufficient_source_duration"):
        preparer.select_utterances([{"id": "one", "frames": 20 * 16000}])


@pytest.mark.parametrize("seconds", [45, 60])
def test_single_whole_utterance_can_fill_the_declared_clip_limit(preparer, seconds):
    row = {"id": "whole", "frames": seconds * 16000}
    assert preparer.select_utterances([row]) == [row]


def test_over_limit_utterance_is_skipped_without_replacing_the_person(preparer):
    rows = [{"id": "long", "frames": 61 * 16000}, {"id": "fits", "frames": 35 * 16000}]
    assert preparer.select_utterances(rows) == [rows[1]]


def test_exclusion_manifest_is_hash_bound_and_collects_all_sources(preparer, tmp_path):
    path = tmp_path / "old.json"
    data = {
        "gallery_order": ["ls-1"],
        "unknown_order": ["ls-2"],
        "recordings": [
            {"speaker_id": "ls-1", "source_utterance_ids": ["1-2-3"], "sha256": "a" * 64}
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    result = preparer.load_exclusions([(path, expected)])
    assert result["people"] == {"ls-1", "ls-2"}
    assert result["utterances"] == {"1-2-3"}
    assert result["recording_hashes"] == {"a" * 64}
    path.write_text(json.dumps({**data, "unknown_order": []}), encoding="utf-8")
    with pytest.raises(preparer.PreparationError, match="exclusion_manifest_changed"):
        preparer.load_exclusions([(path, expected)])


def source(tmp_path, identity, seconds, frequency):
    path = tmp_path / f"{identity}.flac"
    frames = round(seconds * 16000)
    pcm = (np.sin(np.arange(frames) * frequency / 16000) * 12000).astype("int16")
    sf.write(path, pcm, 16000, format="FLAC", subtype="PCM_16")
    return {"id": identity, "path": path, "frames": frames, "reference": "TWO WORDS"}, pcm


def test_actual_flac_pcm_reference_and_frame_provenance(preparer, tmp_path):
    first, first_pcm = source(tmp_path, "1-2-3", 20, 201)
    second, second_pcm = source(tmp_path, "1-2-4", 20, 397)
    output = tmp_path / "result"
    result = preparer.write_clip([first, second], output, "clip", set())
    with wave.open(str(output / result["path"]), "rb") as audio:
        assert (audio.getnchannels(), audio.getframerate(), audio.getsampwidth()) == (1, 16000, 2)
        actual = audio.readframes(audio.getnframes())
    expected = np.concatenate([first_pcm, second_pcm]).astype("<i2").tobytes()
    assert actual == expected
    assert result["pcm_sha256"] == hashlib.sha256(actual).hexdigest()
    assert result["sha256"] == hashlib.sha256((output / result["path"]).read_bytes()).hexdigest()
    assert result["duration_seconds"] == 40 and result["reference_word_count"] == 4
    assert (output / result["reference_path"]).read_text() == "TWO WORDS TWO WORDS\n"
    assert [(r["output_start_frame"], r["output_end_frame"]) for r in result["sources"]] == [
        (0, 320000),
        (320000, 640000),
    ]
    assert all(
        r["source_start_frame"] == 0 and r["source_end_frame"] == 320000 for r in result["sources"]
    )
    for row, original in zip(result["sources"], [first, second], strict=True):
        assert row["flac_sha256"] == hashlib.sha256(original["path"].read_bytes()).hexdigest()
        assert (
            hashlib.sha256((output / row["reference_path"]).read_bytes()).hexdigest()
            == row["reference_sha256"]
        )


@pytest.mark.parametrize("seconds", [45, 60])
def test_complete_long_utterance_passes_real_meeting_clip_verification(preparer, tmp_path, seconds):
    original, _ = source(tmp_path, "1-2-3", seconds, 201)
    output = tmp_path / "result"
    result = preparer.write_clip([original], output, "clip", set())
    assert (
        preparer.verify_meeting_clip(output, {**result, "status": "succeeded"})
        == (output / result["path"]).absolute()
    )


def test_existing_outputs_are_immutable_and_exact_retry_is_identical(preparer, tmp_path):
    original, _ = source(tmp_path, "1-2-3", 35, 201)
    output = tmp_path / "result"
    result = preparer.write_clip([original], output, "clip", set())
    assert preparer.write_clip([original], output, "clip", set()) == result
    (output / result["path"]).write_bytes(b"user content")
    with pytest.raises(preparer.PreparationError, match="existing_file_conflict"):
        preparer.write_clip([original], output, "clip", set())
    assert (output / result["path"]).read_bytes() == b"user content"


def test_changed_source_frames_and_excluded_waveform_fail(preparer, tmp_path):
    original, _ = source(tmp_path, "1-2-3", 35, 201)
    with pytest.raises(preparer.PreparationError, match="source_frames_changed"):
        preparer.write_clip(
            [{**original, "frames": original["frames"] + 1}], tmp_path / "bad", "clip", set()
        )
    result = preparer.write_clip([original], tmp_path / "good", "clip", set())
    with pytest.raises(preparer.PreparationError, match="excluded_recording_hash"):
        preparer.write_clip([original], tmp_path / "excluded", "clip", {result["sha256"]})
    assert not (tmp_path / "excluded/audio/clip.wav").exists()


def test_duplicate_transcript_id_and_cross_chapter_reference_are_rejected(preparer, tmp_path):
    chapter = tmp_path / "1" / "2"
    chapter.mkdir(parents=True)
    path = chapter / "1-2.trans.txt"
    path.write_text("1-2-3 WORD\n1-2-3 WORD\n")
    with pytest.raises(preparer.PreparationError, match="invalid_transcript_inventory"):
        preparer.read_references(chapter)
    path.write_text("1-9-3 WORD\n")
    with pytest.raises(preparer.PreparationError, match="invalid_transcript_inventory"):
        preparer.read_references(chapter)


def test_stage_probe_roles_preserve_the_same_fixed_sources(preparer):
    known = [f"ls-{n}" for n in range(50)]
    unknown = [f"ls-{n}" for n in range(50, 70)]
    stages = preparer.stage_definitions(known, unknown)
    assert [row["gallery_size"] for row in stages] == [5, 10, 20, 50]
    assert [row["known_probe_count"] for row in stages] == [10, 20, 40, 100]
    assert [row["out_of_gallery_probe_count"] for row in stages] == [90, 80, 60, 0]
    assert all(
        row["never_enrolled_probe_count"] == 40 and row["total_probe_count"] == 140
        for row in stages
    )


def corpus_for_meetings(preparer, tmp_path):
    output = tmp_path / "clips"
    known = [f"ls-{n}" for n in range(5)]
    rows = []
    for person, identity in enumerate(known):
        for chapter, (role, number) in enumerate(
            [("enrollment", 1), ("known_query", 1), ("known_query", 2)]
        ):
            items = [
                source(
                    tmp_path,
                    f"{person}-{chapter}-{index}",
                    duration,
                    201 + person * 13 + chapter * 7 + index,
                )[0]
                for index, duration in enumerate([20, 15])
            ]
            identifier = f"{identity}-{role}-{number}"
            rows.append(
                {
                    "id": identifier,
                    "speaker_id": identity,
                    "role": role,
                    "query_index": number,
                    "chapter_id": str(chapter),
                    "status": "succeeded",
                    **preparer.write_clip(items, output, identifier, set()),
                }
            )
    manifest = {
        "protocol_id": preparer.SEED,
        "preparation_status": "complete",
        "gallery_order": known,
        "recordings": rows,
    }
    path = output / "protocol.json"
    path.write_bytes(preparer.canonical(manifest))
    return path, manifest


def test_whole_utterance_meetings_cover_every_frame_and_reference_once(preparer, tmp_path):
    path, original = corpus_for_meetings(preparer, tmp_path)
    output = tmp_path / "meetings"
    result = preparer.assemble_meetings(path, output, (5,))
    assert result["source_protocol_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(result["cases"]) == 3
    for case in result["cases"]:
        assert len(case["intervals"]) == 10 and case["source_audio_seconds"] == 175
        assert case["duration_seconds"] == 177.25
        assert [r["speaker_id"] for r in case["intervals"]] == original["gallery_order"] * 2
        assert len({r["utterance_id"] for r in case["intervals"]}) == 10
        assert [r["end_frame"] - r["start_frame"] for r in case["intervals"]] == [320000] * 5 + [
            240000
        ] * 5
        with wave.open(str(output / case["path"]), "rb") as recording:
            for interval in case["intervals"]:
                recording.setpos(interval["start_frame"])
                actual = recording.readframes(interval["end_frame"] - interval["start_frame"])
                source_row = next(
                    row for row in original["recordings"] if row["id"] == interval["recording_id"]
                )
                with wave.open(str(path.parent / source_row["path"]), "rb") as clip:
                    clip.setpos(interval["source_start_frame"])
                    expected = clip.readframes(
                        interval["source_end_frame"] - interval["source_start_frame"]
                    )
                assert actual == expected
                assert (
                    hashlib.sha256(
                        (path.parent / interval["reference_path"]).read_bytes()
                    ).hexdigest()
                    == interval["reference_sha256"]
                )
        assert case["reference_word_count"] == 20
    assert preparer.assemble_meetings(path, output, (5,)) == result
    changed = output / result["cases"][0]["path"]
    changed.write_bytes(b"user content")
    with pytest.raises(preparer.PreparationError, match="existing_file_conflict"):
        preparer.assemble_meetings(path, output, (5,))
    assert changed.read_bytes() == b"user content"


def test_meetings_refuse_changed_reference_or_source_before_output(preparer, tmp_path):
    path, original = corpus_for_meetings(preparer, tmp_path)
    reference = path.parent / original["recordings"][0]["sources"][0]["reference_path"]
    reference.write_text("CHANGED\n")
    with pytest.raises(preparer.PreparationError, match="meeting_reference_changed"):
        preparer.assemble_meetings(path, tmp_path / "meetings", (5,))
    assert not (tmp_path / "meetings").exists()


def test_full_plan_preserves_every_short_source_failure(preparer, tmp_path, monkeypatch):
    root = tmp_path / "raw"
    for person in range(70):
        for chapter in range(3):
            folder = root / "train-clean-100" / str(person) / str(chapter)
            folder.mkdir(parents=True)
            identifier = f"{person}-{chapter}-0"
            sf.write(
                folder / f"{identifier}.flac",
                np.ones(16000, dtype="int16"),
                16000,
                subtype="PCM_16",
            )
            (folder / f"{person}-{chapter}.trans.txt").write_text(f"{identifier} WORD\n")
    for name in ["CHAPTERS.TXT", "SPEAKERS.TXT", "BOOKS.TXT"]:
        (root / name).write_text("Software fixture metadata\n")
    manifest = tmp_path / "data/public-speaker-holdout-v2/test.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "gallery_order": [],
                "unknown_order": [],
                "recordings": [],
                "sources": [{"sha256": "a" * 64}],
            }
        )
    )
    monkeypatch.setattr(
        preparer,
        "EXCLUSIONS",
        {
            "data/public-speaker-holdout-v2/test.json": hashlib.sha256(
                manifest.read_bytes()
            ).hexdigest()
        },
    )
    result = preparer.prepare(root, tmp_path / "output", tmp_path)
    assert result["preparation_status"] == "incomplete" and result["preparation_failures"] == 190
    assert len(result["gallery_order"]) == 50 and len(result["unknown_order"]) == 20
    assert len(result["recordings"]) == 190
    assert all(
        row["status"] == "failed" and row["error_code"] == "insufficient_source_duration"
        for row in result["recordings"]
    )
    assert not (tmp_path / "output/audio").exists()
    assert (tmp_path / "output/protocol.json").read_bytes() == preparer.canonical(result)


@pytest.mark.parametrize("relative", ["../outside.txt", "../../outside.wav"])
def test_meeting_artifact_path_cannot_leave_frozen_root(preparer, tmp_path, relative):
    with pytest.raises(preparer.PreparationError, match="unsafe_artifact_path"):
        preparer.contained_path(tmp_path / "clips", relative)
