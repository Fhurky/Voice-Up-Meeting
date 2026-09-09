#!/usr/bin/env sh
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
python3 "$root/scripts/check-dependency-admission.py" --print-inventory
"$root/scripts/stack.sh" exec -T backend sh -lc '
  set -eu
  pip-compile --generate-hashes --output-file=requirements.txt requirements.in
  pip-compile --allow-unsafe --generate-hashes --output-file=requirements-dev.txt requirements-dev.in
'
echo "candidate Python locks regenerated; update dependency-admission.json and run the full gates"
