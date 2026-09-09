"""Build-time wheel integrity and Linux target selection; no remote test traffic."""

import hashlib
import importlib.util
from pathlib import Path

import pytest
from packaging.tags import Tag

SCRIPT = Path(__file__).resolve().parents[1] / "provision_wheelhouse.py"
SPEC = importlib.util.spec_from_file_location("provision_wheelhouse", SCRIPT)
PROVISION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROVISION)


def test_lock_requires_fixed_hashes_and_rejects_index_reset(tmp_path):
    lock = tmp_path / "requirements.txt"
    for content in ("torch==2.8.0+cu128\n", "--index-url https://pypi.org/simple\n"):
        lock.write_text(content)
        with pytest.raises(ValueError):
            PROVISION.read_lock(lock)


def test_lock_reads_pins_and_allowlisted_hashes(tmp_path):
    digest = "a" * 64
    lock = tmp_path / "requirements.txt"
    lock.write_text(f"fixture==1.0 \\\n    --hash=sha256:{digest}\n    # via test\n")
    assert PROVISION.read_lock(lock) == {"fixture": ("1.0", {digest})}


def test_tags_allow_linux_cp313_and_abi3_but_not_windows_or_cp314():
    tags = PROVISION.supported_tags()
    assert Tag("cp313", "cp313", "manylinux_2_28_x86_64") in tags
    assert Tag("cp38", "abi3", "manylinux_2_17_x86_64") in tags
    assert Tag("py3", "none", "any") in tags
    assert Tag("cp313", "cp313", "win_amd64") not in tags
    assert Tag("cp314", "cp314", "manylinux_2_28_x86_64") not in tags


def test_download_verifies_real_bytes_and_reuses_verified_cache(tmp_path):
    source = tmp_path / "fixture.whl"
    source.write_bytes(b"wheel integrity fixture")
    output = tmp_path / "output"
    output.mkdir()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert PROVISION.download(source.as_uri(), digest, output) == "fixture.whl"
    assert (output / "fixture.whl").read_bytes() == source.read_bytes()
    assert PROVISION.download(source.as_uri(), digest, output) == "fixture.whl"


def test_wrong_hash_never_publishes_completed_wheel(tmp_path):
    source = tmp_path / "fixture.whl"
    source.write_bytes(b"wrong bytes")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError, match="hash mismatch"):
        PROVISION.download(source.as_uri(), "0" * 64, output)
    assert not (output / "fixture.whl").exists()


@pytest.mark.parametrize(
    ("name", "version"),
    [("torch", "2.8.0+cu128"), ("torchaudio", "2.8.0+cu128"), ("triton", "3.4.0")],
)
def test_torch_exact_url_requires_matching_lock_hash(name, version):
    url, digest = PROVISION.TORCH_WHEELS[name]
    assert url.startswith("https://download.pytorch.org/")
    assert PROVISION.select_wheel(name, version, {digest}, {}) == (url, digest)
    with pytest.raises(ValueError):
        PROVISION.select_wheel(name, version, {"0" * 64}, {})
    with pytest.raises(ValueError):
        PROVISION.select_wheel(name, "untrusted-version", {digest}, {})
