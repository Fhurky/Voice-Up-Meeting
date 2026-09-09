#!/usr/bin/env sh
# Build this bundle only in the approved connected artifact factory. Consumers need no network.
set -eu

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
output="${1:-$root/dist/offline-linux-amd64}"
python="${PYTHON:-python3.13}"
pip_platform="${PIP_PLATFORM:-musllinux_1_2_x86_64}"
pip_compat_platform="${PIP_COMPAT_PLATFORM:-musllinux_1_1_x86_64}"
oci_platform="${OCI_PLATFORM:-linux/amd64}"
generator_python="${GENERATOR_PYTHON_VERSION:-313}"
profile_python="${PROFILE_PYTHON_VERSION:-313}"
generator_abi="${GENERATOR_PYTHON_ABI:-cp${generator_python}}"
profile_abi="${PROFILE_PYTHON_ABI:-cp${profile_python}}"
default_generator_lock="$root/packaging/locks/generator-linux-amd64-cp313-musllinux.requirements.lock"
generator_lock_override="${GENERATOR_REQUIREMENTS_LOCK:-}"
build_system_lock="$root/packaging/locks/build-system.requirements.lock"
alpine_runtime_lock="$root/packaging/locks/alpine-runtime-packages.lock"

# The repository admits one generator artifact set by default. A different target remains
# supported, but it must bring a separately reviewed hash lock instead of silently reusing version
# pins for another platform. --require-hashes below makes a mirror substitution at the same version
# fail before the artifact enters the bundle.
if [ -z "$generator_lock_override" ]; then
  if [ "$pip_platform" != "musllinux_1_2_x86_64" ] \
    || [ "$pip_compat_platform" != "musllinux_1_1_x86_64" ] \
    || [ "$oci_platform" != "linux/amd64" ] \
    || [ "$generator_python" != "313" ] \
    || [ "$generator_abi" != "cp313" ]; then
    echo "non-default generator matrix requires GENERATOR_REQUIREMENTS_LOCK" >&2
    echo "create and review a hash lock for that exact OS/architecture/Python tuple" >&2
    exit 2
  fi
  generator_requirements_lock="$default_generator_lock"
else
  generator_requirements_lock="$generator_lock_override"
fi

factory_os="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$(uname -m)" in
  x86_64|amd64) factory_arch="amd64" ;;
  arm64|aarch64) factory_arch="arm64" ;;
  *) echo "unsupported artifact-factory architecture: $(uname -m)" >&2; exit 2 ;;
esac
factory_platform="$factory_os/$factory_arch"
if [ "$factory_platform" != "$oci_platform" ]; then
  echo "artifact factory $factory_platform does not match bundle platform $oci_platform" >&2
  echo "npm optional dependencies, Playwright and OCI images require a native matrix runner" >&2
  exit 2
fi

for lock in "$generator_requirements_lock" "$build_system_lock" "$alpine_runtime_lock"; do
  if [ ! -f "$lock" ] || [ -L "$lock" ]; then
    echo "required hash lock must be a regular, non-symbolic-link file: $lock" >&2
    exit 2
  fi
done

package_version="$(
  "$python" -c 'import pathlib,sys,tomllib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text())["project"]["version"])' \
    "$root/pyproject.toml"
)"

if [ -e "$output" ]; then
  echo "refusing to merge with existing bundle: $output" >&2
  echo "choose a new output path or remove the old bundle explicitly" >&2
  exit 2
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT HUP INT TERM
bundle="$work/bundle"
wheel_dist="$work/dist"
source_root="$work/source"
resolved_generator_lock="$work/generator-requirements.lock"
resolved_build_system_lock="$work/build-system-requirements.lock"
mkdir -p \
  "$bundle/wheelhouse/generator" \
  "$bundle/wheelhouse/python-fastapi" \
  "$bundle/apk" \
  "$bundle/npm-cache" \
  "$bundle/playwright" \
  "$wheel_dist" \
  "$source_root/src"
cp "$generator_requirements_lock" "$resolved_generator_lock"
cp "$build_system_lock" "$resolved_build_system_lock"

# Stabilize wheel metadata and archive ordering across builds of the same source tree.
export PYTHONHASHSEED=0
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-315532800}"

# Resolve every generator/build artifact through its reviewed content hash before running any of
# its code. This is the only Python step that may contact the approved factory package source.
"$python" -m pip download \
  --disable-pip-version-check \
  --require-hashes \
  --only-binary=:all: \
  --platform "$pip_platform" \
  --platform "$pip_compat_platform" \
  --python-version "$generator_python" \
  --implementation cp \
  --abi "$generator_abi" \
  --dest "$bundle/wheelhouse/generator" \
  -r "$resolved_generator_lock"

