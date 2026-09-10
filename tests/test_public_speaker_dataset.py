"""Public-corpus preparation contracts; generated tones are software fixtures only."""

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def preparer():
    path = Path(__file__).resolve().parents[1] / "scripts" / "prepare-public-speaker-dataset.py"
    spec = importlib.util.spec_from_file_location("public_speaker_preparer", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def archive_at(path, entries):
    with tarfile.open(path, "w:gz") as archive:
        for name, content, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(content) if kind == tarfile.REGTYPE else 0
            info.linkname = "outside"
            archive.addfile(info, io.BytesIO(content) if info.isreg() else None)


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("C:/absolute", tarfile.REGTYPE),
        ("LibriSpeech\\escape", tarfile.REGTYPE),
        ("LibriSpeech/link", tarfile.SYMTYPE),
        ("LibriSpeech/link", tarfile.LNKTYPE),
        ("LibriSpeech/device", tarfile.CHRTYPE),
        ("LibriSpeech/a/../escape", tarfile.REGTYPE),
    ],
)
def test_archive_rejects_unsafe_members(preparer, tmp_path, name, kind):
    source = tmp_path / "source.tar.gz"
    archive_at(source, [(name, b"payload", kind)])
    with pytest.raises(preparer.PreparationError):
        preparer.extract_archive(source, tmp_path / "raw")
    assert not (tmp_path / "escape").exists()


def test_extraction_preserves_identical_metadata_and_refuses_conflict(preparer, tmp_path):
    source = tmp_path / "source.tar.gz"
    archive_at(source, [("LibriSpeech/README.TXT", b"license", tarfile.REGTYPE)])
    destination = tmp_path / "raw"
    preparer.extract_archive(source, destination)
    preparer.extract_archive(source, destination)
    target = destination / "LibriSpeech" / "README.TXT"
    target.write_bytes(b"user data")
    with pytest.raises(preparer.PreparationError, match="existing_file_conflict"):
        preparer.extract_archive(source, destination)
    assert target.read_bytes() == b"user data"


def test_extract_member_and_total_limits(preparer, tmp_path, monkeypatch):
    source = tmp_path / "source.tar.gz"
    archive_at(source, [("LibriSpeech/README.TXT", b"123456", tarfile.REGTYPE)])
    monkeypatch.setattr(preparer, "MAX_MEMBER_BYTES", 5)
    with pytest.raises(preparer.PreparationError, match="archive_limit"):
        preparer.extract_archive(source, tmp_path / "raw")


class DownloadResponse(io.BytesIO):
    status = 200

    def __init__(self, content, advertised_size=None):
        super().__init__(content)
        self.headers = {
            "Content-Length": str(len(content) if advertised_size is None else advertised_size)
        }

    def geturl(self):
        return "https://www.openslr.org/resources/12/test-clean.tar.gz"


def download_fixture(preparer, monkeypatch, payload=b"archive bytes", **response_options):
    monkeypatch.setattr(
        preparer, "SOURCES", {"test-clean": (len(payload), hashlib.md5(payload).hexdigest())}
    )
    response = DownloadResponse(response_options.pop("content", payload), **response_options)

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == response.geturl()
            assert timeout == 30
            return response

    monkeypatch.setattr(preparer.urllib.request, "build_opener", lambda *_: Opener())
    return response


def test_download_checks_upstream_digest_and_records_sha256(preparer, tmp_path, monkeypatch):
    payload = b"bounded archive"
    download_fixture(preparer, monkeypatch, payload)
    path, provenance = preparer.download_archive("test-clean", tmp_path)
    assert path.read_bytes() == payload
    assert provenance["upstream_md5"] == hashlib.md5(payload).hexdigest()
    assert provenance["sha256"] == hashlib.sha256(payload).hexdigest()
    assert provenance["license"] == "CC-BY-4.0"
    monkeypatch.setattr(
        preparer.urllib.request, "build_opener", lambda *_: pytest.fail("cache must be reused")
    )
    assert preparer.download_archive("test-clean", tmp_path) == (path, provenance)


@pytest.mark.parametrize("failure", ["length", "hash", "short", "large", "status", "deadline"])
def test_download_failures_never_publish_archive(preparer, tmp_path, monkeypatch, failure):
    payload = b"archive"
    options = {}
    if failure == "length":
        options["advertised_size"] = 1000
    if failure == "hash":
        options["content"] = b"changed"
    if failure in {"short", "large"}:
        options.update(
            content=b"a" if failure == "short" else b"too much data", advertised_size=len(payload)
        )
    response = download_fixture(preparer, monkeypatch, payload, **options)
    if failure == "status":
        response.status = 302
    if failure == "deadline":
        clock = iter((0, 2000))
        monkeypatch.setattr(preparer.time, "monotonic", lambda: next(clock))
    with pytest.raises(preparer.PreparationError):
        preparer.download_archive("test-clean", tmp_path)
    assert not (tmp_path / "test-clean.tar.gz").exists()


