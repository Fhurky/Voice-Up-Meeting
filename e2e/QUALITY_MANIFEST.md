# Quality manifest

| Surface | Scenario | Evidence |
|---|---|---|
| Platform authentication | auth/01-super-admin-login.mjs | Protected redirect, login, JWT persistence, tenant rejection/acceptance, DB-backed `/me`, reload and logout cleanup |
| Explicit local administrator sign-in | auth/02-local-admin-login.mjs | Accepted speaker-identity/006 PRD: enabled public option, empty credential fields, explicit TR/EN button to protected home, existing admin/tenant session, reload via `/me`, logout cleanup, no automatic login on mount/reload/logout, console/HTTP and accessibility checks. Requires an eligible pre-existing administrator on a local development stack; creates no account or business fixture. |
| Local speaker pilot | speaker-identity/01-local-pilot.mjs, speaker-identity/02-read-only.mjs | Accepted speaker-identity/001 PRD: real ordinary-role/read-only and admin login, TR/EN, malformed audio rejection, durable failed job and refresh; profile enrollment, rename, identify, deletion and API cleanup when an explicit clean audio fixture is supplied. Fixture reuse proves wiring, not held-out recognition quality. |
| Speaker profile totals and historical errors | speaker-identity/03-profile-capacity.mjs | Accepted speaker-identity/001 Decision 11: ordinary writable login in an isolated fixture tenant with at least 50 profiles; TR/EN API total agreement, no max_profiles metadata, new enrollment fields editable, existing-profile sample form available, pagination uses total, historical profile_limit explanation. Read-only fixture inspection; no profile/audio/job mutations or recognition-accuracy claim. |

Domain rows are added only by accepted PRDs.
