"""CPU artifact contracts retain the admitted model stack and offline lock inputs."""

import importlib.util
import json
import re
from pathlib import Path

import pytest
from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
INFERENCE = ROOT / "app" / "inference"
ARCHITECTURES = ("x86_64", "aarch64")


@pytest.fixture
def generator():
    path = ROOT / "scripts" / "prepare-spark-wheelhouse.py"
    spec = importlib.util.spec_from_file_location("cpu_wheelhouse_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def document(architecture):
    path = INFERENCE / f"cpu-{architecture}-wheelhouse-manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("architecture", ARCHITECTURES)
def test_cpu_manifest_retains_baseline_pins_without_cuda_dependencies(architecture):
    baseline = json.loads((INFERENCE / "spark-wheelhouse-manifest.json").read_text())
    expected = {
        row["name"]: row["version"] for row in baseline["artifacts"] if row["name"] != "triton"
    }
    expected["torch"] = "2.8.0+cpu"
    expected["torchaudio"] = "2.8.0+cpu" if architecture == "x86_64" else "2.8.0"
    manifest = document(architecture)
    actual = {row["name"]: row["version"] for row in manifest["artifacts"]}
    assert len(manifest["artifacts"]) == len(actual) == 47
    assert actual == expected
    assert manifest["target"] == f"cp313-linux-{architecture}-bookworm-cpu"
    assert manifest["python_version"] == "3.13.14"
    assert manifest["runtime_profile"] == f"{architecture}-cpu"
    assert not any(name.startswith("nvidia-") or name == "triton" for name in actual)


@pytest.mark.parametrize("architecture", ARCHITECTURES)
def test_cpu_manifest_contains_only_compatible_cp313_linux_wheels(architecture, generator):
    path = INFERENCE / f"cpu-{architecture}-wheelhouse-manifest.json"
    artifacts = generator.read_manifest(path, for_lock=True)
    platforms = [f"manylinux_2_{minor}_{architecture}" for minor in range(36, 16, -1)]
    platforms.append(f"manylinux2014_{architecture}")
    accepted = set(cpython_tags((3, 13), abis=["cp313"], platforms=platforms))
    accepted.update(compatible_tags((3, 13), interpreter="cp313", platforms=platforms))
    for artifact in artifacts:
        name, version, _, tags = parse_wheel_filename(artifact["filename"])
        assert name == artifact["name"]
        assert str(version) == artifact["version"]
        assert tags & accepted, artifact["filename"]


@pytest.mark.parametrize("architecture", ARCHITECTURES)
def test_cpu_direct_authority_matches_manifest_and_retains_existing_public_versions(architecture):
    baseline = json.loads((INFERENCE / "spark-wheelhouse-manifest.json").read_text())
    manifest = document(architecture)
    source = (INFERENCE / f"requirements.cpu-{architecture}.in").read_text()
    direct = dict(re.findall(r"^([a-z][a-z0-9-]*)==([^\s]+)$", source, re.MULTILINE))
    assert len(direct) == 12
    assert direct == manifest["direct_pins"]
    assert {name: version.split("+")[0] for name, version in direct.items()} == {
        name: version.split("+")[0] for name, version in baseline["direct_pins"].items()
    }


@pytest.mark.parametrize("architecture", ARCHITECTURES)
def test_cpu_hash_lock_is_exactly_generated_from_reviewable_artifacts(architecture, generator):
    path = INFERENCE / f"cpu-{architecture}-wheelhouse-manifest.json"
    artifacts = generator.read_manifest(path, for_lock=True)
    expected = generator.lock_bytes(artifacts)
    assert (INFERENCE / f"requirements.cpu-{architecture}.txt").read_bytes() == expected


def test_cpu_image_prepares_pinned_arm_openmp_alias_before_dropping_privileges():
    dockerfile = (INFERENCE / "Dockerfile.cpu").read_text()
    assert "ENV LD_LIBRARY_PATH=/usr/local/lib/voiceup-cpu" in dockerfile
    alias = dockerfile.index("torch.libs/libgomp-947d5fa1.so.1.0.0")
    assert dockerfile.index("--require-hashes") < alias < dockerfile.index("USER 10001:10001")
    assert "dc3231f8fd4cadc46d8659c3b8dd811ae33174749e86807f16f61ead6ee59bfd" in dockerfile
    assert "'libgomp.so.1'" in dockerfile
    assert "mode=0o755" in dockerfile
