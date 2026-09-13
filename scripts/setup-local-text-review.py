"""Verify an installed loopback Ollama model and configure optional transcript review."""

import argparse
import http.client
import json
import os
from pathlib import Path
import re
import tempfile

from local_runtime_config import dotenv_values


def request_json(method, path, body=None, *, port=11434):
    """Use a bounded fixed-loopback connection with no proxies or redirects."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        payload = json.dumps(body).encode() if body is not None else None
        connection.request(method, path, body=payload, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("text_review_local_ollama_unavailable")
        raw = response.read(1048577)
        if len(raw) > 1048576:
            raise ValueError("text_review_local_ollama_invalid_response")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("text_review_local_ollama_invalid_response")
        return value
    except (OSError, http.client.HTTPException, UnicodeError, json.JSONDecodeError):
        raise ValueError("text_review_local_ollama_unavailable") from None
    finally:
        connection.close()


def model_identity(tags, detail, model):
    items = tags.get("models")
    if not isinstance(items, list):
        raise ValueError("text_review_local_model_unavailable")
    selected = [item for item in items if isinstance(item, dict) and item.get("name") == model]
    if len(selected) != 1:
        raise ValueError("text_review_local_model_unavailable")
    entry = selected[0]
    digest = entry.get("digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("text_review_local_model_invalid_identity")
    if (
        any(value.get(key) for value in (entry, detail) for key in ("remote_host", "remote_model"))
        or "cloud" in model.lower()
    ):
        raise ValueError("text_review_remote_model_forbidden")
    capabilities = detail.get("capabilities")
    if not isinstance(capabilities, list) or "completion" not in capabilities:
        raise ValueError("text_review_local_model_not_completion")
    return digest


def inspect_model(model):
    before = request_json("GET", "/api/tags")
    detail = request_json("POST", "/api/show", {"model": model})
    digest = model_identity(before, detail, model)
    if model_identity(request_json("GET", "/api/tags"), detail, model) != digest:
        raise ValueError("text_review_local_model_changed")
    return digest


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as target:
            target.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(root, *, enabled, model, digest):
    path = root / "app/infra/.env"
    if not path.is_file() or path.is_symlink():
        raise ValueError("text_review_local_configuration_missing")
    source = path.read_bytes().decode("utf-8")
    dotenv_values(source)
    prefix = "\ufeff" if source.startswith("\ufeff") else ""
    source = source.removeprefix("\ufeff")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}", model) is None or "://" in model:
        raise ValueError("text_review_local_model_invalid_name")
    if enabled and re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("text_review_local_model_invalid_identity")
    values = {"TEXT_REVIEW_ENABLED": "true" if enabled else "false"}
    if enabled:
        values.update(
            {
                "TEXT_REVIEW_URL": "http://nginx:9081",
                "TEXT_REVIEW_MODEL": model,
                "TEXT_REVIEW_MODEL_DIGEST": digest,
            }
        )
    newline = "\r\n" if "\r\n" in source else "\n"
    for key, value in values.items():
        pattern = rf"(?m)^[ \t]*(?:export[ \t]+)?{key}[ \t]*=[^\r\n]*"
        replacement = f"{key}={value}"
        if re.search(pattern, source):
            source = re.sub(pattern, replacement, source)
        else:
            source += (
                ("" if source.endswith(("\n", "\r")) or not source else newline)
                + replacement
                + newline
            )
    marker = root / "outputs/local-text-review-enabled.txt"
    if marker.is_symlink():
        raise ValueError("text_review_local_selection_invalid")
    atomic_write(path, prefix + source)
    atomic_write(marker, "enabled\n" if enabled else "disabled\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--check", action="store_true")
    operation.add_argument("--enable", action="store_true")
    operation.add_argument("--disable", action="store_true")
    parser.add_argument("--model", default="qwen3.5:27b")
    arguments = parser.parse_args()
    try:
        if (
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}", arguments.model) is None
            or "://" in arguments.model
        ):
            raise ValueError("text_review_local_model_invalid_name")
        digest = "" if arguments.disable else inspect_model(arguments.model)
        if not arguments.check:
            configure(
                Path(__file__).resolve().parents[1],
                enabled=arguments.enable,
                model=arguments.model,
                digest=digest,
            )
        print(
            json.dumps(
                {
                    "status": "verified" if arguments.check else "configured",
                    "enabled": not arguments.disable,
                    "model": arguments.model,
                    "digest": digest,
                    "restart_required": not arguments.check,
                }
            )
        )
    except (ValueError, OSError):
        raise SystemExit(
            "Local text review setup failed; verify the installed local model and existing configuration. No secrets were printed."
        ) from None


if __name__ == "__main__":
    main()
