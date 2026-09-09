---
id: "31-frontend-api-integration"
title: "Consume only the committed OpenAPI contract through the shared client"
scope: frontend
authority: mandatory
priority: 40
trigger: path-match
applies_to:
  - "app/frontend/src/services/**"
  - "app/frontend/src/lib/apiClient.*"
  - "app/frontend/src/types/api.d.ts"
  - "specs/openapi/**"
gate: "type-drift"
---

# Frontend API integration

The contract pipeline is ordered and offline:

1. export the backend OpenAPI document;
2. compare and commit the document;
3. regenerate `src/types/api.d.ts` from that committed document;
4. compare and commit the generated types.

Never generate from an arbitrary running server and never manually duplicate a request or response
type that already exists in the committed contract. During a new vertical's single-pass generation,
the page generator may emit the same minimal response projection beside its service before the
backend OpenAPI export exists; the mandatory export/type-drift gate is what admits that projection.
Once the generated contract type exists, prefer an alias/projection from it. One domain service under
`src/services/` exposes focused frontend operations. Pages and components call services, not raw
`fetch`.

All requests go through the shared client. It owns same-origin URL resolution, JSON headers, bearer
access tokens, the configured tenant header, request identifiers where required, response parsing,
and the typed error envelope. Externally address records by `public_id`; never send an internal
numeric identity.

Only terminate the local session when a response proves that the application's own bearer credential
expired or is invalid, such as a matching `WWW-Authenticate` challenge. Do not log out on an upstream
failure, proxy error, unrelated 401, 5xx, timeout, or parse failure.

Service calls expose typed loading, empty, success, validation, forbidden, not-found, and unexpected
failure behavior to the UI. Do not show a raw backend message when it may contain implementation
detail; map stable error codes to localized messages and retain diagnostic context for structured
logging.
