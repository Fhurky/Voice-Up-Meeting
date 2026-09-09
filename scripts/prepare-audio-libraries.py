"""Fetch the reviewed Alpine audio packages for an offline backend image build."""

from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=["amd64", "arm64", "all"], default="amd64")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for line in (root / "app/infra/backend-apk.lock").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        arch, alpine_arch, spec, expected = line.split()
        if args.arch not in {"all", arch}:
            continue
        name, version = spec.split("=", 1)
        filename = f"{name}-{version}.apk"
        target = root / "outputs/backend-apks" / alpine_arch / filename
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        url = f"https://dl-cdn.alpinelinux.org/alpine/v3.23/main/{alpine_arch}/{filename}"
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = response.read(20 * 1024 * 1024 + 1)
        if hashlib.sha256(payload).hexdigest() != expected:
            raise SystemExit(f"Rejected artifact with unexpected checksum: {filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".download")
        temporary.write_bytes(payload)
        temporary.replace(target)
    print(f"Verified Alpine audio library bundle: {args.arch}")


if __name__ == "__main__":
    main()
