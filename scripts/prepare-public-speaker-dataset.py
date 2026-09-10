"""Prepare a deterministic, chapter-separated LibriSpeech identity evaluation.

Downloads occur only in this explicit preparation tool. Application and model
runtime egress remain unchanged. No model output participates in selection.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import ntpath
import re
import tarfile
import time
import urllib.request
from collections import defaultdict
from pathlib import Path, PurePosixPath, PureWindowsPath

import numpy as np
import soundfile as sf

SAMPLE_RATE = 16000
SEED = "voiceup-librispeech-open-set-v1"
FRESH_SEED = "voiceup-librispeech-open-set-v2"
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20000
FRESH_MAX_EXTRACTED_BYTES = 12 * 1024**3
FRESH_MAX_ARCHIVE_MEMBERS = 60000
ORIGINAL_SOURCE_SPLITS = ("dev-clean", "dev-other", "test-clean", "test-other")
EXPECTED_ORIGINAL_SPEAKERS = {"dev-clean": 40, "dev-other": 33, "test-clean": 40, "test-other": 33}
SOURCES = {
    "dev-clean": (337926286, "42e2234ba48799c1f50f24a7926300a1"),
    "dev-other": (314305928, "c8d0bcc9cca99d4f8b62fcc847357931"),
    "test-clean": (346663984, "32fa31d27d2e1cad72775fee3f4849a9"),
    "test-other": (328757843, "fb5a50374b501bb3bac4815ee91d3135"),
    "train-clean-100": (6387309499, "2a93770f6d5c6c964bc36631d331a522"),
}
LIMITATIONS = [
    "English audiobook speech is not representative Turkish meeting speech.",
    "Different source chapters do not prove different recording days or microphones.",
    "Whole utterances are concatenated without repetition; joins are artificial.",
    "Queries sharing a chapter or speaker are correlated observations.",
    "Corpus labels are used without identifying readers by their real-world names.",
    "Speech purity follows corpus provenance and is not individually human-audited here.",
    "Declared VoxCeleb training differs from this corpus; person-level overlap is unverified.",
    "Audio duration includes silence; quality rejection must remain in the evaluation denominator.",
]


class PreparationError(Exception):
    """Stable preparation failure without leaking environment or credentials."""


def safe_path(path: Path) -> Path:
    for component in (path, *path.parents):
        if component.is_symlink() or component.is_junction():
            raise PreparationError("symlink_refused")
    return path


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with safe_path(path).open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_once(path: Path, content: bytes) -> None:
    safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file() or path.stat().st_size != len(content):
            raise PreparationError("existing_file_conflict")
        if file_hash(path, "sha256") != hashlib.sha256(content).hexdigest():
            raise PreparationError("existing_file_conflict")
        return
    with path.open("xb") as target:
        target.write(content)


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PreparationError("download_redirect_refused")


def download_archive(split: str, archive_root: Path) -> tuple[Path, dict]:
    expected_size, expected_md5 = SOURCES[split]
    url = f"https://www.openslr.org/resources/12/{split}.tar.gz"
    archive_root = safe_path(archive_root)
    archive_root.mkdir(parents=True, exist_ok=True)
    target = safe_path(archive_root / f"{split}.tar.gz")
    if not target.exists():
        partial = safe_path(target.with_suffix(target.suffix + ".part"))
        if partial.exists():
            raise PreparationError("incomplete_download_exists")
        opener = urllib.request.build_opener(RefuseRedirect())
        request = urllib.request.Request(url, headers={"User-Agent": SEED})
        deadline = time.monotonic() + 1800
        received = 0
        with opener.open(request, timeout=30) as response, partial.open("xb") as output:
            if response.status != 200 or response.geturl() != url:
                raise PreparationError("unexpected_download_response")
            if response.headers.get("Content-Length") != str(expected_size):
                raise PreparationError("unexpected_download_size")
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > expected_size or time.monotonic() > deadline:
                    raise PreparationError("download_limit")
                output.write(chunk)
        if received != expected_size or file_hash(partial, "md5") != expected_md5:
            raise PreparationError("archive_integrity_failed")
        partial.rename(target)
    if target.stat().st_size != expected_size or file_hash(target, "md5") != expected_md5:
        raise PreparationError("archive_integrity_failed")
    return target, {
        "split": split,
        "url": url,
        "size_bytes": expected_size,
        "upstream_md5": expected_md5,
        "sha256": file_hash(target, "sha256"),
        "license": "CC-BY-4.0",
        "attribution": "LibriSpeech: Panayotov, Chen, Povey and Khudanpur, ICASSP 2015; OpenSLR SLR12.",
    }


def member_path(name: str) -> PurePosixPath:
    posix, windows = PurePosixPath(name), PureWindowsPath(name)
    if (
        not name
        or "\\" in name
        or "\x00" in name
        or posix.is_absolute()
        or windows.drive
        or any(part in {"", ".", ".."} for part in name.rstrip("/").split("/"))
        or posix.parts[0] != "LibriSpeech"
        or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in posix.parts)
        or any(part.endswith((".", " ")) for part in posix.parts)
        or ntpath.isreserved(name)
    ):
        raise PreparationError("unsafe_archive_path")
    return posix


def extract_archive(archive: Path, root: Path, *, source_split: str | None = None) -> None:
    safe_path(root)
    if source_split is not None and source_split not in SOURCES:
        raise PreparationError("invalid_source_split")
    max_total = (
        FRESH_MAX_EXTRACTED_BYTES if source_split == "train-clean-100" else MAX_EXTRACTED_BYTES
    )
    max_members = (
        FRESH_MAX_ARCHIVE_MEMBERS if source_split == "train-clean-100" else MAX_ARCHIVE_MEMBERS
    )
    total = 0
    with tarfile.open(safe_path(archive), "r:gz") as source:
        for index, member in enumerate(source, 1):
            relative = member_path(member.name)
            if not (member.isfile() or member.isdir()):
                raise PreparationError("unsupported_archive_member")
            total += member.size
            if (
                index > max_members
                or member.size < 0
                or member.size > MAX_MEMBER_BYTES
                or total > max_total
            ):
                raise PreparationError("archive_limit")
            target = safe_path(root.joinpath(*relative.parts))
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            stream = source.extractfile(member)
            if stream is None:
                raise PreparationError("invalid_archive_file")
            content = stream.read(MAX_MEMBER_BYTES + 1)
            if len(content) != member.size:
                raise PreparationError("invalid_archive_file")
            write_once(target, content)


def ordered(values, salt: str, seed: str = SEED):
    return sorted(
        values, key=lambda value: hashlib.sha256(f"{seed}|{salt}|{value}".encode()).digest()
    )


def inventory_for(root: Path, splits: tuple[str, ...], *, seed: str = SEED) -> dict:
    inventory = defaultdict(lambda: defaultdict(list))
    for split in splits:
        split_root = safe_path(root / "LibriSpeech" / split)
        if not split_root.is_dir():
            raise PreparationError("missing_source_split")
        for path in sorted(split_root.glob("*/*/*.flac")):
            safe_path(path)
            match = re.fullmatch(r"(\d+)-(\d+)-(\d+)\.flac", path.name)
            if match is None or path.parent.name != match[2] or path.parent.parent.name != match[1]:
                raise PreparationError("unexpected_audio_path")
            info = sf.info(path)
            if (
                info.samplerate != SAMPLE_RATE
                or info.channels != 1
                or info.subtype != "PCM_16"
                or info.format != "FLAC"
                or not 0 < info.frames <= SAMPLE_RATE * 40
            ):
                raise PreparationError("unexpected_audio_format")
            inventory[match[1]][match[2]].append(
                {
                    "id": path.stem,
                    "path": path,
                    "frames": info.frames,
                    "source_split": split,
                    "speaker_id": match[1],
                    "chapter_id": match[2],
                }
            )
    for chapters in inventory.values():
        for chapter, utterances in chapters.items():
            lookup = {utterance["id"]: utterance for utterance in utterances}
            chapters[chapter] = [lookup[key] for key in ordered(lookup, "utterance", seed)]
    return {speaker: dict(chapters) for speaker, chapters in inventory.items()}


def clip_groups(utterances: list[dict], seconds: float, count: int) -> list[list[dict]]:
    result, current, frames = [], [], 0
    for utterance in utterances:
        current.append(utterance)
        frames += utterance["frames"]
        if frames >= round(seconds * SAMPLE_RATE):
            result.append(current)
            current, frames = [], 0
            if len(result) == count:
                break
    return result


def known_clips(chapters: dict, enrollment_seconds: float, query_seconds: float, seed: str = SEED):
    chapter_order = ordered(chapters, "chapter", seed)
    for enrollment_chapter in chapter_order:
        enrollment = clip_groups(chapters[enrollment_chapter], enrollment_seconds, 1)
        if not enrollment:
            continue
        queries = []
        for chapter in chapter_order:
            if chapter != enrollment_chapter:
                queries.extend(clip_groups(chapters[chapter], query_seconds, 3 - len(queries)))
                if len(queries) == 3:
                    return enrollment + queries
    return None


def unknown_clips(chapters: dict, query_seconds: float, seed: str = SEED):
    for chapter in ordered(chapters, "chapter", seed):
        queries = clip_groups(chapters[chapter], query_seconds, 5)
        if len(queries) == 5:
            return queries
    return None


def returning_clips(
    chapters: dict, enrollment_seconds: float, query_seconds: float, seed: str = SEED
):
    chapter_order = ordered(chapters, "chapter", seed)
    for unknown_chapter in chapter_order:
        unknown = clip_groups(chapters[unknown_chapter], query_seconds, 5)
        if len(unknown) != 5:
            continue
        for enrollment_chapter in chapter_order:
            if enrollment_chapter == unknown_chapter:
                continue
            enrollment = clip_groups(chapters[enrollment_chapter], enrollment_seconds, 1)
            if not enrollment:
                continue
            for return_chapter in chapter_order:
                if return_chapter in {unknown_chapter, enrollment_chapter}:
                    continue
                query = clip_groups(chapters[return_chapter], query_seconds, 1)
                if query:
                    return unknown + enrollment + query
    return None


def plan_split(
    inventory: dict,
    split: str,
    *,
    known_count: int = 50,
    unknown_count: int = 20,
    enrollment_seconds: float = 30,
    query_seconds: float = 15,
    seed: str = SEED,
) -> dict:
    if split not in {"calibration", "test"}:
        raise PreparationError("invalid_split")
    candidates = ordered(inventory, f"{split}-speaker", seed)
    known = {
        speaker: clips
        for speaker in candidates
        if (clips := known_clips(inventory[speaker], enrollment_seconds, query_seconds, seed))
    }
    unknown = {
        speaker: clips
        for speaker in candidates
        if (clips := unknown_clips(inventory[speaker], query_seconds, seed))
    }
    returning = {
        speaker: clips
        for speaker in candidates
        if (clips := returning_clips(inventory[speaker], enrollment_seconds, query_seconds, seed))
    }
    if not returning:
        raise PreparationError("insufficient_returning_source_chapters")
    return_speaker = next(iter(returning))
    gallery = [speaker for speaker in candidates if speaker in known and speaker != return_speaker][
        :known_count
    ]
    unknown_order = [return_speaker] + [
        speaker
        for speaker in candidates
        if speaker in unknown and speaker not in gallery and speaker != return_speaker
    ][: unknown_count - 1]
    if len(gallery) != known_count or len(unknown_order) != unknown_count:
        raise PreparationError("insufficient_eligible_speakers")
    rows = []

    def add(speaker, role, index, utterances):
        public_speaker = f"ls-{speaker}"
        rows.append(
            {
                "id": f"{public_speaker}-{role}-{index}",
                "speaker_id": public_speaker,
                "role": role,
                "source_split": utterances[0]["source_split"],
                "chapter_id": utterances[0]["chapter_id"],
                "utterances": utterances,
                "path": f"clips/{split}/{public_speaker}/{role}-{index}.wav",
            }
        )

    for speaker in gallery:
        add(speaker, "enrollment", 1, known[speaker][0])
        for index, utterances in enumerate(known[speaker][1:], 1):
            add(speaker, "known_query", index, utterances)
    for speaker in unknown_order:
        clips = returning[speaker][:5] if speaker == return_speaker else unknown[speaker]
        for index, utterances in enumerate(clips, 1):
            add(speaker, "unknown_query", index, utterances)
    add(return_speaker, "new_enrollment", 1, returning[return_speaker][5])
    add(return_speaker, "return_query", 1, returning[return_speaker][6])
    used = [utterance["id"] for row in rows for utterance in row["utterances"]]
    if len(used) != len(set(used)):
        raise PreparationError("source_utterance_reuse")
    return {
        "split": split,
        "gallery_order": [f"ls-{speaker}" for speaker in gallery],
        "unknown_order": [f"ls-{speaker}" for speaker in unknown_order],
        "returning_speaker_id": f"ls-{return_speaker}",
        "recordings": rows,
        "inventory_speakers": len(inventory),
        "eligible_known_speakers": len(known),
        "eligible_unknown_speakers": len(unknown),
        "enrollment_min_seconds": enrollment_seconds,
        "query_min_seconds": query_seconds,
    }


def exclusion_inventory(previous_root: Path) -> set[str]:
    speakers = set()
    for split in ORIGINAL_SOURCE_SPLITS:
        current = set(inventory_for(previous_root / "raw", (split,)))
        if len(current) != EXPECTED_ORIGINAL_SPEAKERS[split] or current & speakers:
            raise PreparationError("incomplete_exclusion_inventory")
        speakers.update(current)
    return speakers


def plan_fresh_holdout(inventory: dict, excluded_speakers: set[str], **options) -> dict:
    if not excluded_speakers or any(not re.fullmatch(r"\d+", item) for item in excluded_speakers):
        raise PreparationError("invalid_excluded_speakers")
    eligible = {
        speaker: chapters
        for speaker, chapters in inventory.items()
        if speaker not in excluded_speakers
    }
    plan = plan_split(eligible, "test", seed=FRESH_SEED, **options)
    plan.update(
        selection_seed=FRESH_SEED,
        excluded_speaker_ids=sorted(f"ls-{speaker}" for speaker in excluded_speakers),
        source_inventory_speakers=len(inventory),
    )
    return plan


def write_manifest(plan: dict, root: Path, sources: list[dict]) -> dict:
    rows = []
    for planned in plan["recordings"]:
        arrays = []
        for utterance in planned["utterances"]:
            audio, rate = sf.read(safe_path(utterance["path"]), dtype="int16")
            if rate != SAMPLE_RATE or audio.ndim != 1 or len(audio) != utterance["frames"]:
                raise PreparationError("source_audio_changed")
            arrays.append(audio)
        audio = np.concatenate(arrays)
        if len(audio) > SAMPLE_RATE * 120:
            raise PreparationError("prepared_audio_limit")
        buffer = io.BytesIO()
        sf.write(buffer, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        content = buffer.getvalue()
        write_once(root / planned["path"], content)
        row = {key: value for key, value in planned.items() if key != "utterances"}
        row.update(
            source_utterance_ids=[utterance["id"] for utterance in planned["utterances"]],
            sha256=hashlib.sha256(content).hexdigest(),
            duration_seconds=len(audio) / SAMPLE_RATE,
        )
        rows.append(row)
    seed = plan.get("selection_seed", SEED)
    manifest = {
        "schema_version": 1,
        "dataset_id": f"librispeech-open-set-{'v2' if seed == FRESH_SEED else 'v1'}-{plan['split']}",
        "language": "en",
        "split": plan["split"],
        "gallery_order": plan["gallery_order"],
        "unknown_order": plan["unknown_order"],
        "returning_speaker_id": plan["returning_speaker_id"],
        "protocol": {
            "id": seed,
            "selection_seed": seed,
            "selection_uses_model_results": False,
            "actual_session_independence_verified": False,
            "enrollment_query_chapters_disjoint": True,
            "returning_role_chapters_disjoint": True,
            "source_utterances_disjoint": True,
            "enrollment_min_seconds": plan["enrollment_min_seconds"],
            "query_min_seconds": plan["query_min_seconds"],
            "inventory_speakers": plan["inventory_speakers"],
            "eligible_known_speakers": plan["eligible_known_speakers"],
            "eligible_unknown_speakers": plan["eligible_unknown_speakers"],
            "limitations": LIMITATIONS,
        },
        "sources": sources,
        "recordings": rows,
    }
    if seed == FRESH_SEED:
        excluded = plan["excluded_speaker_ids"]
        manifest["protocol"].update(
            excluded_source_splits=list(ORIGINAL_SOURCE_SPLITS),
            excluded_speaker_ids=excluded,
            excluded_speaker_count=len(excluded),
            excluded_speaker_ids_sha256=hashlib.sha256(
                json.dumps(excluded, separators=(",", ":")).encode()
            ).hexdigest(),
            source_inventory_speakers=plan["source_inventory_speakers"],
            source_split_training_label_is_not_model_training_evidence=True,
        )
    content = (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode()
    write_once(root / f"{plan['split']}.json", content)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
    )
    parser.add_argument(
        "--protocol", choices=("baseline-v1", "fresh-holdout-v2"), default="baseline-v1"
    )
    parser.add_argument(
        "--exclude-root", type=Path, help="Prior evaluation root containing all four raw splits"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Explicitly download archives pinned for the selected protocol",
    )
    args = parser.parse_args()
    fresh = args.protocol == "fresh-holdout-v2"
    default_name = "public-speaker-holdout-v2" if fresh else "public-speaker-evaluation"
    root = safe_path(
        (args.root or Path(__file__).resolve().parents[1] / "data" / default_name).absolute()
    )
    if not args.download:
        raise PreparationError("explicit_download_flag_required")
    excluded = None
    if fresh:
        if args.exclude_root is None:
            raise PreparationError("fresh_exclusion_root_required")
        previous_root = safe_path(args.exclude_root.absolute())
        if root.resolve().is_relative_to(
            previous_root.resolve()
        ) or previous_root.resolve().is_relative_to(root.resolve()):
            raise PreparationError("overlapping_preparation_roots")
        excluded = exclusion_inventory(previous_root)
    elif args.exclude_root is not None:
        raise PreparationError("exclusion_root_requires_fresh_protocol")
    sources = []
    for split in ("train-clean-100",) if fresh else ORIGINAL_SOURCE_SPLITS:
        print(json.dumps({"stage": "prepare_archive", "split": split}), flush=True)
        archive, provenance = download_archive(split, root / "archives")
        extract_archive(archive, root / "raw", source_split=split)
        sources.append(provenance)
    if fresh:
        plan = plan_fresh_holdout(
            inventory_for(root / "raw", ("train-clean-100",), seed=FRESH_SEED), excluded
        )
        manifest = write_manifest(plan, root, sources)
        print(
            json.dumps(
                {
                    "stage": "ready",
                    "split": "test",
                    "recordings": len(manifest["recordings"]),
                    "known_speakers": len(manifest["gallery_order"]),
                    "unknown_speakers": len(manifest["unknown_order"]),
                    "excluded_speakers": len(excluded),
                    "manifest_sha256": file_hash(root / "test.json", "sha256"),
                }
            ),
            flush=True,
        )
        return 0
    plans = []
    for split, source_splits in (
        ("calibration", ("dev-clean", "dev-other")),
        ("test", ("test-clean", "test-other")),
    ):
        plan = plan_split(inventory_for(root / "raw", source_splits), split)
        plans.append(plan)
    calibration_speakers = set(plans[0]["gallery_order"] + plans[0]["unknown_order"])
    test_speakers = set(plans[1]["gallery_order"] + plans[1]["unknown_order"])
    if calibration_speakers & test_speakers:
        raise PreparationError("calibration_test_speaker_overlap")
    for plan in plans:
        manifest = write_manifest(plan, root, sources)
        print(
            json.dumps(
                {
                    "stage": "ready",
                    "split": plan["split"],
                    "recordings": len(manifest["recordings"]),
                    "known_speakers": len(manifest["gallery_order"]),
                    "unknown_speakers": len(manifest["unknown_order"]),
                    "manifest_sha256": file_hash(root / f"{plan['split']}.json", "sha256"),
                }
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PreparationError as error:
        print(json.dumps({"status": "failed", "code": str(error)}), flush=True)
        raise SystemExit(1) from None
    except (OSError, ValueError, tarfile.TarError):
        print(json.dumps({"status": "failed", "code": "preparation_io_failure"}), flush=True)
        raise SystemExit(1) from None
