#!/usr/bin/env sh
set -eu

fail() {
  echo "offline bundle error: $*" >&2
  exit 2
}

bundle_input="${KT_SCAFFOLD_OFFLINE_BUNDLE:-}"
trusted_digest="${KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256:-}"
[ -n "$bundle_input" ] || fail "KT_SCAFFOLD_OFFLINE_BUNDLE is required"
case "$bundle_input" in
  /*) ;;
  *) fail "KT_SCAFFOLD_OFFLINE_BUNDLE must be an absolute path" ;;
esac
printf '%s\n' "$trusted_digest" | grep -Eq '^[0-9a-f]{64}$' ||
  fail "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256 must be the bank admission digest"
[ -d "$bundle_input" ] || fail "offline bundle directory is missing: $bundle_input"
bundle="$(CDPATH= cd -- "$bundle_input" && pwd -P)"
[ "$bundle" = "$bundle_input" ] || fail "offline bundle path must already be canonical"

manifest="$bundle/SHA256SUMS"
matrix="$bundle/BUILD-MATRIX"
[ -f "$manifest" ] || fail "SHA256SUMS is missing"
[ -f "$matrix" ] || fail "BUILD-MATRIX is missing"
for required in \
  "$bundle/npm-cache" \
  "$bundle/wheelhouse/generator" \
  "$bundle/wheelhouse/python-fastapi"
do
  [ -d "$required" ] || fail "required offline dependency context is missing: $required"
done
[ -f "$bundle/runtime-images.tar" ] || fail "runtime-images.tar is missing"

if command -v sha256sum >/dev/null 2>&1; then
  actual_digest="$(sha256sum "$manifest" | awk '{print $1}')"
  checksum_command="sha256sum --check SHA256SUMS"
elif command -v shasum >/dev/null 2>&1; then
  actual_digest="$(shasum -a 256 "$manifest" | awk '{print $1}')"
  checksum_command="shasum -a 256 -c SHA256SUMS"
else
  fail "sha256sum or shasum is required"
fi
[ "$actual_digest" = "$trusted_digest" ] ||
  fail "bundle manifest does not match the bank admission digest"

awk '
  NF != 2 || length($1) != 64 || $1 !~ /^[0-9a-f]+$/ ||
    $2 !~ /^\.\// || $2 ~ /(^|\/)\.\.(\/|$)/ { exit 1 }
  END { if (NR == 0) exit 1 }
' "$manifest" || fail "SHA256SUMS contains an unsafe entry"
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
for sealed in BUILD-MATRIX runtime-images.tar npm-cache/ wheelhouse/generator/ wheelhouse/python-fastapi/
do
  grep -Fq "  ./$sealed" "$manifest" || fail "$sealed is not integrity-sealed"
done
(CDPATH= cd -- "$bundle" && sh -c "$checksum_command" >/dev/null) ||
  fail "offline bundle checksum verification failed"

target_platform="$(sed -n 's/^oci-platform=//p' "$matrix")"
[ -n "$target_platform" ] || fail "BUILD-MATRIX has no oci-platform"
host_os="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$(uname -m)" in
  x86_64|amd64) host_arch="amd64" ;;
  arm64|aarch64) host_arch="arm64" ;;
  *) fail "unsupported host architecture: $(uname -m)" ;;
esac
[ "$target_platform" = "$host_os/$host_arch" ] ||
  fail "bundle platform $target_platform does not match host $host_os/$host_arch"

echo "offline bundle verified: $bundle"
