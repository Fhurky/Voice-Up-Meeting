#!/usr/bin/env sh
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
mode="write"
case "${1:-}" in
  --check) exec python3 "$root/scripts/check-governance-drift.py" ;;
  --validate) exec python3 "$root/scripts/check-governance-drift.py" ;;
  "") ;;
  *) echo "usage: scripts/render-clients.sh [--check|--validate]" >&2; exit 2 ;;
esac
if ! command -v kt-scaffold >/dev/null 2>&1; then
  echo "write mode requires local agent reconciliation or the optional local CLI" >&2
  exit 2
fi
exec kt-scaffold render --target-dir "$root" --mode "$mode"
