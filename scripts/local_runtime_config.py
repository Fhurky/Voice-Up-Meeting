"""Read single-line Compose dotenv assignments without exposing their values."""

import re


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
