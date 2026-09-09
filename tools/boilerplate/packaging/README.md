# Offline bundle

`offline-bundle.sh` runs only in an approved connected artifact factory. It resolves immutable,
reviewed inputs and emits a self-verifying directory for a single OS/architecture/runtime matrix.
Nothing in a consuming workstation or generated application downloads from the public internet.
The connected factory must first pass `dependency-admission.json`; changing a direct package,
workflow action or OCI identity invalidates its reviewed inventory digest. Scanner binaries and
their databases are a separate bank-admitted security-toolchain snapshot and are never fetched by
this bundle script.

The repository-root `Dockerfile` is the connected AppSec build entrypoint used by scanners that
require a directly buildable source context. It downloads only artifacts admitted by the generator
hash lock, installs only the architecture-specific Alpine runtime package admitted by
`locks/alpine-runtime-packages.lock`, builds the wheel without isolation, and copies only the wheel
plus runtime dependencies into the final image. Air-gapped promotion remains owned by `offline-bundle.sh` and
`packaging/Dockerfile`; the AppSec entrypoint does not replace that boundary.

The default matrix is Linux x86-64 and Python 3.13 on Alpine 3.23 for both `kt-scaffold` and the
FastAPI profile. The wheel resolver accepts both the target's `musllinux_1_2` tag and the compatible
`musllinux_1_1` tag because pinned dependencies legitimately publish across both. Use
`OCI_PLATFORM`, `PIP_PLATFORM`, `PIP_COMPAT_PLATFORM`, `GENERATOR_PYTHON_VERSION`,
`GENERATOR_PYTHON_ABI`, `PROFILE_PYTHON_VERSION`, and `PROFILE_PYTHON_ABI` to build another reviewed
matrix into a different output directory. A non-default generator tuple must additionally provide
its separately reviewed, fully hashed lock through `GENERATOR_REQUIREMENTS_LOCK`; the repository's
default artifact lock is intentionally valid only for Linux x86-64 / CPython 3.13 / musllinux. Never merge
matrices: each bundle has its own `BUILD-MATRIX` and `SHA256SUMS`.
The connected artifact factory must itself match `OCI_PLATFORM`; the script fails otherwise because
npm optional native packages and the Playwright browser tree are host-platform selections and
cannot be safely cross-populated by changing an environment variable.

Before any downloaded generator or Python build dependency executes, pip resolves it with
`--require-hashes` against
`locks/generator-linux-amd64-cp313-musllinux.requirements.lock`. The build frontend and the setuptools/wheel
backend are installed offline from that verified wheelhouse using the smaller
`locks/build-system.requirements.lock`, then the wheel is built with PEP 517 isolation disabled.
This is deliberate: ordinary build isolation would perform another dependency resolution outside
the artifact hash policy. Both lock digests are recorded in `BUILD-MATRIX`, and immutable snapshots
of both lock inputs are copied into the bundle. The review/update procedure is documented in
`locks/README.md`.

The bundle contains:

- the generator wheel, its admitted artifact hash lock and its separate, platform-correct
  wheelhouse;
- the exact Alpine runtime APK selected for that architecture, with its reviewed digest lock;
- the FastAPI profile wheelhouse;
- one integrity-pinned npm cache for the frontend and E2E harness;
- the pinned Playwright Chromium tree for that platform;
- all base and runtime OCI images as one tar;
- the built generator image, its content-addressed image ID, and a no-network stdio wrapper.

The same generator image may run the internal Streamable HTTP application in a Kubernetes pod next
to the bank's approved OAuth/TLS gateway sidecar:

~~~sh
kt-scaffold mcp --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
~~~

It deliberately binds pod loopback, which containers in one pod share. Only the gateway sidecar
publishes a Service port. The pod uses a read-only root filesystem, a bounded non-executable `/tmp`
volume, no public egress and no workspace volume. The service accepts only bounded project metadata
and reconciliation decisions; it never accepts source trees, database data or secrets. The gateway
must cap request bodies at the application's 1 MiB boundary and owns OAuth 2.1, audience/scopes, TLS
or mTLS, rate limits and audit identity.
This central service is separate from the `kt-scaffold-oci` stdio wrapper, whose `--network none`
and admitted writable project mount remain unchanged.

At the boundary, record the SHA-256 of `SHA256SUMS` in the bank's artifact admission system (outside
the bundle), verify `shasum -a 256 -c SHA256SUMS`, load both image tar files, then run
`./kt-scaffold-oci --version`. Platform management may promote runtime images into the internal
registry, preserving their OCI index digests. The wrapper launches the generator by image ID with no
network, a read-only root filesystem, dropped capabilities, the invoking non-root user's UID/GID,
and only one admitted project directory mounted writable.

Before invoking the wrapper, platform management sets `KT_SCAFFOLD_WORKSPACE_ROOT` to the absolute,
already-canonical path of the bank-approved workspace parent. The selected target, supplied through
`KT_SCAFFOLD_TARGET` or the process working directory, must be a strict descendant. It must either be
completely empty for `project_init` or contain regular `.kt-scaffold/answers.yml` and
`.kt-scaffold/manifest.json` files. `/`, `HOME`, the workspace parent itself, symbolic-link targets,
and nonempty unmarked directories are rejected before Docker runs. For example:

~~~sh
export KT_SCAFFOLD_WORKSPACE_ROOT=/bank/workspaces
mkdir /bank/workspaces/payment-controls
cd /bank/workspaces/payment-controls
/opt/kt-scaffold/kt-scaffold-oci --version
~~~

Consumers pass that separately admitted digest as `KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256`. The
in-bundle checksum list detects payload damage; the out-of-band digest prevents a replacement from
becoming trusted merely by rewriting the list too.

The npm cache and Python profile wheelhouse are BuildKit named-context inputs. Generated Compose
passes their absolute paths through `NPM_CACHE_CONTEXT` and `PYTHON_WHEELHOUSE_CONTEXT` when
`DEPENDENCY_MODE=offline`; profile Dockerfiles then enforce npm offline or pip no-index mode. There
is no fallback to a public package or binary registry.
