#!/usr/bin/env sh
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
default_root="$(CDPATH= cd -- "$script_dir/.." && pwd)"
root="${KT_SECURITY_ROOT:-$default_root}"
ledger="${KT_DEPENDENCY_ADMISSION_LEDGER:-$root/dependency-admission.json}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required offline security tool is unavailable: $1" >&2
    exit 2
  }
}

require_command python3
require_command gitleaks
require_command semgrep
require_command trivy
require_command sha256sum

: "${INTERNAL_SCANNER_MATERIAL_DIR:?set INTERNAL_SCANNER_MATERIAL_DIR to the admitted scanner snapshot}"
: "${INTERNAL_SCANNER_SHA256SUMS:?set INTERNAL_SCANNER_SHA256SUMS to its SHA256SUMS file}"
: "${INTERNAL_SCANNER_SHA256SUMS_SHA256:?set the out-of-band bank admission digest}"
: "${INTERNAL_SCANNER_ADMITTED_ON:?set the bank admission date in YYYY-MM-DD form}"
: "${INTERNAL_SEMGREP_RULESET:?set INTERNAL_SEMGREP_RULESET to the admitted offline ruleset}"
: "${TRIVY_CACHE_DIR:?set TRIVY_CACHE_DIR to the admitted offline Trivy cache}"
max_age_days="${INTERNAL_SCANNER_MAX_AGE_DAYS:-7}"

scanner_root="$(CDPATH= cd -- "$INTERNAL_SCANNER_MATERIAL_DIR" && pwd -P)"
sums="$(CDPATH= cd -- "$(dirname -- "$INTERNAL_SCANNER_SHA256SUMS")" && pwd -P)/$(basename -- "$INTERNAL_SCANNER_SHA256SUMS")"
ruleset="$(CDPATH= cd -- "$(dirname -- "$INTERNAL_SEMGREP_RULESET")" && pwd -P)/$(basename -- "$INTERNAL_SEMGREP_RULESET")"
trivy_cache="$(CDPATH= cd -- "$TRIVY_CACHE_DIR" && pwd -P)"
case "$sums" in "$scanner_root"/*) ;; *) echo "scanner checksum manifest escapes admitted snapshot" >&2; exit 2 ;; esac
case "$ruleset" in "$scanner_root"/*) ;; *) echo "Semgrep ruleset escapes admitted snapshot" >&2; exit 2 ;; esac
case "$trivy_cache" in "$scanner_root"/*|"$scanner_root") ;; *) echo "Trivy cache escapes admitted snapshot" >&2; exit 2 ;; esac
[ -f "$sums" ] && [ ! -L "$sums" ] || { echo "scanner checksum manifest must be a regular file" >&2; exit 2; }
[ -f "$ruleset" ] && [ ! -L "$ruleset" ] || { echo "Semgrep ruleset must be a regular file" >&2; exit 2; }
[ -d "$trivy_cache" ] && [ ! -L "$trivy_cache" ] || { echo "Trivy cache must be a directory" >&2; exit 2; }
if find "$scanner_root" -type l -print -quit | grep -q .; then
  echo "scanner snapshot must not contain symbolic links" >&2
  exit 2
fi

sums_relative="${sums#"$scanner_root"/}"
awk '
  NF != 2 || length($1) != 64 || $1 !~ /^[0-9a-f]+$/ ||
    $2 ~ /^\// || $2 ~ /(^|\/)\.\.(\/|$)/ { exit 1 }
  END { if (NR == 0) exit 1 }
' "$sums" || { echo "scanner SHA256SUMS contains an unsafe entry" >&2; exit 2; }
manifest_paths="$(awk '{ path=$2; sub(/^\.\//, "", path); print path }' "$sums" | LC_ALL=C sort)"
actual_paths="$({
  CDPATH= cd -- "$scanner_root"
  find . -type f ! -path "./$sums_relative" -print \
    | sed 's#^\./##' \
    | LC_ALL=C sort
})"
if [ "$actual_paths" != "$manifest_paths" ]; then
  echo "scanner snapshot contains unsealed or missing files" >&2
  exit 1
fi

if ! printf '%s\n' "$INTERNAL_SCANNER_SHA256SUMS_SHA256" | grep -Eq '^[0-9a-f]{64}$'; then
  echo "scanner admission digest must be 64 lowercase hexadecimal characters" >&2
  exit 2
fi
actual_sums_sha256="$(sha256sum "$sums" | awk '{print $1}')"
if [ "$actual_sums_sha256" != "$INTERNAL_SCANNER_SHA256SUMS_SHA256" ]; then
  echo "scanner checksum manifest does not match the out-of-band bank admission digest" >&2
  exit 1
fi
python3 - "$INTERNAL_SCANNER_ADMITTED_ON" "$max_age_days" <<'PY'
from datetime import date
import sys

try:
    admitted = date.fromisoformat(sys.argv[1])
    maximum = int(sys.argv[2])
except (ValueError, IndexError) as exc:
    raise SystemExit(f"invalid scanner admission age evidence: {exc}")
age = (date.today() - admitted).days
if maximum < 0 or age < 0 or age > maximum:
    raise SystemExit(f"scanner snapshot age {age} days is outside admitted maximum {maximum}")
PY
(cd "$scanner_root" && sha256sum --check "$sums_relative")
python3 "$script_dir/check-dependency-admission.py" --root "$root" --ledger "$ledger"

echo "scanner versions: $(gitleaks version); $(semgrep --version); $(trivy --version | head -n 1)"
gitleaks dir --config "$root/.gitleaks.toml" --redact --exit-code 1 "$root"
SEMGREP_ENABLE_VERSION_CHECK=0 SEMGREP_SEND_METRICS=off \
  semgrep scan --config "$ruleset" --error "$root"
migration_chart="$root/app/devops/charts/app-migrate"
migration_values="$migration_chart/values.yaml"
if [ -f "$migration_values" ]; then
  TRIVY_NO_PROGRESS=true TRIVY_SKIP_DB_UPDATE=true TRIVY_SKIP_JAVA_DB_UPDATE=true \
    trivy fs --offline-scan --include-dev-deps --scanners vuln,misconfig,secret \
      --skip-dirs "$migration_chart" --exit-code 1 --severity HIGH,CRITICAL "$root"
  TRIVY_NO_PROGRESS=true \
    trivy config --skip-check-update --helm-values "$migration_values" \
      --helm-set-string revision=1111111111111111111111111111111111111111 \
      --exit-code 1 --severity HIGH,CRITICAL "$migration_chart"
else
  TRIVY_NO_PROGRESS=true TRIVY_SKIP_DB_UPDATE=true TRIVY_SKIP_JAVA_DB_UPDATE=true \
    trivy fs --offline-scan --include-dev-deps --scanners vuln,misconfig,secret \
      --exit-code 1 --severity HIGH,CRITICAL "$root"
fi
