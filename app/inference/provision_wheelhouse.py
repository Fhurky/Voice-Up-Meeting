#!/usr/bin/env python3
"""Online build-time provisioning of a hash-verified CPython 3.13 Linux wheelhouse.

This tool is not copied into the runtime image. It never installs or imports a
downloaded package. Files persist between attempts, including resumable partials.
"""

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import parse_wheel_filename

TORCH_WHEELS = {
    "torch": (
        "https://download.pytorch.org/whl/cu128/torch-2.8.0%2Bcu128-cp313-cp313-manylinux_2_28_x86_64.whl",
        "3a852369a38dec343d45ecd0bc3660f79b88a23e0c878d18707f7c13bf49538f",
    ),
    "torchaudio": (
        "https://download.pytorch.org/whl/cu128/torchaudio-2.8.0%2Bcu128-cp313-cp313-manylinux_2_28_x86_64.whl",
        "410bb8ea46225efe658e5d27a3802c181a2255913003621a5d25a51aca8018d9",
    ),
    "triton": (
        "https://download.pytorch.org/whl/triton-3.4.0-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
        "0e582bfd8147afd0e17f410b39ee161df933a2aca9f653e1178daae98f87f601",
    ),
}


def read_lock(path: Path) -> dict[str, tuple[str, set[str]]]:
    pins = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s\\;]+)", line)
        if match:
            current = match[1].lower().replace("_", "-")
            if current in pins:
                raise ValueError("Duplicate package in lock")
            pins[current] = (match[2], set())
        elif line.lstrip().startswith("--hash="):
            digest = re.search(r"sha256:([0-9a-f]{64})", line)
            if current is None or digest is None:
                raise ValueError("Invalid lock hash")
            pins[current][1].add(digest[1])
        elif line.strip() and not line.lstrip().startswith("#"):
            raise ValueError("Only pinned requirements and SHA-256 hashes are accepted")
    if not pins or any(not hashes for _, hashes in pins.values()):
        raise ValueError("Every locked package must have hashes")
    return pins


def supported_tags() -> dict:
    platforms = [f"manylinux_2_{minor}_x86_64" for minor in range(36, 4, -1)]
    platforms += [
        "manylinux2014_x86_64",
        "manylinux2010_x86_64",
        "manylinux1_x86_64",
        "linux_x86_64",
    ]
    tags = list(cpython_tags((3, 13), abis=["cp313"], platforms=platforms))
    tags += list(compatible_tags((3, 13), interpreter="cp313", platforms=platforms))
    return {tag: index for index, tag in enumerate(tags)}


def select_wheel(name: str, version: str, hashes: set[str], tags: dict) -> tuple[str, str]:
    if name in TORCH_WHEELS:
        url, digest = TORCH_WHEELS[name]
        expected_version = "3.4.0" if name == "triton" else "2.8.0+cu128"
        if digest not in hashes or version != expected_version:
            raise ValueError("Torch wheel does not match the admitted lock")
        return url, digest
    with urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=60) as response:
        metadata = json.load(response)
    candidates = []
    for artifact in metadata["urls"]:
        filename = artifact["filename"]
        digest = artifact["digests"]["sha256"]
        if artifact["packagetype"] != "bdist_wheel" or digest not in hashes:
            continue
        if Path(filename).name != filename:
            raise ValueError("Invalid package filename")
        _, _, _, wheel_tags = parse_wheel_filename(filename)
        ranks = [tags[tag] for tag in wheel_tags if tag in tags]
        if ranks:
            candidates.append((min(ranks), artifact["url"], digest))
    if not candidates:
        raise ValueError(f"No locked CPython 3.13 Linux wheel for {name}=={version}")
    _, url, digest = min(candidates)
    return url, digest


def file_hash(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def download(url: str, digest: str, destination: Path) -> str:
    filename = unquote(url.rsplit("/", 1)[1])
    if Path(filename).name != filename or not filename.endswith(".whl"):
        raise ValueError("Invalid wheel URL")
    target = destination / filename
    if target.exists():
        if file_hash(target) != digest:
            raise ValueError(f"Existing wheel hash mismatch: {filename}")
        return filename
    partial = target.with_suffix(".whl.partial")
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with urlopen(Request(url, headers=headers), timeout=120) as source:
                resumed = offset and source.status == 206
                if resumed and not source.headers.get("Content-Range", "").startswith(
                    f"bytes {offset}-"
                ):
                    raise ValueError("Invalid resumed response")
                with partial.open("ab" if resumed else "wb") as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
            if file_hash(partial) != digest:
                raise ValueError(f"Downloaded wheel hash mismatch: {filename}")
            partial.replace(target)
            return filename
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
    raise RuntimeError("Download attempts exhausted")


def provision(lock: Path, destination: Path, workers: int = 8) -> None:
    pins = read_lock(lock)
    tags = supported_tags()
    destination.mkdir(parents=True, exist_ok=True)

    def provision_one(item):
        name, (version, hashes) = item
        url, digest = select_wheel(name, version, hashes, tags)
        filename = download(url, digest, destination)
        print(f"Verified {filename}", flush=True)
        return {
            "name": name,
            "version": version,
            "filename": filename,
            "sha256": digest,
            "url": url,
        }

    artifacts = []
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(provision_one, item) for item in pins.items()]
        for future in as_completed(futures):
            try:
                artifacts.append(future.result())
            except Exception as exc:
                print(f"Failed: {exc}", flush=True)
                failures.append(str(exc))
    if failures:
        raise RuntimeError("; ".join(failures))
    (destination / "wheelhouse-manifest.json").write_text(
        json.dumps(
            {
                "target": "cp313-linux-x86_64-bookworm",
                "requirements_sha256": file_hash(lock),
                "artifacts": sorted(artifacts, key=lambda artifact: artifact["name"]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path(__file__).with_name("requirements.txt"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=range(1, 17), default=8)
    args = parser.parse_args()
    provision(args.lock, args.destination, args.workers)
