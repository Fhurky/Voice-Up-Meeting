#!/usr/bin/env sh
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
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
