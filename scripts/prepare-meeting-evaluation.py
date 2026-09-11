"""Prepare deterministic local meeting fixtures from the existing public calibration set."""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
from contextlib import ExitStack
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def assemble(
    sources: list[tuple[str, Path]],
    output: Path,
    *,
    excerpt_seconds: float = 8,
    gap_seconds: float = 0.25,
    limits: dict[str, float] | None = None,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Evaluation output already exists")
    if not 0 < excerpt_seconds <= 120 or not 0 <= gap_seconds <= 10:
        raise ValueError("Invalid fixture timing")
    limits = limits or {}
    intervals: list[dict[str, Any]] = []
    frame = 0
    source_frames = 0
    with ExitStack() as stack:
        readers = []
        for identity, path in sources:
            reader = stack.enter_context(wave.open(str(path), "rb"))
            if (
                reader.getnchannels(),
                reader.getsampwidth(),
                reader.getframerate(),
                reader.getcomptype(),
            ) != (1, 2, 16000, "NONE"):
                raise ValueError("Fixtures require mono 16 kHz PCM16 sources")
            maximum = min(
                reader.getnframes(),
                round(limits.get(identity, reader.getnframes() / 16000) * 16000),
            )
            readers.append((identity, reader, maximum))
        with output.open("xb") as stream, wave.open(stream, "wb") as destination:
            destination.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            while True:
                changed = False
                for identity, reader, maximum in readers:
                    start = reader.tell()
                    count = min(round(excerpt_seconds * 16000), maximum - start)
                    if count <= 0:
                        continue
                    data = reader.readframes(count)
                    if len(data) != count * 2:
                        raise ValueError("Incomplete fixture source")
                    if intervals:
                        gap = round(gap_seconds * 16000)
                        destination.writeframesraw(b"\x00\x00" * gap)
                        frame += gap
                    intervals.append(
                        {
                            "speaker_id": identity,
                            "source_start_frame": start,
                            "source_end_frame": start + count,
                            "start_seconds": frame / 16000,
                            "end_seconds": (frame + count) / 16000,
                        }
                    )
                    destination.writeframesraw(data)
                    frame += count
                    source_frames += count
                    changed = True
                if not changed:
                    break
    return {
        "path": output.name,
        "sha256": digest(output),
        "duration_seconds": frame / 16000,
        "source_audio_seconds": source_frames / 16000,
        "sample_rate": 16000,
        "intervals": intervals,
    }


def prepare(manifest_path: Path, output: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("split") != "calibration" or manifest.get("schema_version") != 1:
        raise ValueError("A version-one calibration manifest is required")
    identities = manifest["gallery_order"][:6]
    if len(set(identities)) != 6:
        raise ValueError("Six distinct predeclared identities are required")
    root = manifest_path.parent.resolve()
    selected: dict[tuple[str, str, int], Path] = {}
    input_rows = []
    for identity in identities:
        for role, number in [
            ("enrollment", 1),
            ("known_query", 1),
            ("known_query", 2),
            ("known_query", 3),
        ]:
            row = next(
                item
                for item in manifest["recordings"]
                if item["id"] == f"{identity}-{role}-{number}"
            )
            path = (root / row["path"]).resolve()
            if not path.is_relative_to(root) or not path.is_file() or digest(path) != row["sha256"]:
                raise ValueError("Fixture source inventory mismatch")
            selected[identity, role, number] = path
            input_rows.append(
                {
                    key: row[key]
                    for key in (
                        "id",
                        "speaker_id",
                        "role",
                        "sha256",
                        "source_utterance_ids",
                        "chapter_id",
                    )
                }
            )
    names = [
        "meeting-a-five.wav",
        "meeting-b-return.wav",
        "meeting-d-short-sixth.wav",
        "meeting-c-sixth-new.wav",
        "protocol.json",
    ]
    if any((output / name).exists() for name in names):
        raise FileExistsError("Refusing to overwrite an existing evaluation protocol")
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    specifications = [
        (
            names[0],
            [(identity, selected[identity, "enrollment", 1]) for identity in identities[:5]],
            {},
            5,
            5,
        ),
        (
            names[1],
            [
                (identity, selected[identity, "known_query", 1])
                for identity in reversed(identities[:5])
            ],
            {},
            5,
            5,
        ),
        (
            names[2],
            [(identity, selected[identity, "known_query", 3]) for identity in identities[:5]]
            + [(identities[5], selected[identities[5], "enrollment", 1])],
            {identities[5]: 3},
            6,
            5,
        ),
        (
            names[3],
            [(identities[5], selected[identities[5], "enrollment", 1])]
            + [(identity, selected[identity, "known_query", 2]) for identity in identities[:5]],
            {},
            6,
            6,
        ),
    ]
    for name, sources, limits, speakers, profiles in specifications:
        case = assemble(sources, output / name, limits=limits)
        case.update({"expected_speakers": speakers, "expected_gallery_total": profiles})
        cases.append(case)
    result = {
        "schema_version": 1,
        "protocol_id": "voiceup-meeting-first-six-v1",
        "selection": "First six existing calibration gallery identities; no selection using this run's model output.",
        "source_manifest_sha256": digest(manifest_path),
        "identities": identities,
        "inputs": input_rows,
        "cases": cases,
        "attribution": "LibriSpeech: Panayotov, Chen, Povey and Khudanpur, ICASSP 2015; OpenSLR SLR12, CC-BY-4.0.",
        "limitations": [
            "Constructed English audiobook mixtures are not representative Turkish meetings.",
            "Reference intervals include the original within-utterance silence; they are not human-annotated speech masks.",
            "Different chapters and disjoint utterances do not prove different microphones or recording days.",
            "Short-sixth excerpt is intentionally repeated later only as a new meeting; never twice in one meeting's clean evidence.",
        ],
    }
    (output / "protocol.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/public-speaker-evaluation/calibration.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/2026-09-10-meeting-delivery/fixtures")
    )
    args = parser.parse_args()
    result = prepare(args.manifest, args.output)
    print(
        json.dumps(
            {
                "protocol_id": result["protocol_id"],
                "cases": len(result["cases"]),
                "identities": result["identities"],
            }
        )
    )


if __name__ == "__main__":
    main()
