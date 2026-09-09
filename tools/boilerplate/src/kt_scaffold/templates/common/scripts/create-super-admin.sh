#!/usr/bin/env sh
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
username="${@@ENV_PREFIX@@SUPER_ADMIN_USER:-}"
password="${@@ENV_PREFIX@@SUPER_ADMIN_PASS:-}"

if [ -z "$username" ]; then
  printf "Super-admin username: "
  IFS= read -r username
fi
if [ -z "$password" ]; then
  printf "Super-admin password: "
  trap 'stty echo 2>/dev/null || true' EXIT HUP INT TERM
  stty -echo
  IFS= read -r password
  stty echo
  trap - EXIT HUP INT TERM
  printf "\n"
fi
if [ "${#password}" -lt 12 ]; then
  echo "password must contain at least 12 characters" >&2
  exit 2
fi

printf '%s\n' "$password" | "$root/scripts/stack.sh" exec -T \
  -e @@ENV_PREFIX@@BOOTSTRAP_SUPER_ADMIN_USERNAME="$username" \
  backend python -m app.scripts.create_super_admin --password-stdin