# Build in a disposable environment populated only from the verified wheelhouse. --no-isolation is
# deliberate: the normal PEP 517 isolated environment would resolve build requirements a second
# time without the repository's hash policy.
"$python" -m venv "$work/build-env"
"$work/build-env/bin/python" -m pip install \
  --disable-pip-version-check \
  --no-index \
  --only-binary=:all: \
  --require-hashes \
  --find-links "$bundle/wheelhouse/generator" \
  -r "$resolved_build_system_lock"

cp "$root/pyproject.toml" "$root/README.md" "$root/MANIFEST.in" "$source_root/"
cp -R "$root/rules" "$source_root/rules"
mkdir -p "$source_root/agent-platform"
cp \
  "$root/agent-platform/agent-catalog.schema.json" \
  "$root/agent-platform/agent-catalog.yml" \
  "$root/agent-platform/agent-contract.schema.json" \
  "$root/agent-platform/agent-policy.schema.json" \
  "$root/agent-platform/client-capabilities.yml" \
  "$root/agent-platform/conformance-snapshot.schema.json" \
  "$root/agent-platform/decision-policy.schema.json" \
  "$root/agent-platform/orchestration.schema.json" \
  "$root/agent-platform/runtime-candidate.schema.json" \
  "$root/agent-platform/standards-crosswalk.yml" \
  "$source_root/agent-platform/"
cp -R "$root/agent-platform/agents" "$source_root/agent-platform/agents"
cp -R "$root/agent-platform/orchestrations" "$source_root/agent-platform/orchestrations"
cp -R "$root/agent-platform/policies" "$source_root/agent-platform/policies"
cp -R "$root/src/kt_scaffold" "$source_root/src/kt_scaffold"
PIP_NO_INDEX=1 "$work/build-env/bin/python" -m build \
  --no-isolation \
  --wheel \
  --outdir "$wheel_dist" \
  "$source_root"
set -- "$wheel_dist"/kt_scaffold-*.whl
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "expected exactly one kt-scaffold wheel" >&2
  exit 2
fi
wheel="$1"
cp "$wheel" "$bundle/"

# Generator and generated Python profile use different Python versions and may pin different
# developer tools, so they intentionally have separate wheelhouses.
"$python" -m pip download \
  --disable-pip-version-check \
  --require-hashes \
  --only-binary=:all: \
  --platform "$pip_platform" \
  --platform "$pip_compat_platform" \
  --python-version "$profile_python" \
  --implementation cp \
  --abi "$profile_abi" \
  --dest "$bundle/wheelhouse/python-fastapi" \
  -r "$root/src/kt_scaffold/templates/python-fastapi/app/backend/requirements.txt" \
  -r "$root/src/kt_scaffold/templates/python-fastapi/app/backend/requirements-dev.txt"

index=0
for project in \
  "$root/src/kt_scaffold/templates/common/app/frontend" \
  "$root/src/kt_scaffold/templates/common/e2e"
do
  index=$((index + 1))
  target="$work/npm-$index"
  mkdir -p "$target"
  cp "$project/package.json" "$project/package-lock.json" "$target/"
  (
    cd "$target"
    npm ci --ignore-scripts --no-audit --no-fund --cache "$bundle/npm-cache"
    rm -rf node_modules
    npm ci --offline --ignore-scripts --no-audit --no-fund --cache "$bundle/npm-cache"
  )
done

# The package lock pins the Playwright driver. Playwright verifies its browser download; the
# bundle-wide SHA256SUMS below then seals the extracted browser tree for air-gap transfer.
(
  cd "$work/npm-2"
  PLAYWRIGHT_BROWSERS_PATH="$bundle/playwright" \
    npm exec --offline --cache "$bundle/npm-cache" -- playwright install chromium
  PLAYWRIGHT_BROWSERS_PATH="$bundle/playwright" \
    node -e \
      'const {chromium}=require("playwright"); console.log(chromium.executablePath())'
)

# Pull every build/runtime identity by immutable digest and preserve those exact identities in one
# tar. The consuming bank imports/promotes the tar; workloads never contact these source registries.
set --
while IFS= read -r image; do
  case "$image" in
    ""|\#*) continue ;;
  esac
  case "$image" in
    *@sha256:*) ;;
    *) echo "image is not digest-pinned: $image" >&2; exit 2 ;;
  esac
  docker pull --platform "$oci_platform" "$image"
  set -- "$@" "$image"
done < "$root/packaging/images.lock"
docker save --output "$bundle/runtime-images.tar" "$@"

