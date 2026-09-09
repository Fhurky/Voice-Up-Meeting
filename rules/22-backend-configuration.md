---
id: "22-backend-configuration"
title: "Route all configuration through one typed settings surface"
scope: backend
authority: mandatory
priority: 40
trigger: path-match
applies_to:
  - "app/backend/**"
  - "app/infra/**"
  - "app/devops/**"
gate: "configuration-sync"
---

# Configuration and secrets

The fixed Python/FastAPI backend exposes one typed settings object. Application code reads configuration
only through that object; direct process-environment reads are limited to the settings loader and
explicit bootstrap entry points. Do not create module-level settings snapshots that bypass test
overrides.

Every environment key uses the prefix recorded in `.kt-scaffold/answers.yml`. Never hardcode the
example prefix. A new setting is incomplete until the same change updates all applicable surfaces:

1. the typed settings declaration and boot validation;
2. `app/backend/.env.example` with a placeholder, never a real secret;
3. each consuming service's local Compose environment block;
4. the deployment chart's single pre-created Secret boundary, selected through `existingSecret`.

Run `python3 scripts/check-config-sync.py` after configuration changes. The check derives applicable
keys from the fixed stack's typed settings, rejects unprefixed or foreign-prefixed application
environment keys, and rejects direct process-environment reads outside the approved settings loader
and bootstrap boundaries.

Real-environment overlays may leave deployment facts visibly unresolved, while committed fixture
overlays provide non-secret values for structural render tests. Environment-readiness validation must
reject unresolved hosts, registries, StorageClasses, and Secret names.

Charts reference one pre-created Secret by name through `envFrom`; they do not enumerate per-key
secret mappings. Overlays select deployment facts, including the Secret name, without claiming or
copying its key set. Secret material never enters source, example files, chart values, overlays,
logs, generated answers, or the scaffold manifest. The `super_admin`
bootstrap password is read interactively or from the invoking process, used to store a password hash,
and discarded; it is never a normal setting. The bootstrap command is idempotent for the configured
identity, preserves the explicit `super_admin` grant, and never prints the password or hash.

Validate required settings at process start. Construct URLs with one safe join/parse helper rather
than string concatenation. When configuration differs by environment, encode the difference in the
environment layer, not in scattered application branches.
