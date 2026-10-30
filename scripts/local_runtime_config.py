"""Read single-line Compose dotenv assignments without exposing their values."""

import re

# Local x86_64 CUDA inference builds: lock file under app/inference and its
# repository-relative wheelhouse. Compose receives the wheelhouse as ../../<path>.
CUDA_PROFILES = {
    "x86_64-cu128": {
        "requirements": "requirements.txt",
        "wheelhouse": "models/inference-wheelhouse",
    },
    "x86_64-cu126": {
        "requirements": "requirements.cu126.txt",
        "wheelhouse": "models/inference-wheelhouse-cu126",
    },
}
DEFAULT_CUDA_PROFILE = "x86_64-cu128"
# PyTorch 2.8 CUDA 12.8 wheels omit compute capability 5.0-6.1 (Maxwell/Pascal).
CU128_MINIMUM_COMPUTE_CAPABILITY = 7.0


def cuda_profile_settings(profile: str) -> dict[str, str]:
    selected = CUDA_PROFILES[profile]
    return {
        "INFERENCE_RUNTIME_PROFILE": profile,
        "INFERENCE_REQUIREMENTS": selected["requirements"],
        "INFERENCE_WHEELHOUSE_CONTEXT": "../../" + selected["wheelhouse"],
    }


def cuda_profile(values: dict[str, str]) -> str:
    """Return the configured CUDA profile once its lock and wheelhouse agree with it."""
    profile = values.get("INFERENCE_RUNTIME_PROFILE", DEFAULT_CUDA_PROFILE)
    if profile not in CUDA_PROFILES:
        raise ValueError(f"Unsupported local CUDA inference profile: {profile}")
    defaults = cuda_profile_settings(DEFAULT_CUDA_PROFILE)
    for key, expected in cuda_profile_settings(profile).items():
        if values.get(key, defaults[key]) != expected:
            raise ValueError(f"{key} does not match INFERENCE_RUNTIME_PROFILE={profile}")
    return profile


def dotenv_values(source: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in source.lstrip("\ufeff").splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if match is None:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key in values:
            raise ValueError(f"Duplicate local configuration key: {key}")
        if value.startswith(("'", '"')):
            quote = value[0]
            end = value.find(quote, 1)
            if end == -1 or (
                value[end + 1 :].strip() and not value[end + 1 :].strip().startswith("#")
            ):
                raise ValueError(f"Invalid single-line local configuration value: {key}")
            value = value[1:end]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        values[key] = value
    return values
