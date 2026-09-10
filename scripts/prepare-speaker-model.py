#!/usr/bin/env python3
"""Acquire the pinned public model at build time; runtime never downloads models."""

from __future__ import annotations

import hashlib
import os
import runpy
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
MODEL_BUNDLE = runpy.run_path(str(ROOT / "app/inference/voiceup_inference/model_bundle.py"))
FILES = MODEL_BUNDLE["FILES"]
MODEL_ID = MODEL_BUNDLE["MODEL_ID"]
MODEL_REVISION = MODEL_BUNDLE["MODEL_REVISION"]
verify_bundle = MODEL_BUNDLE["verify_bundle"]

WHEELHOUSE = runpy.run_path(str(ROOT / "scripts/prepare-spark-wheelhouse.py"))
PACKAGE = runpy.run_path(str(ROOT / "scripts/package-speaker-model.py"))
MAX_MODEL_BYTES = 1024 * 1024 * 1024
MODEL_HOSTS = frozenset(
    {
        "huggingface.co",
        "cdn-lfs.huggingface.co",
        "cdn-lfs-us-1.huggingface.co",
        "cdn-lfs-eu-1.huggingface.co",
        "cas-bridge.xethub.hf.co",
        "us.aws.cdn.hf.co",
        "us.gcp.cdn.hf.co",
        "cdn-lfs-us-1.hf.co",
        "cdn-lfs-eu-1.hf.co",
    }
)


def validate_model_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in MODEL_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or any(ord(char) <= 32 for char in url)
        ):
            raise ValueError
    except ValueError:
        raise ValueError("untrusted_model_url") from None


class ModelRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_model_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_model(url: str, target: Path, expected: str, *, opener=None) -> None:
    validate_model_url(url)
    target = WHEELHOUSE["checked_path"](target)
    if target.exists():
        if not target.is_file() or target.stat().st_size > MAX_MODEL_BYTES:
            raise ValueError("existing_model_hash_mismatch")
        with target.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError("existing_model_hash_mismatch")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    opener = opener or build_opener(ModelRedirects())
    descriptor, temporary_name = tempfile.mkstemp(suffix=".partial", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, opener.open(url, timeout=60) as response:
            digest, size = hashlib.sha256(), 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_MODEL_BYTES:
                    raise ValueError("model_download_too_large")
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("downloaded_model_hash_mismatch")
        # A hard link publishes complete bytes atomically and refuses an existing
        # destination, including another concurrent preparer's completed file.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def publish_model_bytes(target: Path, payload: bytes, expected: str) -> None:
    if len(payload) > MAX_MODEL_BYTES or hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("model_hash_mismatch")
    target = WHEELHOUSE["checked_path"](target)
    if WHEELHOUSE["verify_existing"](
        target, len(payload), expected, "existing_model_hash_mismatch"
    ):
        return
    descriptor, temporary_name = tempfile.mkstemp(suffix=".partial", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        WHEELHOUSE["publish"](
            temporary, target, len(payload), expected, "existing_model_hash_mismatch"
        )
    finally:
        temporary.unlink(missing_ok=True)


def prepare(root: Path = ROOT) -> None:
    output = WHEELHOUSE["checked_path"](root / "models/speaker-pilot")
    if output.exists():
        verify_bundle(output)
        print("Pinned local model package verified; no download needed")
        return
    source = WHEELHOUSE["directory_path"](root / "models/model-sources")
    for relative, digest in FILES.items():
        if relative.startswith("ecapa/"):
            filename = Path(relative).name
            print(f"Preparing pinned model file: {filename}", flush=True)
            fetch_model(
                f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{filename}",
                source / relative,
                digest,
            )
    # Silero's platform-independent wheel contains the exact admitted JIT file.
    artifacts = WHEELHOUSE["read_manifest"](
        root / "app/inference/cpu-x86_64-wheelhouse-manifest.json"
    )
    artifact = next(item for item in artifacts if item["name"] == "silero-vad")
    wheel_directory = WHEELHOUSE["directory_path"](source / "wheels")
    WHEELHOUSE["download_artifact"](artifact, wheel_directory)
    jit = WHEELHOUSE["checked_path"](source / "silero_vad.jit")
    with zipfile.ZipFile(wheel_directory / artifact["filename"]) as archive:
        entry = archive.getinfo("silero_vad/data/silero_vad.jit")
        if entry.file_size > MAX_MODEL_BYTES:
            raise ValueError("model_download_too_large")
        payload = archive.read(entry)
    if hashlib.sha256(payload).hexdigest() != FILES["silero/silero_vad.jit"]:
        raise ValueError("silero_model_hash_mismatch")
    publish_model_bytes(jit, payload, FILES["silero/silero_vad.jit"])
    with tempfile.TemporaryDirectory(prefix=".speaker-package-", dir=source) as temporary:
        staged = Path(temporary) / "bundle"
        PACKAGE["package_model"](source / "ecapa", jit, staged)
        if output.exists():
            raise ValueError("model_output_already_exists")
        staged.rename(output)
    print("Pinned ECAPA and Silero package ready for offline use")


if __name__ == "__main__":
    try:
        prepare()
    except (ValueError, OSError, KeyError, zipfile.BadZipFile):
        # Download errors may contain signed redirect URLs; never echo them.
        raise SystemExit(
            "Model preparation failed: check connectivity, free space and pinned local files; existing files were preserved"
        ) from None
