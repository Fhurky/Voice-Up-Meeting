"""Verify the complete, immutable local model package before importing model code."""

import hashlib
import json
from pathlib import Path

MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
MODEL_REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"
DIMENSIONS = 192
SILERO_VERSION = "6.2.1"

# ECAPA hashes match the pinned upstream revision. Silero is the JIT file bundled
# in silero-vad 6.2.1. The packaging command never creates trust from arbitrary input.
FILES = {
    "ecapa/hyperparams.yaml": "6f78854fa04ba59e761437b76a2575d3aba5e5016de3e9b69f0c9a5077fb1a41",
    "ecapa/embedding_model.ckpt": "0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2",
    "ecapa/classifier.ckpt": "fd9e3634fe68bd0a427c95e354c0c677374f62b3f434e45b78599950d860d535",
    "ecapa/mean_var_norm_emb.ckpt": "cd70225b05b37be64fc5a95e24395d804231d43f74b2e1e5a513db7b69b34c33",
    "ecapa/label_encoder.txt": "e13c3a167bb4112685670ee896d20e2b565af16b3a4ceeaa8689fa4d22adb8b9",
    "silero/silero_vad.jit": "e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720",
}


class BundleError(ValueError):
    """A missing or changed model is never downloaded or silently replaced."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def manifest() -> dict:
    return {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": DIMENSIONS,
        "silero_version": SILERO_VERSION,
        "files": dict(FILES),
    }


def verify_bundle(directory: Path) -> dict:
    """Verify fixed names/hashes; a supplied manifest cannot admit alternate bytes."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    try:
        if directory.is_symlink() or manifest_path.is_symlink():
            raise BundleError("Model package must contain regular local files")
        if manifest_path.stat().st_size > 16384:
            raise BundleError("Invalid model package manifest")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data != manifest():
            raise BundleError("Model package metadata does not match the pinned model")
        for name, expected in FILES.items():
            path = directory / name
            if path.parent.is_symlink() or path.is_symlink() or not path.is_file():
                raise BundleError("Model package has missing or non-regular files")
            if sha256_file(path) != expected:
                raise BundleError("Model package content hash does not match the pinned model")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BundleError("Model package is missing or unreadable") from exc
    return data
