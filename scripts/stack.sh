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
# Only upstream restarts need fresh DNS resolution in the existing proxy workers.
# Parse the restart command before adding the selected Compose overlay arguments.
restarts_upstream() {
  [ "${1:-}" = restart ] || return 1
  shift
  has_services=false
  has_upstream=false
  options=true
  while [ "$#" -gt 0 ]; do
    if [ "$options" = true ]; then
      case "$1" in
        --help|-h) return 1 ;;
        --timeout|-t) [ "$#" -ge 2 ] || return 1; shift 2; continue ;;
        --timeout=*|-t[0-9]*|--no-deps) shift; continue ;;
        --) options=false; shift; continue ;;
        -*) return 1 ;;
      esac
    fi
    has_services=true
    case "$1" in backend|frontend) has_upstream=true ;; esac
    shift
  done
  [ "$has_services" = false ] || [ "$has_upstream" = true ]
}
reload_upstream=false
if restarts_upstream "$@"; then reload_upstream=true; fi
case "$mode" in
  local)
    meeting_file="$root/outputs/local-meeting-enabled.txt"
    if [ -f "$meeting_file" ]; then
      [ "$(tr -d '\r\n' < "$meeting_file")" = "enabled" ] || { echo "Invalid local meeting selection" >&2; exit 2; }
      [ -f "$root/app/infra/docker-compose.meeting.yml" ] || { echo "Local meeting overlay is missing" >&2; exit 2; }
      set -- -f "$root/app/infra/docker-compose.meeting.yml" "$@"
    fi
    ;;
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
if [ "$reload_upstream" = false ]; then exec "$@"; fi
"$@"
# Reuse the same mode's wrapper so its Compose/profile guards also protect exec.
# Never regenerate Spark's private config or replace its active include chain.
stack_nginx_reload_local='set -eu; nginx -t; nginx -s reload'
stack_nginx_reload_spark='set -eu; set -- /tmp/voiceup-spark.*/nginx.conf; [ "$#" -eq 1 ]; [ -f "$1" ]; [ ! -L "$1" ]; [ -d "${1%/*}" ]; [ ! -L "${1%/*}" ]; nginx -t -c "$1"; nginx -s reload -c "$1"'
if [ "$mode" = spark ]; then
  reload_command="$stack_nginx_reload_spark"
else
  reload_command="$stack_nginx_reload_local"
fi
exec sh "$root/scripts/stack.sh" --mode "$mode" exec -T nginx sh -c "$reload_command"
