#!/usr/bin/env sh
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
base="$root/app/infra/docker-compose.local.yml"
observability="$root/app/infra/docker-compose.observability.yml"
if [ -f "$observability" ]; then
  set -- docker compose --project-directory "$root/app/infra" -p "voiceup" -f "$base" -f "$observability" "$@"
else
  set -- docker compose --project-directory "$root/app/infra" -p "voiceup" -f "$base" "$@"
fi
exec "$@"
