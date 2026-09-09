---
id: "14-browser-verification"
title: "Verify interface behavior through the real browser and committed scenarios"
scope: process
priority: 50
trigger: path-match
applies_to:
  - "app/frontend/**"
  - "e2e/**"
  - "specs/**/PRDs/**"
gate: "quality_gate --allow-project-code-execution --include-browser"
---

# Browser verification

An interface-affecting change requires both frontend automated tests and a live pass against the
running stack. Use the configured reverse-proxy origin that serves the SPA and API together; do not
verify against the frontend development server when it cannot proxy the real API.

Drive the actual login form. Do not inject a token or bypass authentication. Platform and generated
domain fixture setup may use the application `super_admin`; authorization-specific acceptance points
must also use an ordinary role because the bypass would hide a gating defect.

For each acceptance point:

1. Navigate to the real route.
2. Read the accessibility tree.
3. Interact through returned element references.
4. Assert the expected role, accessible name, state, navigation, error, loading, or empty result.
5. Inspect console and network evidence before changing code after a failure.

Wait for a concrete state, never a fixed sleep. Use screenshots only for visual properties the
accessibility tree cannot express. Verify locale-sensitive behavior in every affected configured
locale or explicitly pin and report the locale.

Permanent scenarios live under `e2e/<domain>/`, use the shared harness, clean up through public APIs
in a `finally` path, and register one surface row in `e2e/QUALITY_MANIFEST.md`. Report exactly what was
driven and observed; a build pass is not live evidence.
