#!/usr/bin/env sh
set -eu

required="0.3.0"
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

# A caller may pin its already-validated interpreter without relying on another PATH Python.
python_bin="${KT_SCAFFOLD_PYTHON:-python3}"
"$python_bin" scripts/check-governance-drift.py >/dev/null
"$python_bin" scripts/check-dependency-admission.py >/dev/null
docker info >/dev/null
echo "bootstrap ok: $generator, Docker reachable, governance and dependency admission current"
