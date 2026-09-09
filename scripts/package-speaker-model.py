#!/usr/bin/env python3
"""Package already provisioned model files; this command never accesses a network."""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "inference"))

from voiceup_inference.model_bundle import (
    FILES,
    BundleError,
    manifest,
    sha256_file,
    verify_bundle,
)


def package_model(ecapa_source: Path, silero_jit: Path, output: Path) -> None:
    """Validate every source before creating a new output directory; never overwrite."""
    output = output.resolve()
    if output.exists():
        raise ValueError("Output already exists; use --verify or choose a new directory")
    sources = {}
    for relative, expected in FILES.items():
        source = (
            silero_jit if relative.startswith("silero/") else ecapa_source / Path(relative).name
        )
        # SpeechBrain's reference cache renames the upstream .txt to .ckpt.
        if relative.endswith("label_encoder.txt") and not source.exists():
            source = ecapa_source / "label_encoder.ckpt"
        if not source.is_file() or sha256_file(source) != expected:
            raise BundleError(f"Source does not match pinned content: {relative}")
        sources[relative] = source
    output.mkdir(parents=True, exist_ok=False)
    for relative, source in sources.items():
        destination = output / relative
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, destination)
    (output / "manifest.json").write_text(
        json.dumps(manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    verify_bundle(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ecapa-source", type=Path)
    parser.add_argument("--silero-jit", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            verify_bundle(args.output)
        elif args.ecapa_source is None or args.silero_jit is None:
            parser.error("packaging requires --ecapa-source and --silero-jit")
        else:
            package_model(args.ecapa_source, args.silero_jit, args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Model package rejected: {exc}\n")
    print("Pinned ECAPA and Silero model package verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
