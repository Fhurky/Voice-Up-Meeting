"""Collect bounded read-only Spark facts using only the Python standard library."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import platform
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

TIMEOUT_SECONDS = 8
MAX_OUTPUT_BYTES = 32768
DOCKER = ["docker", "--host", "unix:///var/run/docker.sock"]


def run_command(argv, *, timeout=TIMEOUT_SECONDS, max_bytes=MAX_OUTPUT_BYTES):
    """Drain bounded streams and terminate only this inspection subprocess on limits."""
    result = {"status": "command_failed", "return_code": None, "stdout": ""}
    try:
        process = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        return {**result, "status": "missing_tool"}
    except PermissionError:
        return {**result, "status": "permission_denied"}
    except OSError:
        return result
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    overflow = threading.Event()

    def drain(stream, label):
        try:
            while chunk := stream.read(4096):
                remaining = max_bytes - len(buffers[label])
                buffers[label].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    process.kill()
                    break
        except (OSError, ValueError):
            pass

    readers = [
        threading.Thread(target=drain, args=(stream, name), daemon=True)
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr"))
    ]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait(timeout=2)
    for reader in readers:
        reader.join(timeout=1)
    # Do not wait on a pipe inherited by an unexpected child process.
    for stream, reader in zip((process.stdout, process.stderr), readers):
        if not reader.is_alive():
            stream.close()
    error = buffers["stderr"].decode("utf-8", errors="replace").lower()
    status = "ok" if process.returncode == 0 else "command_failed"
    if any(
        term in error for term in ("permission denied", "access denied", "operation not permitted")
    ):
        status = "permission_denied"
    if timed_out:
        status = "timeout"
    if overflow.is_set():
        status = "output_limit"
    return {
        "status": status,
        "return_code": process.returncode,
        "stdout": buffers["stdout"].decode("utf-8", errors="replace"),
    }


def read_file(path, limit=262144):
    try:
        with open(path, "rb") as source:
            content = source.read(limit + 1)
        if len(content) > limit:
            return {"status": "output_limit"}
        return {"status": "ok", "text": content.decode("utf-8", errors="replace")}
    except FileNotFoundError:
        return {"status": "missing_file"}
    except PermissionError:
        return {"status": "permission_denied"}
    except OSError:
        return {"status": "read_failed"}


def interface_kind(name):
    if not isinstance(name, str) or name in {"", ".", ".."} or "/" in name or "\\" in name:
        return "unknown"
    root = Path("/sys/class/net") / name
    if (root / "wireless").exists() or (root / "phy80211").exists():
        return "wifi"
    kind = read_file(root / "type", limit=64)
    if (root / "device").exists() and kind.get("text", "").strip() == "1":
        return "ethernet"
    return "virtual_or_unknown"


def _probe(argv, parse):
    response = run_command(argv)
    result = {key: response[key] for key in ("status", "return_code")}
    if response["status"] != "ok":
        return result
    try:
        return {**result, **parse(response["stdout"])}
    except (ValueError, TypeError, KeyError, AttributeError, csv.Error):
        return {**result, "status": "invalid_output"}


def _gpu(text):
    items = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 3 or any(not value.strip() for value in row):
            raise ValueError("unexpected GPU query shape")
        items.append(
            dict(zip(("name", "driver_version", "compute_capability"), map(str.strip, row)))
        )
    return {"items": items}


def _docker(text):
    data = json.loads(text)
    selected = {
        key: data[key] for key in ("server_version", "architecture", "os_type", "default_runtime")
    }
    if not all(isinstance(value, str) for value in selected.values()):
        raise ValueError("unexpected Docker query shape")
    runtimes = data["runtime_names"]
    if not isinstance(runtimes, list) or any(
        value is not None and not isinstance(value, str) for value in runtimes
    ):
        raise ValueError("unexpected runtimes")
    return {**selected, "runtime_names": [value for value in runtimes if value is not None]}


def _images(text):
    items = []
    for line in text.splitlines():
        data = json.loads(line)
        if data.get("repository") != "nvcr.io/nvidia/pytorch":
            continue
        selected = {key: data[key] for key in ("repository", "tag", "id", "digest")}
        if not all(isinstance(value, str) for value in selected.values()):
            raise ValueError("unexpected image shape")
        items.append(selected)
    return {"items": items}


def _interfaces(text):
    rows = json.loads(text)
    if not isinstance(rows, list):
        raise TypeError("unexpected interface query shape")
    items = []
    for row in rows:
        name = row["ifname"]
        addresses = [
            {
                key: address[key]
                for key in ("family", "local", "prefixlen", "scope")
                if key in address
            }
            for address in row.get("addr_info", [])
        ]
        items.append(
            {
                "name": name,
                "state": row.get("operstate"),
                "kind": interface_kind(name),
                "link_type": row.get("link_type"),
                "addresses": addresses,
            }
        )
    return {"items": items}


def _routes(text):
    rows = json.loads(text)
    if not isinstance(rows, list):
        raise TypeError("unexpected route query shape")
    fields = ("dst", "gateway", "dev", "prefsrc", "metric", "protocol", "scope", "type", "table")
    return {"items": [{key: row[key] for key in fields if key in row} for row in rows]}


def _disk(path):
    try:
        value = shutil.disk_usage(path)
        return {
            "status": "ok",
            "total_bytes": value.total,
            "used_bytes": value.used,
            "free_bytes": value.free,
        }
    except PermissionError:
        return {"status": "permission_denied"}
    except OSError:
        return {"status": "read_failed"}


def collect():
    os_data = read_file("/etc/os-release")
    cpu_data = read_file("/proc/cpuinfo")
    memory_data = read_file("/proc/meminfo")
    system = {
        "status": "ok" if os_data["status"] == cpu_data["status"] == "ok" else "partial",
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "os": platform.system(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "logical_cpu_count": os.cpu_count(),
        "os_release_status": os_data["status"],
        "cpuinfo_status": cpu_data["status"],
    }
    for line in os_data.get("text", "").splitlines():
        key, _, value = line.partition("=")
        if key in {"ID", "VERSION_ID", "PRETTY_NAME"}:
            system[key.lower()] = value.strip().strip('"')[:256]
    for line in cpu_data.get("text", "").splitlines():
        key, _, value = line.partition(":")
        if key.strip() in {"model name", "Hardware"}:
            system["cpu_model"] = value.strip()[:256]
            break
    memory = {"status": memory_data["status"]}
    if memory_data["status"] == "ok":
        try:
            values = {}
            for line in memory_data["text"].splitlines():
                key, _, value = line.partition(":")
                if key in {"MemTotal", "MemAvailable"}:
                    count, unit = value.split()
                    if unit != "kB" or not count.isdigit():
                        raise ValueError("invalid memory unit")
                    values[key] = int(count) * 1024
            memory.update(total_bytes=values["MemTotal"], available_bytes=values["MemAvailable"])
        except (ValueError, KeyError):
            memory = {"status": "invalid_output"}
    docker_format = '{"server_version":{{json .ServerVersion}},"architecture":{{json .Architecture}},"os_type":{{json .OSType}},"default_runtime":{{json .DefaultRuntime}},"runtime_names":[{{range $name, $value := .Runtimes}}{{json $name}},{{end}}null]}'
    image_format = '{"repository":{{json .Repository}},"tag":{{json .Tag}},"id":{{json .ID}},"digest":{{json .Digest}}}'
    report = {
        "schema_version": 1,
        "collected_at_utc": datetime.now(UTC).isoformat(),
        "read_only": True,
        "model_executed": False,
        "status": "complete",
        "limits": {
            "command_timeout_seconds": TIMEOUT_SECONDS,
            "output_bytes_per_stream": MAX_OUTPUT_BYTES,
        },
        "system": system,
        "memory": memory,
        "disk": {"root": _disk("/"), "working_directory": _disk(".")},
        "gpu": _probe(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            _gpu,
        ),
        "docker": _probe(DOCKER + ["info", "--format", docker_format], _docker),
        "pytorch_images": _probe(
            DOCKER
            + [
                "image",
                "ls",
                "--no-trunc",
                "--digests",
                "--filter",
                "reference=nvcr.io/nvidia/pytorch:*",
                "--format",
                image_format,
            ],
            _images,
        ),
        "network": {
            "interfaces": _probe(["ip", "-j", "address", "show"], _interfaces),
            "ipv4_routes": _probe(["ip", "-j", "-4", "route", "show", "table", "all"], _routes),
            "ipv6_routes": _probe(["ip", "-j", "-6", "route", "show", "table", "all"], _routes),
        },
        "notes": [
            "This is a host inventory, not proof of CUDA execution or ARM64 model compatibility.",
            "System memory is reported once; GPU memory is not added to it.",
            "Docker queries target only unix:///var/run/docker.sock, not a remote context; rootless daemons may require separate discovery.",
            "No environment, SSH material, container list, or unrelated image inventory is collected.",
        ],
    }
    checks = [
        system,
        memory,
        report["gpu"],
        report["docker"],
        report["pytorch_images"],
        *report["disk"].values(),
        *report["network"].values(),
    ]
    if any(item["status"] != "ok" for item in checks):
        report["status"] = "partial"
    return report


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(collect(), ensure_ascii=True, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
