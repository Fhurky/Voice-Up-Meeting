"""The same governance bytes must verify under Windows and POSIX path ordering."""

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-governance-drift.py"
FIXTURE_FILES = {
    "10-spec-first.md": b"Accepted requirements precede implementation.\n",
    "corpus.schema.json": b'{"type":"object"}\n',
    "README.md": b"Canonical rule corpus.\n",
}
FIXTURE_DIGEST = hashlib.sha256(
    b"10-spec-first.md\0Accepted requirements precede implementation.\n\0"
    b'corpus.schema.json\0{"type":"object"}\n\0'
    b"README.md\0Canonical rule corpus.\n\0"
).hexdigest()


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("check_governance_drift", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def select_native_order(monkeypatch, path_flavor):
    # Only the OS-dependent comparison changes; glob, reads and hashes use real files.
    def less_than(left, right):
        return path_flavor(left.as_posix()) < path_flavor(right.as_posix())

    monkeypatch.setattr(type(Path()), "__lt__", less_than)


@pytest.mark.parametrize("path_flavor", [PureWindowsPath, PurePosixPath])
def test_mixed_case_corpus_has_one_digest(helper, tmp_path, monkeypatch, path_flavor):
    for name, contents in reversed(FIXTURE_FILES.items()):
        (tmp_path / name).write_bytes(contents)
    (tmp_path / "GENERATED.lock").write_text("ignored lock content", encoding="utf-8")
    (tmp_path / "ignored-directory").mkdir()
    monkeypatch.setattr(helper, "RULES", tmp_path)
    select_native_order(monkeypatch, path_flavor)

    assert helper.digest_corpus() == FIXTURE_DIGEST


@pytest.mark.parametrize("path_flavor", [PureWindowsPath, PurePosixPath])
def test_committed_governance_lock_verifies_unchanged(helper, monkeypatch, path_flavor):
    before = helper.LOCK.read_bytes()
    select_native_order(monkeypatch, path_flavor)

    assert helper.main() == 0
    assert helper.LOCK.read_bytes() == before


@pytest.mark.parametrize("changed_file", ["README.md", "corpus.schema.json"])
def test_changed_rule_content_is_rejected_without_rewriting_lock(
    helper, tmp_path, monkeypatch, changed_file
):
    for name, contents in FIXTURE_FILES.items():
        (tmp_path / name).write_bytes(contents)
    lock = tmp_path / "GENERATED.lock"
    lock.write_text(json.dumps({"corpus_digest": FIXTURE_DIGEST}), encoding="utf-8")
    original_lock = lock.read_bytes()
    changed = FIXTURE_FILES[changed_file] + b"unexpected edit\n"
    (tmp_path / changed_file).write_bytes(changed)
    monkeypatch.setattr(helper, "RULES", tmp_path)
    monkeypatch.setattr(helper, "LOCK", lock)

    with pytest.raises(SystemExit, match="canonical rule corpus differs"):
        helper.main()

    assert lock.read_bytes() == original_lock
    assert (tmp_path / changed_file).read_bytes() == changed
