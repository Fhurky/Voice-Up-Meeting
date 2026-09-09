#!/usr/bin/env sh
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
e2e_root="$root/e2e"
suite="${1:-auth}"
mode="${KT_SCAFFOLD_E2E_MODE:-offline}"

fail() {
  echo "offline E2E error: $*" >&2
  exit 2
}

case "$suite" in
  ""|[!a-z]*|*[!a-z0-9-]*)
    fail "suite must be a lowercase slug"
    ;;
esac
[ -f "$e2e_root/$suite/run-all.mjs" ] || fail "unknown browser suite: $suite"

verify_browser() {
  browser_root="$1"
  [ -d "$browser_root" ] || fail "Playwright browser directory is missing: $browser_root"
  browser_root="$(CDPATH= cd -- "$browser_root" && pwd -P)"
  chromium_path="$(PLAYWRIGHT_BROWSERS_PATH="$browser_root" node -e '
    const fs = require("node:fs");
    const {chromium} = require("@playwright/test");
    const executable = chromium.executablePath();
    fs.accessSync(executable, fs.constants.X_OK);
    process.stdout.write(executable);
  ')" || fail "the approved Playwright tree has no executable Chromium for this platform"
  [ -x "$chromium_path" ] || fail "Chromium is not executable: $chromium_path"
  chromium_path="$(CDPATH= cd -- "$(dirname -- "$chromium_path")" && pwd -P)/$(basename -- "$chromium_path")"
  case "$chromium_path" in
    "$browser_root"/*) ;;
    *) fail "Playwright resolved Chromium outside the approved browser tree" ;;
  esac
  export PLAYWRIGHT_BROWSERS_PATH="$browser_root"
}

case "$mode" in
  offline)
    bundle_input="${KT_SCAFFOLD_OFFLINE_BUNDLE:-}"
    trusted_manifest_digest="${KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256:-}"
    [ -n "$bundle_input" ] || fail \
      "KT_SCAFFOLD_OFFLINE_BUNDLE must point to an admitted, platform-matched bundle"
    printf '%s\n' "$trusted_manifest_digest" | grep -Eq '^[0-9a-f]{64}$' || fail \
      "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256 must be the bank admission digest of SHA256SUMS"
    [ -d "$bundle_input" ] || fail "offline bundle directory is missing: $bundle_input"
    bundle="$(CDPATH= cd -- "$bundle_input" && pwd -P)"
    manifest="$bundle/SHA256SUMS"
    matrix="$bundle/BUILD-MATRIX"
    npm_cache="$bundle/npm-cache"
    browser_root="$bundle/playwright"

    [ -f "$manifest" ] || fail "offline bundle has no SHA256SUMS manifest"
    [ -f "$matrix" ] || fail "offline bundle has no BUILD-MATRIX record"
    [ -d "$npm_cache" ] || fail "offline bundle has no npm-cache directory"
    [ -d "$browser_root" ] || fail "offline bundle has no Playwright browser directory"

    if command -v sha256sum >/dev/null 2>&1; then
      actual_manifest_digest="$(sha256sum "$manifest" | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then
      actual_manifest_digest="$(shasum -a 256 "$manifest" | awk '{print $1}')"
    else
      fail "sha256sum or shasum is required to verify the admitted bundle"
    fi
    [ "$actual_manifest_digest" = "$trusted_manifest_digest" ] || fail \
      "offline bundle manifest does not match the bank admission digest"

    awk '
      NF != 2 || length($1) != 64 || $1 !~ /^[0-9a-f]+$/ ||
        $2 !~ /^\.\// || $2 ~ /(^|\/)\.\.(\/|$)/ { exit 1 }
      END { if (NR == 0) exit 1 }
    ' "$manifest" || fail "offline bundle SHA256SUMS contains an unsafe entry"
    if find "$bundle" -type l -print -quit | grep -q .; then
      fail "offline bundle must not contain symbolic links"
    fi
    manifest_paths="$(awk '{print $2}' "$manifest" | LC_ALL=C sort)"
    actual_paths="$({
      CDPATH= cd -- "$bundle"
      find . -type f ! -name SHA256SUMS -print | LC_ALL=C sort
    })"
    [ "$actual_paths" = "$manifest_paths" ] ||
      fail "offline bundle contains unsealed or missing files"
    grep -Eq '  \./BUILD-MATRIX$' "$manifest" || fail "BUILD-MATRIX is not integrity-sealed"
    grep -Eq '  \./npm-cache/' "$manifest" || fail "npm cache is not integrity-sealed"
    grep -Eq '  \./playwright/' "$manifest" || fail "Playwright tree is not integrity-sealed"

    if command -v sha256sum >/dev/null 2>&1; then
      (CDPATH= cd -- "$bundle" && sha256sum --check SHA256SUMS >/dev/null) ||
        fail "offline bundle checksum verification failed"
    elif command -v shasum >/dev/null 2>&1; then
      (CDPATH= cd -- "$bundle" && shasum -a 256 -c SHA256SUMS >/dev/null) ||
        fail "offline bundle checksum verification failed"
    fi

    target_platform="$(sed -n 's/^oci-platform=//p' "$matrix")"
    [ -n "$target_platform" ] || fail "BUILD-MATRIX has no oci-platform"
    host_os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    case "$(uname -m)" in
      x86_64|amd64) host_arch="amd64" ;;
      arm64|aarch64) host_arch="arm64" ;;
      *) fail "unsupported host architecture: $(uname -m)" ;;
    esac
    [ "$target_platform" = "$host_os/$host_arch" ] || fail \
      "bundle platform $target_platform does not match host $host_os/$host_arch"

    (
      cd "$e2e_root"
      npm ci --offline --ignore-scripts --no-audit --no-fund --cache "$npm_cache"
      verify_browser "$browser_root"
      npm run "$suite"
    )
    ;;
  private-index)
    registry="${KT_SCAFFOLD_NPM_REGISTRY:-}"
    browser_root="${PLAYWRIGHT_BROWSERS_PATH:-}"
    [ -n "$registry" ] || fail \
      "private-index mode requires KT_SCAFFOLD_NPM_REGISTRY"
    registry_lower="$(printf '%s' "$registry" | tr '[:upper:]' '[:lower:]')"
    case "$registry_lower" in
      *registry.npmjs.org*|*npmjs.com*|*yarnpkg.com*)
        fail "public npm registries are forbidden"
        ;;
    esac
    [ -n "$browser_root" ] || fail \
      "private-index mode requires an approved PLAYWRIGHT_BROWSERS_PATH"
    (
      cd "$e2e_root"
      npm_config_registry="$registry" \
      npm_config_replace_registry_host=always \
        npm ci --ignore-scripts --no-audit --no-fund --registry "$registry"
      verify_browser "$browser_root"
      npm run "$suite"
    )
    ;;
  *)
    fail "KT_SCAFFOLD_E2E_MODE must be offline or private-index"
    ;;
esac
