"""Prepare the frozen independent identity corpus offline; never run a voice model."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

SEED = "voiceup-meeting-identity-independent-v1"
RATE = 16000
TARGET_FRAMES = 35 * RATE
MAX_FRAMES = 60 * RATE
EXCLUSIONS = {
    "data/public-speaker-evaluation/calibration.json": "a170d8fa88a13bd7059cd3e6e82747e3b05b7dfc7a814a451672cb4f98ac5c33",
    "data/public-speaker-evaluation/test.json": "0e4deb4d61e36e378a29e270fc4d1c070d3331a9839314f37261c403d1361ad9",
    "data/public-speaker-holdout-v2/test.json": "67fa0170afbe4c3a382a91506cd68d3e635fe7c1d562810c5fe9c2b8ad3c9eb7",
}


class PreparationError(Exception):
    """Stable bounded failure; never include source text or environment secrets."""


def safe_path(path: Path) -> Path:
    for component in (path, *path.parents):
        if component.is_symlink() or component.is_junction():
            raise PreparationError("symlink_refused")
    return path


def digest(path: Path) -> str:
    with safe_path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def immutable_write(path: Path, content: bytes) -> None:
    safe_path(path)
    if path.exists():
        if not path.is_file() or path.read_bytes() != content:
            raise PreparationError("existing_file_conflict")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def ordered(values, salt: str):
    return sorted(
        values,
        key=lambda value: (hashlib.sha256(f"{SEED}|{salt}|{value}".encode()).digest(), value),
    )


def load_exclusions(paths: list[tuple[Path, str]]) -> dict:
    people, utterances, recording_hashes, manifests = set(), set(), set(), []
    for path, expected in paths:
        if digest(path) != expected:
            raise PreparationError("exclusion_manifest_changed")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        people.update(manifest["gallery_order"] + manifest["unknown_order"])
        for row in manifest["recordings"]:
            people.add(row["speaker_id"])
            utterances.update(row["source_utterance_ids"])
            recording_hashes.add(row["sha256"])
        manifests.append({"name": path.parent.name + "/" + path.name, "sha256": expected})
    return {
        "people": people,
        "utterances": utterances,
        "recording_hashes": recording_hashes,
        "manifests": manifests,
    }


def source_inventory(root: Path) -> dict:
    safe_path(root)
    result = {}
    for speaker in sorted((root / "train-clean-100").iterdir()):
        if not speaker.is_dir() or not speaker.name.isdigit():
            raise PreparationError("invalid_source_inventory")
        safe_path(speaker)
        chapters = {}
        for chapter in sorted(speaker.iterdir()):
            safe_path(chapter)
            if not chapter.is_dir() or not chapter.name.isdigit():
                raise PreparationError("invalid_source_inventory")
            paths = sorted(chapter.glob("*.flac"))
            if not paths or any(
                not re.fullmatch(rf"{speaker.name}-{chapter.name}-\d+", path.stem) for path in paths
            ):
                raise PreparationError("invalid_source_inventory")
            chapters[chapter.name] = paths
        result["ls-" + speaker.name] = chapters
    return result


def select_people(inventory: dict, excluded: set[str]) -> tuple[list[str], list[str]]:
    known = ordered(
        [
            person
            for person, chapters in inventory.items()
            if person not in excluded and len(chapters) >= 3
        ],
        "known",
    )[:50]
    if len(known) != 50:
        raise PreparationError("insufficient_known_people")
    unknown = ordered(
        [
            person
            for person, chapters in inventory.items()
            if person not in excluded and person not in known and len(chapters) >= 2
        ],
        "unknown",
    )[:20]
    if len(unknown) != 20:
        raise PreparationError("insufficient_unknown_people")
    return known, unknown


def select_utterances(
    rows, *, target_frames: int = TARGET_FRAMES, max_frames: int = MAX_FRAMES
) -> list[dict]:
    selected, frames = [], 0
    for row in rows:
        count = row["frames"]
        if type(count) is not int or count <= 0:
            raise PreparationError("unexpected_audio_format")
        if frames + count > max_frames:
            continue
        selected.append(row)
        frames += count
        if frames >= target_frames:
            return selected
    raise PreparationError("insufficient_source_duration")


def read_references(chapter: Path) -> dict[str, str]:
    prefix = chapter.parent.name + "-" + chapter.name
    path = safe_path(chapter / f"{prefix}.trans.txt")
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        identifier, separator, content = line.partition(" ")
        if (
            not separator
            or not content.strip()
            or not re.fullmatch(rf"{prefix}-\d+", identifier)
            or identifier in result
        ):
            raise PreparationError("invalid_transcript_inventory")
        result[identifier] = " ".join(content.split())
    return result


def utterance_rows(paths: list[Path], excluded: set[str]):
    references = read_references(paths[0].parent)
    lookup = {path.stem: path for path in paths}
    if set(references) != set(lookup):
        raise PreparationError("transcript_audio_mismatch")
    for identifier in ordered(lookup, "utterance"):
        if identifier in excluded:
            raise PreparationError("excluded_source_utterance")
        path = safe_path(lookup[identifier])
        info = sf.info(path)
        if (info.samplerate, info.channels, info.subtype, info.format) != (
            RATE,
            1,
            "PCM_16",
            "FLAC",
        ):
            raise PreparationError("unexpected_audio_format")
        yield {
            "id": identifier,
            "path": path,
            "frames": info.frames,
            "reference": references[identifier],
        }


def write_clip(rows: list[dict], output: Path, identifier: str, excluded_hashes: set[str]) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise PreparationError("invalid_recording_id")
    if not TARGET_FRAMES <= sum(row["frames"] for row in rows) <= MAX_FRAMES:
        raise PreparationError("invalid_clip_duration")
    arrays, sources, references, frame = [], [], [], 0
    for row in rows:
        path = safe_path(row["path"])
        before = digest(path)
        pcm, rate = sf.read(path, dtype="int16", always_2d=True)
        if len(pcm) != row["frames"]:
            raise PreparationError("source_frames_changed")
        if rate != RATE or pcm.shape[1] != 1 or digest(path) != before:
            raise PreparationError("source_content_changed")
        content = (row["reference"] + "\n").encode("utf-8")
        ref_path = f"references/utterances/{row['id']}.txt"
        sources.append(
            {
                "utterance_id": row["id"],
                "flac_sha256": before,
                "source_start_frame": 0,
                "source_end_frame": len(pcm),
                "output_start_frame": frame,
                "output_end_frame": frame + len(pcm),
                "reference_path": ref_path,
                "reference_sha256": hashlib.sha256(content).hexdigest(),
                "reference_word_count": len(row["reference"].split()),
            }
        )
        arrays.append(pcm)
        references.append(row["reference"])
        frame += len(pcm)
    pcm_bytes = np.concatenate(arrays).astype("<i2", copy=False).tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        target.writeframes(pcm_bytes)
    payload = buffer.getvalue()
    wav_hash = hashlib.sha256(payload).hexdigest()
    if wav_hash in excluded_hashes:
        raise PreparationError("excluded_recording_hash")
    reference = (" ".join(references) + "\n").encode("utf-8")
    path = f"audio/{identifier}.wav"
    reference_path = f"references/{identifier}.txt"
    immutable_write(output / path, payload)
    immutable_write(output / reference_path, reference)
    for source, row in zip(sources, rows, strict=True):
        immutable_write(
            output / source["reference_path"], (row["reference"] + "\n").encode("utf-8")
        )
    return {
        "path": path,
        "sha256": wav_hash,
        "pcm_sha256": hashlib.sha256(pcm_bytes).hexdigest(),
        "frames": frame,
        "duration_seconds": frame / RATE,
        "sample_rate": RATE,
        "reference_path": reference_path,
        "reference_sha256": hashlib.sha256(reference).hexdigest(),
        "reference_word_count": len(reference.decode("utf-8").split()),
        "sources": sources,
    }


def stage_definitions(known: list[str], unknown: list[str]) -> list[dict]:
    return [
        {
            "gallery_size": size,
            "gallery_order": known[:size],
            "known_probe_count": size * 2,
            "out_of_gallery_probe_count": (len(known) - size) * 2,
            "never_enrolled_probe_count": len(unknown) * 2,
            "total_probe_count": (len(known) + len(unknown)) * 2,
        }
        for size in (5, 10, 20, 50)
    ]


def prepare(root: Path, output: Path, workspace: Path) -> dict:
    exclusions = load_exclusions([(workspace / path, sha) for path, sha in EXCLUSIONS.items()])
    inventory = source_inventory(root)
    known, unknown = select_people(inventory, exclusions["people"])
    planned = []
    for person in known + unknown:
        chapters = ordered(inventory[person], "chapter|" + person)
        roles = (
            [("enrollment", 1), ("known_query", 1), ("known_query", 2)]
            if person in known
            else [("unknown_query", 1), ("unknown_query", 2)]
        )
        for chapter, (role, number) in zip(chapters, roles):
            planned.append(
                {
                    "id": f"{person}-{role}-{number}",
                    "speaker_id": person,
                    "role": role,
                    "query_index": number,
                    "chapter_id": chapter,
                }
            )
    inventory_value = {
        person: {chapter: [p.stem for p in paths] for chapter, paths in chapters.items()}
        for person, chapters in inventory.items()
    }
    source_manifest = json.loads(
        (workspace / "data/public-speaker-holdout-v2/test.json").read_text(encoding="utf-8")
    )
    selection = {
        "schema_version": 1,
        "protocol_id": SEED,
        "seed": SEED,
        "preparer_sha256": digest(Path(__file__)),
        "exclusion_manifests": exclusions["manifests"],
        "source_inventory_sha256": hashlib.sha256(canonical(inventory_value)).hexdigest(),
        "source_metadata": [
            {"name": name, "sha256": digest(root / name)}
            for name in ("CHAPTERS.TXT", "SPEAKERS.TXT", "BOOKS.TXT")
        ],
        "source_archive": source_manifest["sources"][0],
        "source_archive_verification": "Previously verified archive identity; selected FLAC files are hashed in this preparation.",
        "selection_counts": {
            "source_people": len(inventory),
            "remaining_people": sum(p not in exclusions["people"] for p in inventory),
            "remaining_two_chapters": sum(
                p not in exclusions["people"] and len(c) >= 2 for p, c in inventory.items()
            ),
            "remaining_three_chapters": sum(
                p not in exclusions["people"] and len(c) >= 3 for p, c in inventory.items()
            ),
        },
        "gallery_order": known,
        "unknown_order": unknown,
        "stages": stage_definitions(known, unknown),
        "policy": {
            "target_seconds": 35,
            "maximum_seconds": 60,
            "whole_utterances": True,
            "model_based_selection": False,
            "voiced_duration_prevalidated": False,
            "replace_failed_people": False,
            "query_auto_enrollment": False,
        },
        "planned_recordings": planned,
    }
    immutable_write(output / "selection.json", canonical(selection))
    recordings, used_sources, used_hashes = [], set(), set()
    for plan in planned:
        row = dict(plan)
        try:
            sources = select_utterances(
                utterance_rows(
                    inventory[row["speaker_id"]][row["chapter_id"]], exclusions["utterances"]
                )
            )
            if used_sources.intersection(source["id"] for source in sources):
                raise PreparationError("repeated_source_utterance")
            result = write_clip(sources, output, row["id"], exclusions["recording_hashes"])
            if used_hashes.intersection(source["flac_sha256"] for source in result["sources"]):
                raise PreparationError("repeated_source_content")
            row.update(result, status="succeeded")
            used_sources.update(source["id"] for source in sources)
            used_hashes.update(source["flac_sha256"] for source in result["sources"])
        except PreparationError as error:
            if str(error) != "insufficient_source_duration":
                raise
            row.update(status="failed", error_code=str(error))
        recordings.append(row)
    failures = sum(row["status"] == "failed" for row in recordings)
    result = {
        **selection,
        "selection_sha256": digest(output / "selection.json"),
        "preparation_status": "incomplete" if failures else "complete",
        "preparation_failures": failures,
        "recordings": recordings,
        "limitations": [
            "English audiobook corpus, not representative Turkish meetings.",
            "Distinct chapters do not prove different sessions or microphones.",
            "Audio duration does not prove usable speech duration.",
            "Corpus speech boundaries are not manually annotated.",
            "Person overlap with pretrained model training remains unverified.",
        ],
    }
    immutable_write(output / "protocol.json", canonical(result))
    return result


def contained_path(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise PreparationError("unsafe_artifact_path")
    return safe_path(path)


def verify_meeting_clip(root: Path, row: dict) -> Path:
    if row["status"] != "succeeded" or not TARGET_FRAMES <= row["frames"] <= MAX_FRAMES:
        raise PreparationError("meeting_clip_unavailable")
    path = contained_path(root, row["path"])
    if digest(path) != row["sha256"]:
        raise PreparationError("meeting_source_changed")
    with wave.open(str(path), "rb") as recording:
        if (
            recording.getnchannels(),
            recording.getsampwidth(),
            recording.getframerate(),
            recording.getnframes(),
            recording.getcomptype(),
        ) != (1, 2, RATE, row["frames"], "NONE"):
            raise PreparationError("meeting_source_format")
    frame, reference_parts, identifiers = 0, [], set()
    for source in row["sources"]:
        if (
            source["utterance_id"] in identifiers
            or source["output_start_frame"] != frame
            or source["source_start_frame"] != 0
        ):
            raise PreparationError("meeting_source_coverage")
        frames = source["output_end_frame"] - frame
        if not 0 < frames <= row["frames"] - frame or source["source_end_frame"] != frames:
            raise PreparationError("meeting_source_coverage")
        reference = contained_path(root, source["reference_path"])
        if digest(reference) != source["reference_sha256"]:
            raise PreparationError("meeting_reference_changed")
        content = reference.read_text(encoding="utf-8").strip()
        if len(content.split()) != source["reference_word_count"]:
            raise PreparationError("meeting_reference_changed")
        reference_parts.append(content)
        identifiers.add(source["utterance_id"])
        frame = source["output_end_frame"]
    if frame != row["frames"]:
        raise PreparationError("meeting_source_coverage")
    combined = (" ".join(reference_parts) + "\n").encode("utf-8")
    if (
        hashlib.sha256(combined).hexdigest() != row["reference_sha256"]
        or digest(contained_path(root, row["reference_path"])) != row["reference_sha256"]
    ):
        raise PreparationError("meeting_reference_changed")
    return path


def assemble_meetings(manifest_path: Path, output: Path, sizes: tuple[int, ...]) -> dict:
    manifest = json.loads(safe_path(manifest_path).read_text(encoding="utf-8"))
    if manifest["protocol_id"] != SEED or manifest["preparation_status"] != "complete":
        raise PreparationError("meeting_protocol_incomplete")
    if (
        not sizes
        or len(set(sizes)) != len(sizes)
        or any(
            size not in (5, 10, 20, 50) or size > len(manifest["gallery_order"]) for size in sizes
        )
    ):
        raise PreparationError("invalid_meeting_sizes")
    lookup = {
        (row["speaker_id"], row["role"], row["query_index"]): row for row in manifest["recordings"]
    }
    if len(lookup) != len(manifest["recordings"]):
        raise PreparationError("duplicate_recording")
    root = manifest_path.parent
    specifications = []
    for size in sizes:
        for name, role, number in (
            ("a-enrollment", "enrollment", 1),
            ("b-return", "known_query", 1),
            ("c-return", "known_query", 2),
        ):
            rows = [lookup[person, role, number] for person in manifest["gallery_order"][:size]]
            paths = [verify_meeting_clip(root, row) for row in rows]
            specifications.append((size, name, rows, paths))
    cases = []
    for size, name, rows, paths in specifications:
        buffer, intervals, frame, source_frames = io.BytesIO(), [], 0, 0
        with wave.open(buffer, "wb") as target:
            target.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            for index in range(max(len(row["sources"]) for row in rows)):
                for row, path in zip(rows, paths, strict=True):
                    if index >= len(row["sources"]):
                        continue
                    source = row["sources"][index]
                    count = source["output_end_frame"] - source["output_start_frame"]
                    with wave.open(str(path), "rb") as clip:
                        clip.setpos(source["output_start_frame"])
                        pcm = clip.readframes(count)
                    if len(pcm) != count * 2:
                        raise PreparationError("meeting_source_changed")
                    if intervals:
                        target.writeframesraw(b"\x00\x00" * (RATE // 4))
                        frame += RATE // 4
                    target.writeframesraw(pcm)
                    intervals.append(
                        {
                            "speaker_id": row["speaker_id"],
                            "recording_id": row["id"],
                            "recording_sha256": row["sha256"],
                            "utterance_id": source["utterance_id"],
                            "start_frame": frame,
                            "end_frame": frame + count,
                            "start_seconds": frame / RATE,
                            "end_seconds": (frame + count) / RATE,
                            "source_start_frame": source["output_start_frame"],
                            "source_end_frame": source["output_end_frame"],
                            "reference_path": source["reference_path"],
                            "reference_sha256": source["reference_sha256"],
                            "reference_word_count": source["reference_word_count"],
                        }
                    )
                    frame += count
                    source_frames += count
        # Recheck the bound source after reading, before publishing its derivative.
        if any(digest(path) != row["sha256"] for row, path in zip(rows, paths, strict=True)):
            raise PreparationError("meeting_source_changed")
        if len({row["utterance_id"] for row in intervals}) != len(intervals):
            raise PreparationError("repeated_source_utterance")
        payload = buffer.getvalue()
        filename = f"meeting-{size:02d}-{name}.wav"
        immutable_write(output / filename, payload)
        cases.append(
            {
                "name": name,
                "path": filename,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "expected_speakers": size,
                "frames": frame,
                "duration_seconds": frame / RATE,
                "source_audio_seconds": source_frames / RATE,
                "sample_rate": RATE,
                "gap_seconds": 0.25,
                "reference_word_count": sum(row["reference_word_count"] for row in intervals),
                "intervals": intervals,
            }
        )
    result = {
        "schema_version": 1,
        "protocol_id": SEED + "-whole-utterance-meetings",
        "source_protocol_sha256": digest(manifest_path),
        "source_protocol_reference_base": "Paths in intervals are relative to the original clip protocol directory.",
        "sizes": list(sizes),
        "cases": cases,
        "limitations": [
            "Constructed, nonoverlapping audiobook meetings; no manual speech-activity boundaries.",
            "Prepared sources are not evidence of an executed model evaluation.",
        ],
    }
    immutable_write(output / "protocol.json", canonical(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path, default=Path("data/public-speaker-holdout-v2/raw/LibriSpeech")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/meeting-identity-independent-v1/fixtures")
    )
    parser.add_argument("--meeting-sizes", type=int, nargs="+", choices=(5, 10, 20, 50))
    parser.add_argument("--meeting-output", type=Path)
    args = parser.parse_args()
    result = prepare(args.source_root, args.output, Path(__file__).resolve().parents[1])
    if args.meeting_sizes and result["preparation_status"] == "complete":
        assemble_meetings(
            args.output / "protocol.json",
            args.meeting_output or args.output / "meetings",
            tuple(args.meeting_sizes),
        )
    print(
        json.dumps(
            {
                "protocol_id": SEED,
                "preparation_status": result["preparation_status"],
                "recordings": len(result["recordings"]),
                "failures": result["preparation_failures"],
                "protocol_sha256": digest(args.output / "protocol.json"),
            }
        )
    )
    return int(result["preparation_failures"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
