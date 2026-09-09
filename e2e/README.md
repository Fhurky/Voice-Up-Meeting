# Browser evidence

The permanent browser suite runs against `APP_E2E_BASE`, defaulting to `http://127.0.0.1:8081`. It
uses process-sourced super-admin credentials and never commits them. The baseline scenario proves
the protected redirect, login, JWT persistence, tenant enforcement, database-backed `/auth/me`,
reload recovery and logout cleanup. It is plain, client-neutral Node.js/Playwright code: it does not
install a plugin or expose a second MCP server. Browser binaries must come from the controlled
offline bundle and are selected through `PLAYWRIGHT_BROWSERS_PATH`.

Run a suite from the repository root:

~~~sh
export KT_SCAFFOLD_OFFLINE_BUNDLE=/approved/bundles/<platform-matrix>
export KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-sha256-of-SHA256SUMS>
scripts/e2e.sh auth
~~~

Offline mode is the default. The helper first binds `SHA256SUMS` to the digest held in the bank's
out-of-band artifact admission record, then verifies every listed file, checks the bundle platform, installs
with npm's offline mode from the bundle cache, verifies that Playwright resolves an executable
Chromium inside the admitted tree, and only then starts the suite. There is no registry or browser
download fallback. Rewriting both a payload and its in-bundle manifest therefore does not establish
trust. A bank-connected development environment may explicitly select
`KT_SCAFFOLD_E2E_MODE=private-index`; that mode also requires `KT_SCAFFOLD_NPM_REGISTRY` and a
pre-provisioned `PLAYWRIGHT_BROWSERS_PATH`, and rejects public npm registries.

On failure each suite writes a slugged `test-results/*-failure.png`; this is ignored local evidence.
The root quality gate discovers every `e2e/*/run-all.mjs` runner, so generated domain suites cannot
silently fall outside the browser evidence tier.
