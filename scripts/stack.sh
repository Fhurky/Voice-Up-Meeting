#!/usr/bin/env sh
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
base="$root/app/infra/docker-compose.local.yml"
observability="$root/app/infra/docker-compose.observability.yml"
mode_file="$root/outputs/local-runtime-mode.txt"
mode="local"
if [ "${1:-}" = "--mode" ]; then
  [ "$#" -ge 2 ] || { echo "--mode requires local, cpu or spark" >&2; exit 2; }
  mode="$2"
  shift 2
elif [ -f "$mode_file" ]; then
  mode="$(tr -d '\r' < "$mode_file")"
fi
case "$mode" in
  local) ;;
  cpu)
    [ -z "${COMPOSE_PROFILES:-}" ] || { echo "CPU mode requires empty COMPOSE_PROFILES" >&2; exit 2; }
    [ -z "${COMPOSE_PROJECT_NAME:-}" ] || { echo "CPU mode requires empty COMPOSE_PROJECT_NAME" >&2; exit 2; }
    for argument in "$@"; do
      case "$argument" in
        --profile|--profile=*|-f*|--file|--file=*|-p*|--project-name|--project-name=*|--project-directory|--project-directory=*|--workdir|--workdir=*|--env-file|--env-file=*)
          echo "Compose model overrides are disabled in CPU mode" >&2; exit 2 ;;
      esac
    done
    set -- -f "$root/app/infra/docker-compose.cpu.yml" "$@"
    ;;
  spark)
    [ -z "${COMPOSE_PROFILES:-}" ] || { echo "Spark mode requires empty COMPOSE_PROFILES" >&2; exit 2; }
    [ -z "${COMPOSE_PROJECT_NAME:-}" ] || { echo "Spark mode requires empty COMPOSE_PROJECT_NAME" >&2; exit 2; }
    # Compose must not reconstruct a project from runtime containers on config failure.
    COMPOSE_PROJECT_NAME=""
    export COMPOSE_PROJECT_NAME
    activates="false"
    names_inference="false"
    for argument in "$@"; do
      case "$argument" in
        up|start|restart|run|create|build|scale|unpause|watch) activates="true" ;;
        inference|inference=*) names_inference="true" ;;
        --profile|--profile=*) echo "Explicit Compose profiles are disabled in Spark mode" >&2; exit 2 ;;
        -f*|--file|--file=*|-p*|--project-name|--project-name=*|--project-directory|--project-directory=*|--workdir|--workdir=*|--env-file|--env-file=*)
          echo "Compose model overrides are disabled in Spark mode" >&2; exit 2 ;;
      esac
    done
    if [ "$activates" = "true" ] && [ "$names_inference" = "true" ]; then
      echo "Local inference activation is disabled in Spark mode" >&2
      exit 2
    fi
    # Resolve the effective profiles, including dotenv, without printing environment values.
    # This also makes bare start/restart fail closed before any container operation.
    spark_services() {
      if [ -f "$observability" ]; then set -- -f "$observability"; else set --; fi
      timeout --kill-after=3s 15s docker compose --project-directory "$root/app/infra" -p voiceup -f "$base" "$@" \
        -f "$root/app/infra/docker-compose.spark.yml" config --services
    }
    command -v timeout >/dev/null 2>&1 || { echo "Spark mode requires bounded command support (timeout)" >&2; exit 2; }
    services="$(spark_services 2>/dev/null)" || { echo "Spark Compose configuration could not be resolved" >&2; exit 2; }
    [ -n "$services" ] || { echo "Spark Compose configuration has no active services" >&2; exit 2; }
    for service in $services; do
      [ "$service" != "inference" ] || { echo "Local inference is active in effective Spark Compose profiles" >&2; exit 2; }
    done
    set -- -f "$root/app/infra/docker-compose.spark.yml" "$@"
    ;;
  *) echo "runtime mode must be local, cpu or spark" >&2; exit 2 ;;
esac
if [ -f "$observability" ]; then
  set -- docker compose --project-directory "$root/app/infra" -p "voiceup" -f "$base" -f "$observability" "$@"
else
  set -- docker compose --project-directory "$root/app/infra" -p "voiceup" -f "$base" "$@"
fi
exec "$@"
