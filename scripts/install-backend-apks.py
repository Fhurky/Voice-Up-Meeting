"""Install only hash-verified, pre-fetched Alpine audio libraries during image build."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def main() -> None:
    lock, package_root, docker_arch = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    packages: list[str] = []
    for line in lock.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        architecture, alpine_arch, spec, expected = line.split()
        if architecture != docker_arch:
            continue
        name, version = spec.split("=", 1)
        path = package_root / alpine_arch / f"{name}-{version}.apk"
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Alpine artifact checksum mismatch: {path.name}")
        packages.append(str(path))
    if not packages:
        raise SystemExit(f"No verified audio packages for {docker_arch}")
    subprocess.run(
        ["apk", "add", "--no-network", "--repositories-file", "/dev/null", *packages],
        check=True,
    )


if __name__ == "__main__":
    main()
