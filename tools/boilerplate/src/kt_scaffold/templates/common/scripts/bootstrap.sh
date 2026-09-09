#!/usr/bin/env sh
set -eu

required="@@GENERATOR_VERSION@@"
if command -v kt-scaffold >/dev/null 2>&1; then
  actual="$(kt-scaffold --version)"
  if [ "$actual" != "$required" ]; then
    echo "kt-scaffold version mismatch: expected $required, found $actual" >&2
    exit 1
  fi
  generator="local kt-scaffold $actual"
else
  generator="global Streamable HTTP MCP (project expects kt-scaffold $required)"
fi

python3 scripts/check-governance-drift.py >/dev/null
python3 scripts/check-dependency-admission.py >/dev/null
docker info >/dev/null
echo "bootstrap ok: $generator, Docker reachable, governance and dependency admission current"