# Build the global stdio MCP provisioning image with networking disabled. Its content-addressed
# image ID is the identity used by the bundled wrapper, so a mutable tag never decides what runs.
cp "$root/packaging/Dockerfile" "$bundle/Containerfile.kt-scaffold"
generator_base="$(awk '/^python:3[.]13-alpine3[.]23@sha256:/ {print; exit}' "$root/packaging/images.lock")"
if [ -z "$generator_base" ]; then
  echo "generator base image missing from packaging/images.lock" >&2
  exit 2
fi

# Resolve the patched runtime APK for the exact bundle architecture while the factory is still
# connected. The lock supplies both the exact package version and its reviewed content digest;
# the no-network image build below verifies the digest again before apk verifies Alpine's package
# signature and installs it.
set -- $(awk -v arch="$factory_arch" '$1 == arch { print $2, $3, $4 }' \
  "$alpine_runtime_lock")
if [ "$#" -ne 3 ]; then
  echo "missing or ambiguous Alpine runtime package lock for $factory_arch" >&2
  exit 2
fi
alpine_arch="$1"
alpine_package_spec="$2"
alpine_package_sha256="$3"
alpine_package_name="${alpine_package_spec%%=*}"
alpine_package_file="${alpine_package_spec%%=*}-${alpine_package_spec#*=}.apk"
docker run --rm \
  --platform "$oci_platform" \
  --volume "$bundle/apk:/apk" \
  "$generator_base" \
  sh -ec '[ "$(apk --print-arch)" = "$1" ]; apk update >/dev/null; apk fetch --available --output /apk "$2" >/dev/null' \
  sh "$alpine_arch" "$alpine_package_name"
printf '%s  %s\n' "$alpine_package_sha256" "$bundle/apk/$alpine_package_file" \
  | shasum -a 256 -c -
cp "$alpine_runtime_lock" "$bundle/alpine-runtime-packages.lock"

docker build \
  --network=none \
  --platform "$oci_platform" \
  --build-arg "KT_SCAFFOLD_BASE_IMAGE=$generator_base" \
  --build-arg "KT_SCAFFOLD_VERSION=$package_version" \
  --iidfile "$work/generator-image.id" \
  --file "$root/packaging/Dockerfile" \
  "$bundle"
generator_image_id="$(cat "$work/generator-image.id")"
case "$generator_image_id" in
  sha256:????????????????????????????????????????????????????????????????) ;;
  *) echo "unexpected generator image ID: $generator_image_id" >&2; exit 2 ;;
esac
printf '%s\n' "$generator_image_id" > "$bundle/generator-image.id"
docker save --output "$bundle/generator-image.tar" "$generator_image_id"
sed "s|@@GENERATOR_IMAGE_ID@@|$generator_image_id|g" \
  "$root/packaging/kt-scaffold-oci.in" > "$bundle/kt-scaffold-oci"
chmod 0755 "$bundle/kt-scaffold-oci"

cp "$root/packaging/images.lock" "$bundle/"
cp "$resolved_generator_lock" "$bundle/generator-requirements.lock"
cp "$resolved_build_system_lock" "$bundle/build-system-requirements.lock"
cp "$root/packaging/README.md" "$bundle/README.md"
generator_lock_sha256="$(shasum -a 256 "$resolved_generator_lock" | awk '{print $1}')"
build_system_lock_sha256="$(shasum -a 256 "$resolved_build_system_lock" | awk '{print $1}')"
alpine_runtime_lock_sha256="$(shasum -a 256 "$alpine_runtime_lock" | awk '{print $1}')"
printf '%s\n' \
  "pip-platform=$pip_platform" \
  "pip-compat-platform=$pip_compat_platform" \
  "oci-platform=$oci_platform" \
  "generator-python=$generator_python" \
  "generator-abi=$generator_abi" \
  "generator-requirements-lock-sha256=$generator_lock_sha256" \
  "build-system-lock-sha256=$build_system_lock_sha256" \
  "alpine-runtime-lock-sha256=$alpine_runtime_lock_sha256" \
  "profile-python=$profile_python" \
  "profile-abi=$profile_abi" \
  "kt-scaffold-version=$package_version" \
  "source-date-epoch=$SOURCE_DATE_EPOCH" > "$bundle/BUILD-MATRIX"
(
  cd "$bundle"
  if find . -type l -print -quit | grep -q .; then
    echo "refusing to seal a bundle containing symbolic links" >&2
    exit 2
  fi
  find . -type f ! -name SHA256SUMS -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 shasum -a 256 > SHA256SUMS
  shasum -a 256 -c SHA256SUMS
)

mkdir -p "$(dirname -- "$output")"
mv "$bundle" "$output"
echo "offline bundle ready: $output"
echo "bank admission SHA256SUMS digest: $(shasum -a 256 "$output/SHA256SUMS" | awk '{print $1}')"