def test_existing_tampered_archive_and_partial_are_preserved(preparer, tmp_path, monkeypatch):
    download_fixture(preparer, monkeypatch)
    path = tmp_path / "test-clean.tar.gz"
    path.write_bytes(b"user data")
    with pytest.raises(preparer.PreparationError, match="archive_integrity_failed"):
        preparer.download_archive("test-clean", tmp_path)
    assert path.read_bytes() == b"user data"
    different = tmp_path / "another"
    different.mkdir()
    partial = different / "test-clean.tar.gz.part"
    partial.write_bytes(b"partial user data")
    with pytest.raises(preparer.PreparationError, match="incomplete_download_exists"):
        preparer.download_archive("test-clean", different)
    assert partial.read_bytes() == b"partial user data"


def test_http_redirects_are_refused(preparer):
    with pytest.raises(preparer.PreparationError, match="download_redirect_refused"):
        preparer.RefuseRedirect().redirect_request(
            None, None, 302, "", {}, "https://other.example/audio"
        )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction boundary")
def test_windows_junction_cannot_redirect_output(preparer, tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    junction = tmp_path / "junction"
    created = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    if created.returncode:
        pytest.skip("Junction creation unavailable in this environment")
    assert junction.is_junction()
    with pytest.raises(preparer.PreparationError, match="symlink_refused"):
        preparer.write_once(junction / "new.wav", b"audio")
    assert not (target / "new.wav").exists()


def make_inventory(preparer, root, speakers=8):
    inventory = {}
    for speaker in range(speakers):
        speaker_id = str(100 + speaker)
        chapters = {}
        for chapter in range(3):
            chapter_id = str(1000 + speaker * 3 + chapter)
            utterances = []
            for utterance in range(6):
                utterance_id = f"{speaker_id}-{chapter_id}-{utterance:04d}"
                path = root / f"{utterance_id}.flac"
                amplitude = 100 + speaker * 50 + chapter * 10 + utterance
                sf.write(path, np.full(1600, amplitude, dtype=np.int16), 16000, subtype="PCM_16")
                utterances.append(
                    {
                        "id": utterance_id,
                        "path": path,
                        "frames": 1600,
                        "source_split": "test-clean",
                        "speaker_id": speaker_id,
                        "chapter_id": chapter_id,
                    }
                )
            chapters[chapter_id] = utterances
        inventory[speaker_id] = chapters
    return inventory


def test_plan_is_deterministic_disjoint_and_cross_chapter(preparer, tmp_path):
    inventory = make_inventory(preparer, tmp_path)
    arguments = {
        "known_count": 4,
        "unknown_count": 3,
        "enrollment_seconds": 0.2,
        "query_seconds": 0.1,
    }
    first = preparer.plan_split(inventory, "test", **arguments)
    second = preparer.plan_split(dict(reversed(list(inventory.items()))), "test", **arguments)
    assert first == second
    assert len(first["gallery_order"]) == 4
    assert len(first["unknown_order"]) == 3
    assert not set(first["gallery_order"]) & set(first["unknown_order"])
    rows = first["recordings"]
    assert len(rows) == 4 * 4 + 3 * 5 + 2
    used = [utterance["id"] for row in rows for utterance in row["utterances"]]
    assert len(used) == len(set(used))
    for speaker in first["gallery_order"]:
        own = [row for row in rows if row["speaker_id"] == speaker]
        enrollment = next(row for row in own if row["role"] == "enrollment")
        assert all(
            row["chapter_id"] != enrollment["chapter_id"]
            for row in own
            if row["role"] == "known_query"
        )
    returning = [row for row in rows if row["speaker_id"] == first["returning_speaker_id"]]
    phases = {}
    for row in returning:
        phases.setdefault(row["role"], set()).add(row["chapter_id"])
    assert len(set.union(*phases.values())) == 3


def test_insufficient_cross_chapter_data_is_not_silently_downgraded(preparer, tmp_path):
    inventory = make_inventory(preparer, tmp_path, speakers=3)
    with pytest.raises(preparer.PreparationError, match="insufficient"):
        preparer.plan_split(inventory, "test", known_count=4, unknown_count=3)


def test_preparer_plans_two_hundred_people_without_a_product_quota(preparer, tmp_path):
    inventory = make_inventory(preparer, tmp_path, speakers=201)
    plan = preparer.plan_split(
        inventory,
        "test",
        known_count=200,
        unknown_count=1,
        enrollment_seconds=0.2,
        query_seconds=0.1,
    )
    assert len(plan["gallery_order"]) == 200
    assert len(plan["unknown_order"]) == 1
    assert len(plan["recordings"]) == 807
    assert plan["returning_speaker_id"] not in plan["gallery_order"]


def test_written_manifest_preserves_audio_and_provenance(preparer, tmp_path):
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    plan = preparer.plan_split(
        make_inventory(preparer, fixture_root),
        "test",
        known_count=4,
        unknown_count=3,
        enrollment_seconds=0.2,
        query_seconds=0.1,
    )
    root = tmp_path / "output"
    manifest = preparer.write_manifest(plan, root, [])
    assert manifest["language"] == "en"
    assert manifest["split"] == "test"
    assert manifest["protocol"]["actual_session_independence_verified"] is False
    assert json.loads((root / "test.json").read_text()) == manifest
    for row in manifest["recordings"]:
        path = root / row["path"]
        assert preparer.file_hash(path, "sha256") == row["sha256"]
        audio, rate = sf.read(path, dtype="int16")
        assert rate == 16000
        assert len(audio) / rate == row["duration_seconds"]
        expected = np.concatenate(
            [
                sf.read(utterance["path"], dtype="int16")[0]
                for utterance in next(
                    planned for planned in plan["recordings"] if planned["id"] == row["id"]
                )["utterances"]
            ]
        )
        assert np.array_equal(audio, expected)
    assert preparer.write_manifest(plan, root, []) == manifest


def test_fresh_holdout_excludes_every_prior_reader_and_preserves_v1(preparer, tmp_path):
    inventory = make_inventory(preparer, tmp_path, speakers=10)
    arguments = {
        "known_count": 4,
        "unknown_count": 3,
        "enrollment_seconds": 0.2,
        "query_seconds": 0.1,
    }
    old_plan = preparer.plan_split(inventory, "test", **arguments)
    assert old_plan["gallery_order"] == ["ls-109", "ls-106", "ls-108", "ls-103"]
    assert old_plan["unknown_order"] == ["ls-102", "ls-105", "ls-104"]
    old_manifest = preparer.write_manifest(old_plan, tmp_path / "original", [])
    assert old_manifest["dataset_id"] == "librispeech-open-set-v1-test"
    assert old_manifest["protocol"]["selection_seed"] == "voiceup-librispeech-open-set-v1"
    assert "excluded_speaker_ids" not in old_manifest["protocol"]
    excluded = {"100", "101"}
    fresh = preparer.plan_fresh_holdout(inventory, excluded, **arguments)
    assert fresh == preparer.plan_fresh_holdout(
        dict(reversed(list(inventory.items()))), excluded, **arguments
    )
    selected = set(fresh["gallery_order"] + fresh["unknown_order"])
    assert len(selected) == 7
    assert not selected & {"ls-100", "ls-101"}
    assert fresh["selection_seed"] == "voiceup-librispeech-open-set-v2"
    assert fresh["excluded_speaker_ids"] == ["ls-100", "ls-101"]
    assert preparer.plan_split(inventory, "test", **arguments) == old_plan
    root = tmp_path / "fresh"
    manifest = preparer.write_manifest(fresh, root, [])
    assert manifest["dataset_id"] == "librispeech-open-set-v2-test"
    assert manifest["protocol"]["selection_uses_model_results"] is False
    assert manifest["protocol"]["excluded_speaker_count"] == 2
    assert (
        manifest["protocol"]["excluded_speaker_ids_sha256"]
        == hashlib.sha256(b'["ls-100","ls-101"]').hexdigest()
    )
    assert manifest["protocol"]["selection_seed"] != preparer.SEED
    with pytest.raises(preparer.PreparationError, match="existing_file_conflict"):
        preparer.write_manifest(old_plan, root, [])


def test_fresh_holdout_never_backfills_from_excluded_readers(preparer, tmp_path):
    inventory = make_inventory(preparer, tmp_path)
    with pytest.raises(preparer.PreparationError, match="insufficient_eligible_speakers"):
        preparer.plan_fresh_holdout(
            inventory,
            {"100", "101"},
            known_count=4,
            unknown_count=3,
            enrollment_seconds=0.2,
            query_seconds=0.1,
        )


def test_source_specific_archive_limits_do_not_weaken_original_sources(
    preparer, tmp_path, monkeypatch
):
    source = tmp_path / "source.tar.gz"
    archive_at(source, [("LibriSpeech/README.TXT", b"123456", tarfile.REGTYPE)])
    monkeypatch.setattr(preparer, "MAX_EXTRACTED_BYTES", 5)
    preparer.extract_archive(source, tmp_path / "fresh", source_split="train-clean-100")
    with pytest.raises(preparer.PreparationError, match="archive_limit"):
        preparer.extract_archive(source, tmp_path / "original", source_split="test-clean")
    monkeypatch.setattr(preparer, "FRESH_MAX_EXTRACTED_BYTES", 5)
    with pytest.raises(preparer.PreparationError, match="archive_limit"):
        preparer.extract_archive(source, tmp_path / "limited", source_split="train-clean-100")


@pytest.mark.parametrize("mode", ["missing_exclusions", "overlapping_roots", "no_opt_in"])
def test_fresh_cli_preflights_before_any_network(preparer, tmp_path, monkeypatch, mode):
    args = ["prepare", "--protocol", "fresh-holdout-v2", "--root", str(tmp_path / "fresh")]
    if mode != "missing_exclusions":
        root = tmp_path / "fresh" if mode == "overlapping_roots" else tmp_path / "old"
        args += ["--exclude-root", str(root)]
    if mode != "no_opt_in":
        args += ["--download"]
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(preparer, "download_archive", lambda *_: pytest.fail("preflight required"))
    with pytest.raises(preparer.PreparationError):
        preparer.main()


def test_pinned_fresh_source_and_old_default_sources_are_separate(preparer):
    assert preparer.SOURCES["train-clean-100"] == (6387309499, "2a93770f6d5c6c964bc36631d331a522")
    assert preparer.ORIGINAL_SOURCE_SPLITS == ("dev-clean", "dev-other", "test-clean", "test-other")
    assert preparer.FRESH_MAX_EXTRACTED_BYTES == 12 * 1024**3
    assert preparer.FRESH_MAX_ARCHIVE_MEMBERS == 60000


def test_exclusion_inventory_uses_actual_audio_not_whole_corpus_metadata(
    preparer, tmp_path, monkeypatch
):
    raw = tmp_path / "raw" / "LibriSpeech"
    expected = set()
    for index, split in enumerate(preparer.ORIGINAL_SOURCE_SPLITS):
        speaker = str(100 + index)
        expected.add(speaker)
        chapter = "1000"
        target = raw / split / speaker / chapter / f"{speaker}-{chapter}-0000.flac"
        target.parent.mkdir(parents=True)
        sf.write(target, np.full(1600, 100, dtype=np.int16), 16000, subtype="PCM_16")
    (raw / "SPEAKERS.TXT").write_text("999 | F | train-clean-100 | unused metadata reader")
    monkeypatch.setattr(
        preparer, "EXPECTED_ORIGINAL_SPEAKERS", dict.fromkeys(preparer.ORIGINAL_SOURCE_SPLITS, 1)
    )
    assert preparer.exclusion_inventory(tmp_path) == expected
    missing = raw / "test-other" / "103" / "1000" / "103-1000-0000.flac"
    missing.unlink()
    with pytest.raises(preparer.PreparationError, match="incomplete_exclusion_inventory"):
        preparer.exclusion_inventory(tmp_path)


def test_new_archive_member_count_limit_is_still_enforced(preparer, tmp_path, monkeypatch):
    source = tmp_path / "source.tar.gz"
    archive_at(
        source,
        [
            ("LibriSpeech/README.TXT", b"readme", tarfile.REGTYPE),
            ("LibriSpeech/LICENSE.TXT", b"license", tarfile.REGTYPE),
        ],
    )
    monkeypatch.setattr(preparer, "FRESH_MAX_ARCHIVE_MEMBERS", 1)
    with pytest.raises(preparer.PreparationError, match="archive_limit"):
        preparer.extract_archive(source, tmp_path / "raw", source_split="train-clean-100")


def test_original_cli_never_downloads_fresh_archive(preparer, tmp_path, monkeypatch):
    expected = list(preparer.ORIGINAL_SOURCE_SPLITS)
    observed = []
    inventory = make_inventory(preparer, tmp_path, speakers=5)
    monkeypatch.setattr(sys, "argv", ["prepare", "--root", str(tmp_path / "out"), "--download"])

    def archive(split, root):
        observed.append(split)
        return root / split, {}

    monkeypatch.setattr(preparer, "download_archive", archive)
    monkeypatch.setattr(preparer, "extract_archive", lambda *_, **__: None)
    monkeypatch.setattr(preparer, "inventory_for", lambda *_: inventory)

    def stop_after_archives(*args, **kwargs):
        raise preparer.PreparationError("selection_stop")

    monkeypatch.setattr(preparer, "plan_split", stop_after_archives)
    with pytest.raises(preparer.PreparationError, match="selection_stop"):
        preparer.main()
    assert observed == expected
