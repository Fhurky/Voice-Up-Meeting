#!/usr/bin/env sh
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
answers="$root/.kt-scaffold/answers.yml"
profile="$(sed -n 's/^backend_profile: //p' "$answers")"
schema_profile="$(sed -n 's/^backend_profile: //p' "$root/schema/profile.yml")"
env_prefix="$(sed -n 's/^env_prefix: //p' "$answers")"
database_env="${env_prefix}DATABASE_URL"
database_override="${KT_SCAFFOLD_DATABASE_URL_OVERRIDE:-}"
action="${1:-status}"
name="${2:-change}"

if [ "$profile" != "$schema_profile" ]; then
  echo "answers and schema profile disagree" >&2
  exit 2
fi
if ! printf '%s\n' "$env_prefix" | grep -Eq '^[A-Z][A-Z0-9_]*_$'; then
  echo "unsafe environment prefix in answers" >&2
  exit 2
fi
if [ -n "$database_override" ]; then
  override_database="$(printf '%s' "$database_override" | sed 's/[?].*$//' | sed 's#^.*/##')"
  case "$override_database" in
    *_test) ;;
    *) echo "database override must target a disposable database ending in _test" >&2; exit 2 ;;
  esac
fi

stack_backend() {
  if [ -n "$database_override" ]; then
    "$root/scripts/stack.sh" exec -T \
      -e "$database_env=$database_override" \
      backend "$@"
  else
    "$root/scripts/stack.sh" exec -T backend "$@"
  fi
}

case "$action" in
  generate)
    stack_backend alembic revision --autogenerate -m "$name"
    ;;
  apply)
    stack_backend alembic upgrade head
    ;;
  status)
    stack_backend alembic current
    ;;
  validate)
    stack_backend sh -lc 'alembic check && alembic heads && alembic current --check-heads'
    ;;
  *)
    echo "unsupported database action: $action" >&2
    exit 2
    ;;
esac
