#!/usr/bin/env sh
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
# The imported generator has an isolated, pinned environment on this Windows workstation.
# Windows console launchers are PE executables and cannot be parsed as POSIX shebang scripts.
if [ -x "$root/tools/boilerplate/.venv/Scripts/python.exe" ]; then
  exec "$root/tools/boilerplate/.venv/Scripts/python.exe" "$root/scripts/render_charts.py" "$@"
fi
scaffold_bin="$(command -v kt-scaffold || true)"
if [ -z "$scaffold_bin" ]; then
  echo "chart policy requires the pinned kt-scaffold CLI on PATH" >&2
  exit 2
fi
python_bin="$(sed -n '1s/^#!//p' "$scaffold_bin")"
if [ ! -x "$python_bin" ]; then
  echo "cannot resolve the pinned kt-scaffold Python interpreter" >&2
  exit 2
fi
exec "$python_bin" "$root/scripts/render_charts.py" "$@"
