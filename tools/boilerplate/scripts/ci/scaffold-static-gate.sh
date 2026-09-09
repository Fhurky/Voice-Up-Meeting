#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: scaffold-static-gate.sh <scaffold-root> <verified-offline-bundle>" >&2
  exit 2
fi

scaffold_root="$(cd -- "$1" && pwd)"
bundle="$(cd -- "$2" && pwd)"
profile="$(sed -n 's/^backend_profile: //p' "$scaffold_root/schema/profile.yml")"
env_prefix="$(sed -n 's/^env_prefix: //p' "$scaffold_root/.kt-scaffold/answers.yml")"
product_name="$(sed -n 's/^product_name: //p' "$scaffold_root/.kt-scaffold/answers.yml")"
work="$(mktemp -d "${RUNNER_TEMP:-/tmp}/kt-scaffold-static.XXXXXX")"
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/npm-logs"
export "${env_prefix}PROJECT_NAME=$product_name"
export "${env_prefix}JWT_SECRET=static-gate-secret-that-is-at-least-32-characters"

set -- "$scaffold_root"/specs/openapi/*-api.yaml
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "expected exactly one rendered OpenAPI contract" >&2
  exit 2
fi
contract="$1"

case "$profile" in
  python-fastapi)
    profile_venv="$work/python-profile"
    python3.13 -m venv "$profile_venv"
    "$profile_venv/bin/python" -m pip install \
      --disable-pip-version-check \
      --no-index \
      --find-links "$bundle/wheelhouse/python-fastapi" \
      --require-hashes \
      -r "$scaffold_root/app/backend/requirements-dev.txt"
    (
      cd "$scaffold_root/app/backend"
      "$profile_venv/bin/ruff" check app tests
      "$profile_venv/bin/black" --check app tests
      "$profile_venv/bin/isort" --check-only app tests
      "$profile_venv/bin/mypy" app
      "$profile_venv/bin/pytest" -q
      "$profile_venv/bin/python" -m app.scripts.export_openapi \
        --output "$work/backend-openapi.json" >/dev/null
    )
    ;;
  *)
    echo "unsupported backend profile: $profile" >&2
    exit 2
    ;;
esac

diff -u "$contract" "$work/backend-openapi.json"

(
  cd "$scaffold_root/app/frontend"
  npm ci --offline --ignore-scripts --no-audit --no-fund \
    --cache "$bundle/npm-cache" --logs-dir "$work/npm-logs"
  npm run lint
  npm run build
  npm test
  cp src/types/api.d.ts "$work/api.d.ts.expected"
  npm run generate-types >/dev/null
  diff -u "$work/api.d.ts.expected" src/types/api.d.ts
)

echo "static scaffold gate passed: $profile"
