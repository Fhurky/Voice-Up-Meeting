# Quality manifest

| Surface | Scenario | Evidence |
|---|---|---|
| Platform authentication | auth/01-super-admin-login.mjs | Protected redirect, login, JWT persistence, tenant rejection/acceptance, DB-backed `/me`, reload and logout cleanup |
| Local speaker pilot | speaker-identity/01-local-pilot.mjs, speaker-identity/02-read-only.mjs | Accepted speaker-identity/001 PRD: real ordinary-role/read-only and admin login, TR/EN, malformed audio rejection, durable failed job and refresh; profile enrollment, rename, identify, deletion and API cleanup when an explicit clean audio fixture is supplied. Fixture reuse proves wiring, not held-out recognition quality. |

Domain rows are added only by accepted PRDs.
