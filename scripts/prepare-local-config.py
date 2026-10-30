"""Create missing local configuration without overwriting existing values."""

import secrets
import subprocess
from pathlib import Path

from local_runtime_config import (
    CU128_MINIMUM_COMPUTE_CAPABILITY,
    cuda_profile,
    cuda_profile_settings,
    dotenv_values,
)


def detected_compute_capability(runner=subprocess.run) -> float | None:
    """Return the first NVIDIA GPU's compute capability, or None without a working driver."""
    try:
        result = runner(
            ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = result.stdout.split() if result.returncode == 0 else []
    try:
        return float(lines[0]) if lines else None
    except ValueError:
        return None


def prepare_config(path: Path, compute_capability: float | None = None) -> None:
    source = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    configured = dotenv_values(source)
    defaults = {"APP_HTTP_PORT": "8081", "GRAFANA_PORT": "3002"}
    for key in (
        "INFERENCE_INTERNAL_KEY",
        "RUNTIME_DATABASE_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
        "JWT_SECRET",
    ):
        defaults[key] = secrets.token_urlsafe(32)
        minimum_bytes = 1 if key == "GRAFANA_ADMIN_PASSWORD" else 32
        if key in configured and (
            len(configured[key].encode("utf-8")) < minimum_bytes
            or configured[key].startswith(("replace-with-", "development-only-"))
        ):
            raise ValueError(
                f"{key} needs an explicit non-template local value of at least {minimum_bytes} bytes; existing values were not changed"
            )
    for key in ("APP_HTTP_PORT", "GRAFANA_PORT"):
        if key in configured and (
            not configured[key].isdigit() or not 1 <= int(configured[key]) <= 65535
        ):
            raise ValueError(f"Invalid local port: {key}; existing values were not changed")
    if (
        compute_capability is not None
        and compute_capability < CU128_MINIMUM_COMPUTE_CAPABILITY
        and "INFERENCE_RUNTIME_PROFILE" not in configured
    ):
        defaults.update(cuda_profile_settings("x86_64-cu126"))
    additions = [f"{key}={value}" for key, value in defaults.items() if key not in configured]
    try:
        cuda_profile({**defaults, **configured})
    except ValueError as exc:
        raise ValueError(f"{exc}; existing values were not changed") from None
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")
    print("Local configuration ready; existing values preserved and secrets not printed")


def main() -> None:
    try:
        prepare_config(
            Path(__file__).resolve().parents[1] / "app/infra/.env",
            detected_compute_capability(),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
